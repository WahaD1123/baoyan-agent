import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.agents import CriticAgent, InterviewAgent, MaterialAgent
from app.models import (
    Advisor,
    AgentResult,
    CriticDecision,
    StudentProfile,
    ToolCallTrace,
    WorkflowRun,
    WorkflowStep,
)
from app.services.llm import model_name_for_task
from app.services.member_c_mcp import MemberCMCPClient
from app.services.store import store
from app.workflows.capabilities import build_member_c_registry
from app.workflows.planner import TaskPlanner
from app.workflows.planning import PlanStep

UTC = timezone.utc


@dataclass(frozen=True)
class MemberCTask:
    goal: str
    workflow_type: str
    title: str
    profile: StudentProfile
    advisor: Advisor | None = None
    request_details: dict[str, Any] = field(default_factory=dict)
    generation_rules: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


class MemberCWorkflowExecutor:
    def __init__(
        self,
        planner: TaskPlanner | None = None,
        mcp_client: MemberCMCPClient | None = None,
        material_agent: MaterialAgent | None = None,
        interview_agent: InterviewAgent | None = None,
        critic_agent: CriticAgent | None = None,
    ) -> None:
        self.planner = planner or TaskPlanner(build_member_c_registry())
        self.mcp_client = mcp_client or MemberCMCPClient()
        self.material_agent = material_agent or MaterialAgent()
        self.interview_agent = interview_agent or InterviewAgent()
        self.critic_agent = critic_agent or CriticAgent()

    def execute(self, task: MemberCTask) -> WorkflowRun:
        plan_context = {
            "has_advisor": task.advisor is not None,
            "has_knowledge": bool(store.documents),
            "request_details": task.request_details,
        }
        planning = self.planner.plan(task.goal, plan_context)
        steps = [self._planner_trace(task, planning)]
        collected: dict[str, dict[str, Any]] = {}
        draft: AgentResult | None = None
        review: AgentResult | None = None
        decision: CriticDecision | None = None

        for planned_step in planning.plan.steps:
            if planned_step.condition == "critic_failed" and decision and decision.passed:
                steps.append(
                    WorkflowStep(
                        name=f"Skip {planned_step.capability}",
                        status="skipped",
                        step_type="condition",
                        capability=planned_step.capability,
                        decision_reason="Critic passed; conditional revision was not needed.",
                    )
                )
                continue

            try:
                if planned_step.kind == "tool":
                    trace, data = self._run_tool(task, planned_step)
                    steps.append(trace)
                    collected[planned_step.capability] = data
                elif planned_step.capability.endswith(".generate"):
                    trace, draft = self._run_generation(task, planned_step, collected)
                    steps.append(trace)
                elif planned_step.capability == "critic.review":
                    if draft is None:
                        raise RuntimeError("Critic cannot run before generation")
                    trace, review, decision = self._run_critic(task, planned_step, collected, draft)
                    steps.append(trace)
                elif planned_step.capability.endswith(".revise"):
                    if draft is None or decision is None:
                        raise RuntimeError("Revision requires a draft and critic decision")
                    trace, draft = self._run_revision(task, planned_step, collected, draft, decision)
                    steps.append(trace)
                else:
                    raise ValueError(f"Unsupported capability: {planned_step.capability}")
            except Exception as exc:
                steps.append(
                    WorkflowStep(
                        name=f"Failed {planned_step.capability}",
                        status="failed",
                        step_type=planned_step.kind,
                        capability=planned_step.capability,
                        decision_reason=planned_step.reason,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                return WorkflowRun(
                    workflow_type=task.workflow_type,
                    status="failed",
                    steps=steps,
                    final_result=f"Workflow failed at {planned_step.capability}: {exc}",
                    plan_source=planning.source,
                    planner_summary=planning.summary,
                )

        if draft is None:
            return WorkflowRun(
                workflow_type=task.workflow_type,
                status="failed",
                steps=steps,
                final_result="Workflow failed: the validated plan produced no draft.",
                plan_source=planning.source,
                planner_summary=planning.summary,
            )
        return WorkflowRun(
            workflow_type=task.workflow_type,
            status="completed",
            steps=steps,
            final_result=self._final_result(task.title, draft.output, review, decision),
            plan_source=planning.source,
            planner_summary=planning.summary,
        )

    def _planner_trace(self, task: MemberCTask, planning: Any) -> WorkflowStep:
        plan_json = planning.plan.model_dump_json()
        return WorkflowStep(
            name="Plan constrained Member C workflow",
            status="completed",
            step_type="planner",
            capability="workflow.plan",
            decision_reason=planning.summary,
            model_name=model_name_for_task("workflow_planner"),
            agent_result=AgentResult(
                agent_name="TaskPlanner",
                input_summary=f"goal={task.goal}",
                output=plan_json,
            ),
        )

    def _run_tool(
        self,
        task: MemberCTask,
        planned_step: PlanStep,
    ) -> tuple[WorkflowStep, dict[str, Any]]:
        arguments = self._tool_arguments(task, planned_step.capability)
        started_at = datetime.now(UTC)
        started = perf_counter()
        result = self.mcp_client.call_tool(planned_step.capability, arguments)
        completed_at = datetime.now(UTC)
        duration_ms = max(result.duration_ms, _elapsed_ms(started))
        return (
            WorkflowStep(
                name=f"Call MCP tool {planned_step.capability}",
                status="completed",
                step_type="tool",
                capability=planned_step.capability,
                decision_reason=planned_step.reason,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                tool_call=ToolCallTrace(
                    tool_name=planned_step.capability,
                    transport=result.transport,
                    arguments_summary=_json_summary(arguments),
                    result_summary=_json_summary(result.data),
                    duration_ms=result.duration_ms,
                    fallback_reason=result.fallback_reason or "",
                ),
            ),
            result.data,
        )

    def _run_generation(
        self,
        task: MemberCTask,
        planned_step: PlanStep,
        collected: dict[str, dict[str, Any]],
    ) -> tuple[WorkflowStep, AgentResult]:
        prompt = self._generation_prompt(task, collected)
        started_at = datetime.now(UTC)
        started = perf_counter()
        if planned_step.capability == "interview.generate":
            result = self.interview_agent.generate(prompt, task.references)
            model_task = "interview"
        else:
            result = self.material_agent.generate(prompt, task.references)
            model_task = "material"
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Generate {task.title}",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason=planned_step.reason,
                model_name=model_name_for_task(model_task),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_elapsed_ms(started),
                agent_result=result,
            ),
            result,
        )

    def _run_critic(
        self,
        task: MemberCTask,
        planned_step: PlanStep,
        collected: dict[str, dict[str, Any]],
        draft: AgentResult,
    ) -> tuple[WorkflowStep, AgentResult, CriticDecision]:
        evidence = _json_summary(collected, limit=1800)
        started_at = datetime.now(UTC)
        started = perf_counter()
        result, decision = self.critic_agent.review_member_c(
            draft.output,
            task.goal,
            evidence,
            [*task.references, draft.id],
        )
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Critic review {task.title}",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason=(
                    f"passed={decision.passed}; score={decision.score}; {decision.summary}"
                ),
                model_name=model_name_for_task("critic_structured"),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_elapsed_ms(started),
                agent_result=result,
            ),
            result,
            decision,
        )

    def _run_revision(
        self,
        task: MemberCTask,
        planned_step: PlanStep,
        collected: dict[str, dict[str, Any]],
        draft: AgentResult,
        decision: CriticDecision,
    ) -> tuple[WorkflowStep, AgentResult]:
        context = _json_summary(collected, limit=1800)
        started_at = datetime.now(UTC)
        started = perf_counter()
        if planned_step.capability == "interview.revise":
            result = self.interview_agent.revise(draft.output, decision, context, task.references)
            model_task = "interview"
        else:
            result = self.material_agent.revise(draft.output, decision, context, task.references)
            model_task = "material"
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Revise {task.title} once",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason="Critic rejected the first draft; one bounded revision was executed.",
                model_name=model_name_for_task(model_task),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_elapsed_ms(started),
                agent_result=result,
            ),
            result,
        )

    def _tool_arguments(self, task: MemberCTask, capability: str) -> dict[str, Any]:
        if capability == "profile.build_context":
            return {"profile": task.profile.model_dump(mode="json")}
        if capability == "advisor.get_context":
            return {
                "advisor": task.advisor.model_dump(mode="json") if task.advisor else None
            }
        query = " ".join(
            [
                task.goal,
                *task.profile.research_interests,
                *(str(value) for value in task.request_details.values()),
            ]
        )
        if capability == "knowledge.search":
            return {"query": query, "top_k": 3}
        if capability == "interview.retrieve_evidence":
            return {
                "profile": task.profile.model_dump(mode="json"),
                "target_school": str(task.request_details.get("target_school", "")),
                "direction": str(task.request_details.get("direction", "")),
                "top_k": 4,
            }
        raise ValueError(f"Unsupported MCP tool: {capability}")

    def _generation_prompt(
        self,
        task: MemberCTask,
        collected: dict[str, dict[str, Any]],
    ) -> str:
        material_kind = {
            "generate_advisor_email": "advisor_email",
            "generate_resume_highlights": "resume_highlights",
            "generate_statement": "personal_statement",
            "generate_interview": "categorized_mock",
        }[task.goal]
        return (
            f"material_kind={material_kind}\n"
            f"goal={task.goal}\n"
            "Output language: Chinese. Use only facts in grounded_context. Do not invent metrics, "
            "publications, technical stacks, advisor works, or contact details.\n"
            f"rules={json.dumps(task.generation_rules, ensure_ascii=False)}\n"
            f"request={json.dumps(task.request_details, ensure_ascii=False)}\n"
            f"grounded_context={json.dumps(collected, ensure_ascii=False)}"
        )

    def _final_result(
        self,
        title: str,
        content: str,
        review: AgentResult | None,
        decision: CriticDecision | None,
    ) -> str:
        review_output = review.output if review else "Critic was not executed."
        if decision and not decision.passed:
            review_output += "\nRevision: one bounded rewrite was applied."
        return f"## {title}\n{content}\n\n## \u8d28\u91cf\u68c0\u67e5\n{review_output}"


