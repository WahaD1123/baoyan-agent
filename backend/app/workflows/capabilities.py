from dataclasses import dataclass
from typing import Literal

from app.workflows.planning import WorkflowPlan


CapabilityKind = Literal["tool", "agent"]


@dataclass(frozen=True)
class Capability:
    name: str
    kind: CapabilityKind
    description: str
    goals: frozenset[str]


class CapabilityRegistry:
    def __init__(self, capabilities: list[Capability]) -> None:
        self._capabilities = {capability.name: capability for capability in capabilities}

    def names_for_goal(self, goal: str) -> set[str]:
        return {
            capability.name
            for capability in self._capabilities.values()
            if goal in capability.goals
        }

    def manifest_for_goal(self, goal: str) -> list[dict[str, str]]:
        return [
            {
                "name": capability.name,
                "kind": capability.kind,
                "description": capability.description,
            }
            for capability in self._capabilities.values()
            if goal in capability.goals
        ]

    def validate_plan(self, goal: str, plan: WorkflowPlan) -> None:
        allowed = {
            name: capability
            for name, capability in self._capabilities.items()
            if goal in capability.goals
        }
        plan.validate_capabilities(set(allowed))
        for step in plan.steps:
            if step.kind != allowed[step.capability].kind:
                raise ValueError(
                    f"Capability kind mismatch for {step.capability}: "
                    f"expected {allowed[step.capability].kind}, got {step.kind}"
                )

        generation = [step for step in plan.steps if step.capability.endswith(".generate")]
        critics = [step for step in plan.steps if step.capability == "critic.review"]
        revisions = [step for step in plan.steps if step.capability.endswith(".revise")]
        if len(generation) != 1 or len(critics) != 1 or len(revisions) != 1:
            raise ValueError("Plan must contain exactly one generate, critic, and revise step")


def build_member_c_registry() -> CapabilityRegistry:
    material_goals = frozenset(
        {
            "generate_advisor_email",
            "generate_resume_highlights",
            "generate_statement",
        }
    )
    all_goals = material_goals | {"generate_interview"}
    return CapabilityRegistry(
        [
            Capability(
                "profile.build_context",
                "tool",
                "Normalize the supplied student profile into grounded generation context.",
                all_goals,
            ),
            Capability(
                "advisor.get_context",
                "tool",
                "Build grounded advisor context when an advisor is supplied.",
                frozenset({"generate_advisor_email"}),
            ),
            Capability(
                "knowledge.search",
                "tool",
                "Retrieve relevant application evidence from the local knowledge base.",
                material_goals,
            ),
            Capability(
                "interview.retrieve_evidence",
                "tool",
                "Retrieve project, direction, and interview evidence.",
                frozenset({"generate_interview"}),
            ),
            Capability(
                "material.generate",
                "agent",
                "Generate the requested application material from collected context.",
                material_goals,
            ),
            Capability(
                "interview.generate",
                "agent",
                "Generate categorized mock interview questions from collected context.",
                frozenset({"generate_interview"}),
            ),
            Capability(
                "critic.review",
                "agent",
                "Return a structured groundedness and quality review.",
                all_goals,
            ),
            Capability(
                "material.revise",
                "agent",
                "Revise material once when the Critic rejects it.",
                material_goals,
            ),
            Capability(
                "interview.revise",
                "agent",
                "Revise interview questions once when the Critic rejects them.",
                frozenset({"generate_interview"}),
            ),
        ]
    )
