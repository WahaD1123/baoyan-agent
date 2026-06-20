import pytest

from app.models import Advisor, StudentProfile
from app.services.member_c_mcp import MemberCMCPClient
from app.services.store import store
from app.tools.member_c_tools import (
    build_advisor_context,
    build_profile_context,
    dispatch_local_tool,
    retrieve_interview_evidence,
    search_knowledge,
)


def _profile() -> StudentProfile:
    return StudentProfile(
        name="Alice",
        university="Xiamen University",
        major="Computer Science",
        rank_percent=6,
        research_interests=["machine learning", "agent systems"],
        projects=["Multi-agent application assistant"],
        competitions=["Programming contest"],
    )


def test_profile_tool_returns_grounded_serializable_context() -> None:
    result = build_profile_context(_profile().model_dump(mode="json"))

    assert result["name"] == "Alice"
    assert result["rank_percent"] == 6
    assert result["research_interests"] == ["machine learning", "agent systems"]
    assert "Multi-agent application assistant" in result["evidence"]


def test_advisor_tool_marks_missing_and_present_context() -> None:
    missing = build_advisor_context(None)
    present = build_advisor_context(
        Advisor(
            name="Prof. Wang",
            university="Target University",
            research_areas=["machine learning"],
            summary="Works on reliable agents.",
        ).model_dump(mode="json")
    )

    assert missing == {"available": False, "message": "No advisor was supplied."}
    assert present["available"] is True
    assert present["name"] == "Prof. Wang"
    assert present["research_areas"] == ["machine learning"]


def test_knowledge_tool_returns_ranked_evidence() -> None:
    result = search_knowledge("machine learning advisor", top_k=2)

    assert result["query"] == "machine learning advisor"
    assert len(result["evidence"]) <= 2
    assert all("document_title" in item and "text" in item for item in result["evidence"])


def test_interview_tool_combines_profile_and_retrieved_evidence() -> None:
    result = retrieve_interview_evidence(
        _profile().model_dump(mode="json"),
        target_school="Target University",
        direction="AI systems",
        top_k=2,
    )

    assert result["target_school"] == "Target University"
    assert result["direction"] == "AI systems"
    assert result["projects"] == ["Multi-agent application assistant"]
    assert len(result["knowledge_evidence"]) <= 2


def test_local_dispatch_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError, match="Unknown Member C tool"):
        dispatch_local_tool("shell.execute", {})


def test_mcp_client_returns_remote_structured_result() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def remote(name: str, arguments: dict[str, object]) -> dict[str, object]:
        calls.append((name, arguments))
        return {"available": True, "name": "Prof. Wang"}

    client = MemberCMCPClient(remote_caller=remote)
    result = client.call_tool("advisor.get_context", {"advisor": None})

    assert calls == [("advisor.get_context", {"advisor": None})]
    assert result.data["name"] == "Prof. Wang"
    assert result.transport == "mcp"
    assert result.fallback_reason is None
    assert result.duration_ms >= 0


def test_mcp_client_falls_back_to_local_dispatcher() -> None:
    def unavailable(_name: str, _arguments: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("MCP server timed out")

    client = MemberCMCPClient(remote_caller=unavailable, local_fallback=True)
    result = client.call_tool(
        "profile.build_context",
        {"profile": _profile().model_dump(mode="json")},
    )

    assert result.data["name"] == "Alice"
    assert result.transport == "local_fallback"
    assert "timed out" in (result.fallback_reason or "")


def test_mcp_client_can_disable_local_fallback() -> None:
    def unavailable(_name: str, _arguments: dict[str, object]) -> dict[str, object]:
        raise ConnectionError("down")

    client = MemberCMCPClient(remote_caller=unavailable, local_fallback=False)

    with pytest.raises(ConnectionError, match="down"):
        client.call_tool("advisor.get_context", {"advisor": None})


def test_knowledge_tool_refreshes_shared_json_store(monkeypatch: pytest.MonkeyPatch) -> None:
    refresh_calls: list[bool] = []

    def refresh() -> list[object]:
        refresh_calls.append(True)
        return store.documents

    monkeypatch.setattr(store, "refresh_documents", refresh, raising=False)
    search_knowledge("agent systems", top_k=1)

    assert refresh_calls == [True]