def _json_summary(value: Any, limit: int = 420) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def run_material_email_workflow(
    profile: StudentProfile,
    advisor: Advisor | None,
    purpose: str,
) -> WorkflowRun:
    references = [f"{advisor.name} - {advisor.university}"] if advisor else []
    return MemberCWorkflowExecutor().execute(
        MemberCTask(
            goal="generate_advisor_email",
            workflow_type="material_email",
            title="\u5bfc\u5e08\u8054\u7cfb\u90ae\u4ef6",
            profile=profile,
            advisor=advisor,
            request_details={"purpose": purpose},
            generation_rules=[
                "Write a polite and restrained Chinese advisor email within 600 Chinese characters.",
                "Include salutation, self-introduction, research fit, attachment note, and closing.",
                "Use placeholders for missing contact details and never invent facts.",
            ],
            references=references,
        )
    )


def run_resume_highlights_workflow(
    profile: StudentProfile,
    target_direction: str,
) -> WorkflowRun:
    return MemberCWorkflowExecutor().execute(
        MemberCTask(
            goal="generate_resume_highlights",
            workflow_type="resume_highlights",
            title="\u7b80\u5386\u4eae\u70b9",
            profile=profile,
            request_details={"target_direction": target_direction},
            generation_rules=[
                "Write exactly four Chinese resume bullets; each bullet must be at most 100 Chinese characters.",
                "Use an action-method-result-fit structure.",
                "Mark missing quantitative results as pending instead of inventing metrics.",
            ],
            references=list(profile.projects),
        )
    )


