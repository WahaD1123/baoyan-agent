from app.models import Advisor, AdvisorMatchRequest, Document, KnowledgeQuery, StudentProfile
from app.services.member_b_mcp import MemberBMCPClient
from app.tools.member_b_tools import dispatch_local_tool
from app.workflows.member_b_executor import (
    MemberBAdvisorExecutor,
    MemberBKnowledgeExecutor,
    _append_tool_step,
    _apply_advisor_payload,
    _apply_knowledge_payload,
)


class _ToolContext:
    def __init__(self, context) -> None:
        self.context = context


def test_member_b_knowledge_executor_uses_mcp_backed_tools(monkeypatch) -> None:
    document = Document(
        title="CS Summer Camp Notice",
        doc_type="notice",
        content="Applicants need resume, transcript, and interview preparation.",
    )
    monkeypatch.setattr("app.tools.member_b_tools.store.documents", [document])
    monkeypatch.setattr("app.tools.member_b_tools.store.add_workflow", lambda workflow: workflow)

    executor = MemberBKnowledgeExecutor(
        mcp_client=MemberBMCPClient(remote_caller=dispatch_local_tool),
    )
    monkeypatch.setattr(executor.runtime, "is_enabled", lambda: True)

    def fake_agent_run(context) -> str:
        catalog = context.mcp_client.call_tool("knowledge.list_documents", {"limit": 20, "include_content": False})
        context.catalog_count = int(catalog.data.get("count", 0))
        _append_tool_step(context.workflow_steps, "List knowledge documents through MCP", "knowledge.list_documents", catalog)
        result = context.mcp_client.call_tool(
            "knowledge.query",
            {"question": context.query.question, "top_k": context.query.top_k},
        )
        _apply_knowledge_payload(context, result.data)
        _append_tool_step(context.workflow_steps, "Query knowledge base through MCP", "knowledge.query", result)
        return context.answer

    monkeypatch.setattr(executor, "_run_agent", fake_agent_run)
    response = executor.execute(KnowledgeQuery(question="需要哪些材料？", top_k=1))

    assert response.answer
    assert response.workflow.workflow_type == "knowledge"
    assert response.workflow.plan_source == "planner"
    assert any(step.tool_call and step.tool_call.transport == "mcp" for step in response.workflow.steps)


def test_member_b_advisor_executor_uses_mcp_backed_tools(monkeypatch) -> None:
    advisor = Advisor(
        name="Prof. Zhang",
        university="Target University",
        research_areas=["machine learning"],
        summary="Works on reliable ML systems.",
    )
    profile = StudentProfile(
        name="Alice",
        research_interests=["machine learning"],
        preferred_schools=["Target University"],
    )
    monkeypatch.setattr("app.tools.member_b_tools.store.advisors", [advisor])
    monkeypatch.setattr("app.tools.member_b_tools.store.add_workflow", lambda workflow: workflow)

    executor = MemberBAdvisorExecutor(
        mcp_client=MemberBMCPClient(remote_caller=dispatch_local_tool),
    )
    monkeypatch.setattr(executor.runtime, "is_enabled", lambda: True)

    def fake_agent_run(context) -> str:
        catalog = context.mcp_client.call_tool("advisor.list", {"limit": 20})
        _append_tool_step(context.workflow_steps, "List advisors through MCP", "advisor.list", catalog)
        result = context.mcp_client.call_tool(
            "advisor.match",
            {"profile": context.request.profile.model_dump(mode="json"), "top_k": context.request.top_k},
        )
        _apply_advisor_payload(context, result.data)
        _append_tool_step(context.workflow_steps, "Match advisors through MCP", "advisor.match", result)
        return "Prof. Zhang is the top match."

    monkeypatch.setattr(executor, "_run_agent", fake_agent_run)
    response = executor.execute(AdvisorMatchRequest(profile=profile, top_k=1))

    assert response.matches
    assert response.matches[0].advisor.name == "Prof. Zhang"
    assert response.workflow.workflow_type == "advisor_match"
    assert response.workflow.plan_source == "planner"
    assert any(step.tool_call and step.tool_call.transport == "mcp" for step in response.workflow.steps)


def test_member_b_mcp_client_does_not_fallback_by_default() -> None:
    def unavailable(_name: str, _arguments: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("MCP server unavailable")

    client = MemberBMCPClient(remote_caller=unavailable)

    try:
        client.call_tool("knowledge.list_documents", {"limit": 1})
    except TimeoutError as exc:
        assert "unavailable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("MemberBMCPClient should not use local fallback by default")
