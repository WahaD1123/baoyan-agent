from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.tools.member_b_tools import (
    advisor_add_url,
    advisor_list,
    advisor_match,
    knowledge_add_text,
    knowledge_add_url,
    knowledge_list_documents,
    knowledge_query,
)
from app.tools.member_c_tools import (
    build_advisor_context,
    build_profile_context,
    retrieve_interview_evidence,
    search_knowledge,
)


settings = get_settings()
mcp = FastMCP(
    name="baoyan-agent-tools",
    instructions=(
        "Baoyan Agent MCP tools. Member B exposes knowledge-base ingestion, RAG QA, "
        "advisor crawling, and advisor matching. Member C uses grounded profile, "
        "advisor, knowledge, and interview helpers."
    ),
    host=settings.mcp_server_host,
    port=settings.mcp_server_port,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)


@mcp.tool(name="knowledge.add_text", structured_output=True)
def mcp_knowledge_add_text(
    title: str,
    content: str,
    doc_type: str = "other",
    source: str = "mcp_text",
) -> dict[str, Any]:
    return knowledge_add_text(title=title, content=content, doc_type=doc_type, source=source)  # type: ignore[arg-type]


@mcp.tool(name="knowledge.add_url", structured_output=True)
def mcp_knowledge_add_url(url: str, doc_type: str = "notice", title: str = "") -> dict[str, Any]:
    return knowledge_add_url(url=url, doc_type=doc_type, title=title)  # type: ignore[arg-type]


@mcp.tool(name="knowledge.query", structured_output=True)
def mcp_knowledge_query(question: str, top_k: int = 3) -> dict[str, Any]:
    return knowledge_query(question=question, top_k=top_k)


@mcp.tool(name="knowledge.list_documents", structured_output=True)
def mcp_knowledge_list_documents(limit: int = 20, include_content: bool = False) -> dict[str, Any]:
    return knowledge_list_documents(limit=limit, include_content=include_content)


@mcp.tool(name="advisor.add_url", structured_output=True)
def mcp_advisor_add_url(url: str, title: str = "") -> dict[str, Any]:
    return advisor_add_url(url=url, title=title)


@mcp.tool(name="advisor.list", structured_output=True)
def mcp_advisor_list(limit: int = 20) -> dict[str, Any]:
    return advisor_list(limit=limit)


@mcp.tool(name="advisor.match", structured_output=True)
def mcp_advisor_match(profile: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    return advisor_match(profile=profile, top_k=top_k)


@mcp.tool(name="profile.build_context", structured_output=True)
def profile_build_context(profile: dict[str, Any]) -> dict[str, Any]:
    return build_profile_context(profile)


@mcp.tool(name="advisor.get_context", structured_output=True)
def advisor_get_context(advisor: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_advisor_context(advisor)


@mcp.tool(name="knowledge.search", structured_output=True)
def knowledge_search(query: str, top_k: int = 3) -> dict[str, Any]:
    return search_knowledge(query, top_k)


@mcp.tool(name="interview.retrieve_evidence", structured_output=True)
def interview_evidence(
    profile: dict[str, Any],
    target_school: str,
    direction: str,
    top_k: int = 4,
) -> dict[str, Any]:
    return retrieve_interview_evidence(profile, target_school, direction, top_k)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
