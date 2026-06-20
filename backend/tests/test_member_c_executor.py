import json

from app.agents import CriticAgent, InterviewAgent, MaterialAgent
from app.models import Advisor, StudentProfile
from app.services.member_c_mcp import MemberCMCPClient
from app.tools.member_c_tools import dispatch_local_tool
from app.workflows.capabilities import build_member_c_registry
from app.workflows.member_c_executor import MemberCTask, MemberCWorkflowExecutor
from app.workflows.planner import TaskPlanner


class ScriptedLLM:
    def __init__(self, critic_passed: bool) -> None:
        self.critic_passed = critic_passed
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, task: str = "general") -> str:
        self.calls.append((task, prompt))
        if task == "workflow_planner":
            return json.dumps(
                {
                    "goal": "generate_advisor_email",
                    "steps": [
                        {"kind": "tool", "capability": "profile.build_context"},
                        {"kind": "tool", "capability": "advisor.get_context"},
                        {"kind": "tool", "capability": "knowledge.search"},
                        {"kind": "agent", "capability": "material.generate"},
                        {"kind": "agent", "capability": "critic.review"},
                        {
                            "kind": "agent",
                            "capability": "material.revise",
                            "condition": "critic_failed",
                        },
                    ],
                }
            )
        if task == "critic_structured":
            return json.dumps(
                {
                    "passed": self.critic_passed,
                    "score": 88 if self.critic_passed else 62,
                    "summary": "grounded" if self.critic_passed else "revision required",
                    "issues": [] if self.critic_passed else ["one unsupported phrase"],
                    "suggestions": [] if self.critic_passed else ["remove the phrase"],
                }
            )
        if "revision_mode=true" in prompt:
            return "revised grounded email"
        return "first draft email"


def _task() -> MemberCTask:
    return MemberCTask(
        goal="generate_advisor_email",
        workflow_type="material_email",
        title="Advisor Contact Email",
        profile=StudentProfile(
            name="Alice",
            research_interests=["agent systems"],
            projects=["Built a multi-agent application assistant"],
        ),
        advisor=Advisor(
            name="Prof. Wang",
            university="Target University",
            research_areas=["agent systems"],
        ),
        request_details={"purpose": "summer camp application"},
        generation_rules=["Write in Chinese", "Use only supplied evidence"],
    )


def _executor(llm: ScriptedLLM) -> MemberCWorkflowExecutor:
    return MemberCWorkflowExecutor(
        planner=TaskPlanner(build_member_c_registry(), llm),
        mcp_client=MemberCMCPClient(remote_caller=dispatch_local_tool),
        material_agent=MaterialAgent(llm=llm),
        interview_agent=InterviewAgent(llm=llm),
        critic_agent=CriticAgent(llm=llm),
    )


def test_executor_runs_mcp_generate_critic_and_one_revision() -> None:
    llm = ScriptedLLM(critic_passed=False)

    workflow = _executor(llm).execute(_task())

    assert workflow.plan_source == "planner"
    assert workflow.status == "completed"
    assert workflow.final_result.startswith("## Advisor Contact Email\nrevised grounded email")
    capabilities = [step.capability for step in workflow.steps]
    assert capabilities == [
        "workflow.plan",
        "profile.build_context",
        "advisor.get_context",
        "knowledge.search",
        "material.generate",
        "critic.review",
        "material.revise",
    ]
    assert workflow.steps[1].tool_call is not None
    assert workflow.steps[1].tool_call.transport == "mcp"
    assert sum(task == "material" for task, _prompt in llm.calls) == 2


def test_executor_skips_conditional_revision_when_critic_passes() -> None:
    llm = ScriptedLLM(critic_passed=True)

    workflow = _executor(llm).execute(_task())

    revision = next(step for step in workflow.steps if step.capability == "material.revise")
    assert revision.status == "skipped"
    assert "Critic passed" in revision.decision_reason
    assert "first draft email" in workflow.final_result
    assert sum(task == "material" for task, _prompt in llm.calls) == 1
