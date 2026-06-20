from app.workflows.capabilities import build_member_c_registry
from app.workflows.planner import TaskPlanner


class StubPlannerLLM:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, task: str = "general") -> str:
        self.calls.append((prompt, task))
        return self.output


def test_registry_exposes_goal_specific_capabilities() -> None:
    registry = build_member_c_registry()

    material_names = registry.names_for_goal("generate_advisor_email")
    interview_names = registry.names_for_goal("generate_interview")

    assert "advisor.get_context" in material_names
    assert "interview.retrieve_evidence" not in material_names
    assert "interview.retrieve_evidence" in interview_names
    assert "material.generate" not in interview_names


def test_planner_accepts_valid_qwen_json_plan() -> None:
    llm = StubPlannerLLM(
        """{
          "goal": "generate_advisor_email",
          "steps": [
            {"kind": "tool", "capability": "profile.build_context"},
            {"kind": "tool", "capability": "advisor.get_context"},
            {"kind": "agent", "capability": "material.generate"},
            {"kind": "agent", "capability": "critic.review"},
            {"kind": "agent", "capability": "material.revise", "condition": "critic_failed"}
          ]
        }"""
    )
    planner = TaskPlanner(build_member_c_registry(), llm)

    result = planner.plan(
        "generate_advisor_email",
        {"has_advisor": True, "has_knowledge": False},
    )

    assert result.source == "planner"
    assert result.plan.steps[1].capability == "advisor.get_context"
    assert llm.calls[0][1] == "workflow_planner"


def test_planner_uses_context_aware_fallback_for_invalid_capability() -> None:
    llm = StubPlannerLLM(
        '{"goal":"generate_advisor_email","steps":'
        '[{"kind":"tool","capability":"shell.execute"}]}'
    )
    planner = TaskPlanner(build_member_c_registry(), llm)

    result = planner.plan(
        "generate_advisor_email",
        {"has_advisor": False, "has_knowledge": False},
    )
    names = [step.capability for step in result.plan.steps]

    assert result.source == "fallback"
    assert names == [
        "profile.build_context",
        "material.generate",
        "critic.review",
        "material.revise",
    ]
    assert result.plan.steps[-1].condition == "critic_failed"


def test_planner_falls_back_when_required_critic_is_missing() -> None:
    llm = StubPlannerLLM(
        '{"goal":"generate_statement","steps":['
        '{"kind":"tool","capability":"profile.build_context"},'
        '{"kind":"agent","capability":"material.generate"}]}'
    )
    planner = TaskPlanner(build_member_c_registry(), llm)

    result = planner.plan(
        "generate_statement",
        {"has_advisor": False, "has_knowledge": False},
    )

    assert result.source == "fallback"
    assert [step.capability for step in result.plan.steps][-2:] == [
        "critic.review",
        "material.revise",
    ]


def test_planner_falls_back_when_capability_kind_is_wrong() -> None:
    llm = StubPlannerLLM(
        '{"goal":"generate_interview","steps":['
        '{"kind":"agent","capability":"profile.build_context"},'
        '{"kind":"agent","capability":"interview.generate"},'
        '{"kind":"agent","capability":"critic.review"},'
        '{"kind":"agent","capability":"interview.revise","condition":"critic_failed"}]}'
    )
    planner = TaskPlanner(build_member_c_registry(), llm)

    result = planner.plan(
        "generate_interview",
        {"has_advisor": False, "has_knowledge": False},
    )

    assert result.source == "fallback"
    assert result.plan.steps[0].kind == "tool"


def test_planner_requires_context_capabilities_before_generation() -> None:
    llm = StubPlannerLLM(
        '{"goal":"generate_advisor_email","steps":['
        '{"kind":"tool","capability":"advisor.get_context"},'
        '{"kind":"tool","capability":"knowledge.search"},'
        '{"kind":"agent","capability":"material.generate"},'
        '{"kind":"agent","capability":"critic.review"},'
        '{"kind":"agent","capability":"material.revise","condition":"critic_failed"}]}'
    )
    planner = TaskPlanner(build_member_c_registry(), llm)

    result = planner.plan(
        "generate_advisor_email",
        {"has_advisor": True, "has_knowledge": True},
    )

    assert result.source == "fallback"
    assert result.plan.steps[0].capability == "profile.build_context"
