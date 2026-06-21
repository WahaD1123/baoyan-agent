import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.agents import CriticAgent, InterviewAgent, MaterialAgent
from app.agents_sdk.member_c import build_member_c_agent_llm
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
        default_llm = None
        if material_agent is None or interview_agent is None or critic_agent is None:
            default_llm = build_member_c_agent_llm()
        self.material_agent = material_agent or MaterialAgent(llm=default_llm)
        self.interview_agent = interview_agent or InterviewAgent(llm=default_llm)
        self.critic_agent = critic_agent or CriticAgent(llm=default_llm)

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
        revision_applied = False
        revision_preserved = False

        for planned_step in planning.plan.steps:
            if (
                planned_step.condition == "critic_failed"
                and decision
                and not _needs_automatic_revision(decision)
            ):
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
                    trace, draft, revision_applied = self._run_revision(
                        task,
                        planned_step,
                        collected,
                        draft,
                        decision,
                    )
                    steps.append(trace)
                    revision_preserved = not revision_applied
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
            final_result=self._final_result(
                task.title,
                draft.output,
                decision,
                revision_applied,
                revision_preserved,
            ),
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
            agent = self.interview_agent
            model_task = "interview"
        else:
            agent = self.material_agent
            model_task = "material"
        result = agent.generate(prompt, task.references)
        result.output = _normalize_generated_content(result.output, task.goal)
        model_name, reason = _agent_execution_trace(agent, model_task, planned_step.reason)
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Generate {task.title}",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason=reason,
                model_name=model_name,
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
            task.generation_rules,
            [*task.references, draft.id],
        )
        model_name, execution_reason = _agent_execution_trace(
            self.critic_agent,
            "critic_structured",
            f"passed={decision.passed}; score={decision.score}; {decision.summary}",
        )
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Critic review {task.title}",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason=execution_reason,
                model_name=model_name,
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
    ) -> tuple[WorkflowStep, AgentResult, bool]:
        context = _json_summary(collected, limit=1800)
        started_at = datetime.now(UTC)
        started = perf_counter()
        if planned_step.capability == "interview.revise":
            agent = self.interview_agent
            model_task = "interview"
        else:
            agent = self.material_agent
            model_task = "material"
        result = agent.revise(
            draft.output,
            decision,
            context,
            task.generation_rules,
            task.references,
        )
        model_name, reason = _agent_execution_trace(
            agent,
            model_task,
            "Critic rejected the first draft; one bounded revision was executed.",
        )
        revision_applied = not _agent_used_fallback(agent)
        if revision_applied:
            result.output = _normalize_generated_content(result.output, task.goal)
        else:
            result.output = draft.output
            reason += " Revision fallback was discarded; kept the original draft."
        completed_at = datetime.now(UTC)
        return (
            WorkflowStep(
                name=f"Revise {task.title} once",
                status="completed",
                step_type="agent",
                capability=planned_step.capability,
                decision_reason=reason,
                model_name=model_name,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=_elapsed_ms(started),
                agent_result=result,
            ),
            result,
            revision_applied,
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
            "publications, technical stacks, advisor works, or contact details. Do not upgrade "
            "participation into leadership: preserve distinctions such as 参与、负责、主导 and 独立完成.\n"
            f"rules={json.dumps(task.generation_rules, ensure_ascii=False)}\n"
            f"request={json.dumps(task.request_details, ensure_ascii=False)}\n"
            f"grounded_context={json.dumps(collected, ensure_ascii=False)}"
        )

    def _final_result(
        self,
        title: str,
        content: str,
        decision: CriticDecision | None,
        revision_applied: bool,
        revision_preserved: bool,
    ) -> str:
        suggestions = _format_user_actions(
            decision,
            revision_applied,
            revision_preserved,
        )
        material = f"## {title}\n{_normalize_generated_content(content, '')}"
        return f"{material}\n\n## 建议\n{suggestions}" if suggestions else material


def _json_summary(value: Any, limit: int = 420) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _sanitize_user_content(content: str) -> str:
    content = re.sub(
        r"\s*\[DashScope fallback:\s*[^\]]+\]\s*$",
        "",
        content,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\bpending\b",
        "【待补充：真实量化结果】",
        content,
        flags=re.IGNORECASE,
    ).strip()


