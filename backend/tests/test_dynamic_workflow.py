import pytest
from pydantic import ValidationError

from app.models import WorkflowRun, WorkflowStep
from app.workflows.planning import PlanStep, WorkflowPlan


ALLOWED = {
    "profile.build_context",
    "advisor.get_context",
    "knowledge.search",
    "material.generate",
    "critic.review",
    "material.revise",
}


def test_plan_accepts_registered_generate_review_flow() -> None:
    plan = WorkflowPlan(
        goal="generate_advisor_email",
        steps=[
            PlanStep(kind="tool", capability="profile.build_context"),
            PlanStep(kind="agent", capability="material.generate"),
            PlanStep(kind="agent", capability="critic.review"),
            PlanStep(kind="agent", capability="material.revise", condition="critic_failed"),
        ],
    )

    plan.validate_capabilities(ALLOWED)

    assert plan.steps[-1].condition == "critic_failed"


def test_plan_rejects_unregistered_capability() -> None:
    plan = WorkflowPlan(
        goal="generate_advisor_email",
        steps=[PlanStep(kind="tool", capability="shell.execute")],
    )

    with pytest.raises(ValueError, match="Unregistered capability"):
        plan.validate_capabilities(ALLOWED)


def test_plan_rejects_more_than_eight_steps() -> None:
    with pytest.raises(ValidationError):
        WorkflowPlan(
            goal="generate_advisor_email",
            steps=[
                PlanStep(kind="tool", capability="profile.build_context")
                for _ in range(9)
            ],
        )


def test_plan_rejects_review_before_generation() -> None:
    with pytest.raises(ValidationError, match="generation step must precede critic review"):
        WorkflowPlan(
            goal="generate_advisor_email",
            steps=[
                PlanStep(kind="agent", capability="critic.review"),
                PlanStep(kind="agent", capability="material.generate"),
            ],
        )


def test_old_workflow_payload_gets_trace_defaults() -> None:
    workflow = WorkflowRun.model_validate(
        {
            "workflow_type": "planning",
            "steps": [{"name": "legacy step"}],
            "final_result": "done",
        }
    )

    step: WorkflowStep = workflow.steps[0]
    assert step.step_type == "agent"
    assert step.capability == ""
    assert step.duration_ms == 0
    assert step.tool_call is None
    assert workflow.plan_source == "fixed"
