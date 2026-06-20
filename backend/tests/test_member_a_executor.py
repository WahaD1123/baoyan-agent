from app.models import StudentProfile
from app.services.member_a_mcp import MemberAMCPClient
from app.tools.member_a_tools import dispatch_local_tool
from app.workflows.member_a_executor import MemberAPlanningExecutor


def test_member_a_executor_uses_mcp_backed_tools_and_returns_plan_response() -> None:
    profile = StudentProfile(
        name="Alice",
        university="Xiamen University",
        major="Computer Science",
        rank_percent=8,
        gpa=3.8,
        research_interests=["machine learning", "agent systems"],
        projects=["Multi-agent application assistant"],
        preferred_schools=["Shanghai Jiao Tong University", "Zhejiang University"],
    )

    executor = MemberAPlanningExecutor(
        mcp_client=MemberAMCPClient(remote_caller=dispatch_local_tool),
    )

    response = executor.execute(profile)

    assert response.plan
    assert response.analysis.overall_score >= 0
    assert response.recommendations
    assert response.timeline
    assert response.workflow.workflow_type == "planning"
    assert any(step.tool_call is not None for step in response.workflow.steps)
    assert any(
        step.tool_call is not None and step.tool_call.transport == "mcp"
        for step in response.workflow.steps
    )