def _normalize_generated_content(content: str, goal: str) -> str:
    sanitized = _sanitize_user_content(content)
    if goal == "generate_advisor_email":
        return _normalize_email_markdown(sanitized)
    if goal == "generate_resume_highlights":
        return _normalize_resume_markdown(sanitized)
    if goal == "generate_interview":
        return _normalize_interview_markdown(sanitized)
    return sanitized


def _normalize_email_markdown(content: str) -> str:
    match = re.match(r"^(尊敬的[^：:\n]+)[：:]\s*(.*)$", content, flags=re.DOTALL)
    if not match:
        return content

    salutation = match.group(1).strip()
    if salutation.endswith("您好"):
        salutation = salutation[:-2].rstrip()
    body = re.sub(r"^您好[！!，,\s]*", "", match.group(2).strip())
    for paragraph_start in (
        "在科研实践中",
        "在项目实践中",
        "科研方面",
        "此次致信",
        "随信附上",
        "感谢您",
        "期待能",
    ):
        body = re.sub(
            rf"(?<!\n)\s+(?={paragraph_start})",
            "\n\n",
            body,
        )

    closing_match = re.search(r"\s*此致\s*敬礼[！!]?\s*(.*)$", body, flags=re.DOTALL)
    signature_text = ""
    if closing_match:
        signature_text = closing_match.group(1).strip()
        body = body[: closing_match.start()].rstrip()

    sections = [f"{salutation}：", "您好！"]
    if body:
        sections.append(body)
    if closing_match:
        sections.extend(["此致", "敬礼！"])
        signature = _normalize_email_signature(signature_text)
        if signature:
            sections.extend(signature)
    return "\n\n".join(sections).strip()


def _normalize_email_signature(signature: str) -> list[str]:
    if not signature:
        return []

    compact = re.sub(r"[|｜]", " ", signature)
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", compact)
    phone_match = re.search(r"(?<!\d)\d[\d-]{6,}\d", compact)
    date_match = re.search(
        r"(?:\d{4}\s*年\s*(?:\d{1,2}|X)\s*月\s*(?:\d{1,2}|X)\s*日|\d{4}[-/.](?:\d{1,2}|X)[-/.](?:\d{1,2}|X))",
        compact,
        flags=re.IGNORECASE,
    )

    name_area_end = min(
        [item.start() for item in (email_match, phone_match, date_match) if item]
        or [len(compact)]
    )
    name_area = re.sub(
        r"学生|姓名|邮箱|电话|日期|敬上|[：:\s]",
        "",
        compact[:name_area_end],
    )
    name_match = re.search(r"[\u4e00-\u9fff·]{2,20}", name_area)

    lines: list[str] = []
    if name_match:
        lines.append(f"学生：{name_match.group(0)}")
    if email_match:
        lines.append(f"邮箱：{email_match.group(0)}")
    if phone_match:
        lines.append(f"电话：{phone_match.group(0)}")
    if date_match:
        lines.append(f"日期：{date_match.group(0)}")
    return lines or [signature.strip()]


