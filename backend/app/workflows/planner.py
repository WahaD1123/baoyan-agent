import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.workflows.capabilities import CapabilityRegistry
from app.workflows.planning import PlanStep, WorkflowPlan


class PlannerLLM(Protocol):
    def generate(self, prompt: str, task: str = "general") -> str: ...


@dataclass(frozen=True)
class PlanningResult:
    plan: WorkflowPlan
    source: Literal["planner", "fallback"]
    summary: str


class TaskPlanner:
    def __init__(self, registry: CapabilityRegistry, llm: PlannerLLM | None = None) -> None:
        self.registry = registry
        if llm is None:
            from app.services.llm import get_llm_provider

            llm = get_llm_provider()
        self.llm = llm

    def plan(self, goal: str, context: dict[str, Any]) -> PlanningResult:
        try:
            raw = self.llm.generate(self._prompt(goal, context), task="workflow_planner")
            plan = WorkflowPlan.model_validate(_extract_json(raw))
            if plan.goal != goal:
                raise ValueError("Planner changed the requested goal")
            self.registry.validate_plan(goal, plan)
            _validate_required_capabilities(goal, context, plan)
            return PlanningResult(
                plan=plan,
                source="planner",
                summary="Qwen planner produced a validated allow-listed plan.",
            )
        except Exception as exc:
            plan = build_fallback_plan(goal, context)
            self.registry.validate_plan(goal, plan)
            _validate_required_capabilities(goal, context, plan)
            return PlanningResult(
                plan=plan,
                source="fallback",
                summary=f"Planner fallback: {exc.__class__.__name__}",
            )

    def _prompt(self, goal: str, context: dict[str, Any]) -> str:
        manifest = self.registry.manifest_for_goal(goal)
        required = sorted(_required_capabilities(goal, context))
        return (
            "You are a constrained workflow planner. Return one JSON object only. "
            "Use only capabilities in the manifest, use at most 8 steps, generate before "
            "critic.review, and put at most one *.revise step after the critic with "
            "condition=critic_failed.\n"
            f"goal={goal}\n"
            f"context={json.dumps(context, ensure_ascii=False)}\n"
            f"capabilities={json.dumps(manifest, ensure_ascii=False)}\n"
            f"required_capabilities={json.dumps(required)}\n"
            '{"schema":{"goal":"...","steps":[{"kind":"tool|agent",'
            '"capability":"...","condition":"always|critic_failed",'
            '"reason":"short public rationale"}]}}'
        )


def build_fallback_plan(goal: str, context: dict[str, Any]) -> WorkflowPlan:
    steps = [PlanStep(kind="tool", capability="profile.build_context")]
    if goal == "generate_advisor_email" and context.get("has_advisor"):
        steps.append(PlanStep(kind="tool", capability="advisor.get_context"))
    if goal != "generate_interview" and context.get("has_knowledge"):
        steps.append(PlanStep(kind="tool", capability="knowledge.search"))
    if goal == "generate_interview":
        if context.get("has_knowledge"):
            steps.append(PlanStep(kind="tool", capability="interview.retrieve_evidence"))
        generation = "interview.generate"
        revision = "interview.revise"
    else:
        generation = "material.generate"
        revision = "material.revise"
    steps.extend(
        [
            PlanStep(kind="agent", capability=generation),
            PlanStep(kind="agent", capability="critic.review"),
            PlanStep(kind="agent", capability=revision, condition="critic_failed"),
        ]
    )
    return WorkflowPlan(goal=goal, steps=steps)


def _extract_json(raw: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("Planner did not return JSON")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Planner JSON must be an object")
    return data


def _required_capabilities(goal: str, context: dict[str, Any]) -> set[str]:
    required = {"profile.build_context"}
    if goal == "generate_advisor_email" and context.get("has_advisor"):
        required.add("advisor.get_context")
    if context.get("has_knowledge"):
        required.add(
            "interview.retrieve_evidence"
            if goal == "generate_interview"
            else "knowledge.search"
        )
    return required


def _validate_required_capabilities(
    goal: str,
    context: dict[str, Any],
    plan: WorkflowPlan,
) -> None:
    selected = {step.capability for step in plan.steps}
    missing = sorted(_required_capabilities(goal, context) - selected)
    if missing:
        raise ValueError(f"Planner omitted required capabilities: {', '.join(missing)}")
