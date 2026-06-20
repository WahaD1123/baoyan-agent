from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.tools.member_c_tools import (
    build_advisor_context,
    build_profile_context,
    retrieve_interview_evidence,
    search_knowledge,
)


settings = get_settings()
mcp = FastMCP(
    name="baoyan-member-c-tools",
    instructions="Grounded profile, advisor, knowledge, and interview tools for Member C workflows.",
    host=settings.mcp_server_host,
    port=settings.mcp_server_port,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)


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