def _normalize_resume_markdown(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    source_items = (
        lines
        if len(lines) > 1
        else re.split(r"(?<=[。！？])\s+(?=\S)", lines[0]) if lines else []
    )
    items: list[str] = []
    for source_item in source_items:
        item = re.sub(
            r"^(?:[-*+]\s+|\d{1,2}[.、]\s*)",
            "",
            source_item.strip(),
        )
        if item:
            items.append(item)
    if len(items) < 2:
        return content
    return "\n".join(f"- {item}" for item in items)


_INTERVIEW_HEADINGS = {
    "项目",
    "项目经历",
    "项目追问",
    "CS基础",
    "专业基础",
    "科研",
    "科研经历",
    "科研方向",
    "英语面试",
    "复盘",
    "综合复盘",
    "复盘建议",
}


def _normalize_interview_markdown(content: str) -> str:
    expanded = re.sub(
        r"[ \t]+(?=(?:\d{1,2}\.\s+|\d{1,2}、\s*))",
        "\n",
        content,
    )
    expanded = re.sub(r"(?<=[？?])\s+(?=\S)", "\n", expanded)
    blocks: list[str] = []
    question_number = 1

    for raw_line in expanded.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.sub(r"^#{1,4}\s*", "", line).rstrip("：:")
        if heading in _INTERVIEW_HEADINGS:
            blocks.append(f"### {heading}")
            continue
        focus = re.sub(r"^>\s*", "", line)
        if focus.startswith("考察重点"):
            blocks.append(f"> {focus}")
            continue
        numbered = re.match(r"^(?:(\d{1,2})\.\s+|(\d{1,2})、\s*)(.+)$", line)
        if numbered:
            number = int(numbered.group(1) or numbered.group(2))
            blocks.append(f"{number}. {numbered.group(3).strip()}")
            question_number = max(question_number, number + 1)
            continue
        if line.endswith(("？", "?")):
            blocks.append(f"{question_number}. {line}")
            question_number += 1
            continue
        blocks.append(line)

    return "\n\n".join(blocks)


def _agent_execution_trace(
    agent: Any,
    model_task: str,
    base_reason: str,
) -> tuple[str, str]:
    model_name = model_name_for_task(model_task)
    call = getattr(getattr(agent, "llm", None), "last_call", None)
    if call is None:
        return model_name, base_reason
    model_name = call.model_name or model_name
    if call.source == "fallback":
        return model_name, f"{base_reason} Agent SDK fallback: {call.fallback_reason}"
    return model_name, f"{base_reason} Executed through the shared Agent SDK runtime."


def _needs_automatic_revision(decision: CriticDecision) -> bool:
    return not decision.passed and bool(decision.suggestions)


def _agent_used_fallback(agent: Any) -> bool:
    call = getattr(getattr(agent, "llm", None), "last_call", None)
    return call is not None and call.source == "fallback"


def _format_user_actions(
    decision: CriticDecision | None,
    revision_applied: bool,
    revision_preserved: bool = False,
) -> str:
    if decision is None or not decision.user_inputs:
        return ""
    return "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(decision.user_inputs, 1)
    )


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
                "Write a focused Chinese advisor email within 600 Chinese characters. It should provide enough evidence about the applicant rather than becoming an overly brief greeting.",
                "Include salutation, self-introduction, research fit, attachment note, and closing.",
                "Put the salutation alone on the first line as '尊敬的X老师：', put '您好！' in its own paragraph, and start the self-introduction in the next paragraph.",
                "In the self-introduction paragraph, include the applicant's university, major, GPA or ranking, English result, one or two relevant core-course grades, and the most representative competition award when those facts exist in grounded_context.",
                "Use the following paragraph for projects and research experience, so academic background and technical experience are not crowded into one paragraph.",
                "Describe the applicant's most relevant projects, research contribution, competition or measurable results with concrete details, and explicitly connect those experiences to the advisor's direction.",
                "Prioritize relevant evidence and organize it into a coherent introduction instead of mechanically copying every resume item.",
                "Use exact Markdown paragraphs for the closing and signature: put 此致, 敬礼！, 学生：姓名, 邮箱：地址, 电话：号码 and 日期：日期 in separate paragraphs with a blank line between them.",
                "Use placeholders for missing contact details and never invent facts.",
                "Omit unavailable optional project details from the body instead of filling the email with placeholders.",
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
                "Write every bullet on its own line and start it with '- '.",
                "Use an action-method-result-fit structure.",
                "Use Chinese placeholders such as 【待补充：项目准确率】 when quantitative results are missing; never invent metrics.",
                "Keep every required missing fact as an explicit Chinese placeholder so the user can complete it.",
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
                "Write three or four coherent paragraphs following: academic foundation; key experiences and lessons; research motivation and school fit; future plan.",
                "Build a complete narrative instead of repeating resume bullets or writing a short advisor email.",
                "Connect research interest, project evidence, target direction, and future plan, explaining what the applicant learned and why the interest formed.",
                "Do not include an email salutation, attachment note, contact details, or letter-style closing.",
                "Do not invent grades, experiments, papers, courses, or tool experience.",
                "Keep explicit Chinese placeholders for every fact required to make the statement credible but absent from evidence.",
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
                "Add one short 考察重点 for each category, but do not generate full reference answers.",
                "Write each category as a Markdown ### heading, each 考察重点 as a blockquote, and every question as a numbered item on its own line.",
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
