from typing import Literal

from pydantic import BaseModel, Field, model_validator


PlanStepKind = Literal["tool", "agent"]
PlanCondition = Literal["always", "critic_failed"]


class PlanStep(BaseModel):
    kind: PlanStepKind
    capability: str
    condition: PlanCondition = "always"
    reason: str = ""


class WorkflowPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_sequence(self) -> "WorkflowPlan":
        generation_indexes = [
            index for index, step in enumerate(self.steps)
            if step.capability.endswith(".generate")
        ]
        critic_indexes = [
            index for index, step in enumerate(self.steps)
            if step.capability == "critic.review"
        ]
        if critic_indexes and not any(index < critic_indexes[0] for index in generation_indexes):
            raise ValueError("generation step must precede critic review")

        revisions = [
            (index, step) for index, step in enumerate(self.steps)
            if step.capability.endswith(".revise")
        ]
        if len(revisions) > 1:
            raise ValueError("only one revision step is allowed")
        if revisions:
            index, step = revisions[0]
            if step.condition != "critic_failed":
                raise ValueError("revision step must be conditional on critic failure")
            if not critic_indexes or index < critic_indexes[0]:
                raise ValueError("critic review must precede revision")
        return self

    def validate_capabilities(self, allowed: set[str]) -> None:
        unknown = sorted({step.capability for step in self.steps} - allowed)
        if unknown:
            raise ValueError(f"Unregistered capability: {', '.join(unknown)}")