def run_statement_workflow(
    profile: StudentProfile,
    target_school: str,
    direction: str,
    tone: str,
) -> WorkflowRun:
    return MemberCWorkflowExecutor().execute(
        MemberCTask(
            goal="generate_statement",
            workflow_type="personal_statement",
            title="\u4e2a\u4eba\u9648\u8ff0",
            profile=profile,
            request_details={
                "target_school": target_school,
                "direction": direction,
                "tone": tone,
            },
            generation_rules=[
                "Write a Chinese personal-statement excerpt within 700 Chinese characters.",
                "Connect research interest, project evidence, target direction, and future plan.",
                "Do not invent grades, experiments, papers, courses, or tool experience.",
            ],
            references=[target_school, direction],
        )
    )


def run_interview_workflow(
    profile: StudentProfile,
    target_school: str,
    direction: str,
) -> WorkflowRun:
    return MemberCWorkflowExecutor().execute(
        MemberCTask(
            goal="generate_interview",
            workflow_type="interview",
            title="\u6a21\u62df\u9762\u8bd5\u9898",
            profile=profile,
            request_details={
                "target_school": target_school,
                "direction": direction,
            },
            generation_rules=[
                "Generate at most 15 questions in Chinese.",
                "Use project, CS fundamentals, research, English interview, and review categories.",
                "Ground project follow-ups in the supplied profile and evidence.",
                "Do not use a Markdown table.",
            ],
            references=[target_school, direction],
        )
    )


def run_material_workflow(
    profile: StudentProfile,
    advisor: Advisor | None,
    purpose: str,
) -> WorkflowRun:
    return run_material_email_workflow(profile, advisor, purpose)
