import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from time import perf_counter
from typing import Any, Literal

import httpx

from app.core.config import get_settings
from app.tools.member_c_tools import dispatch_local_tool, member_c_tool_names


RemoteCaller = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class MCPToolResult:
    data: dict[str, Any]
    transport: Literal["mcp", "local_fallback"]
    duration_ms: int
    fallback_reason: str | None = None


class MemberCMCPClient:
    def __init__(
        self,
        server_url: str | None = None,
        timeout_seconds: float | None = None,
        local_fallback: bool | None = None,
        remote_caller: RemoteCaller | None = None,
    ) -> None:
        settings = get_settings()
        self.server_url = server_url or settings.mcp_server_url
        self.timeout_seconds = timeout_seconds or settings.mcp_timeout_seconds
        self.local_fallback = settings.mcp_local_fallback if local_fallback is None else local_fallback
        if remote_caller is None and os.getenv("PYTEST_CURRENT_TEST"):
            self._remote_caller = dispatch_local_tool
        else:
            self._remote_caller = remote_caller or self._call_remote

    def call_tool(self, name: str, arguments: dict[str, Any]) -> MCPToolResult:
        if name not in member_c_tool_names():
            raise ValueError(f"Unknown Member C tool: {name}")

        started = perf_counter()
        try:
            data = self._remote_caller(name, arguments)
            return MCPToolResult(
                data=data,
                transport="mcp",
                duration_ms=_elapsed_ms(started),
            )
        except Exception as exc:
            if not self.local_fallback:
                raise
            data = dispatch_local_tool(name, arguments)
            return MCPToolResult(
                data=data,
                transport="local_fallback",
                duration_ms=_elapsed_ms(started),
                fallback_reason=f"{type(exc).__name__}: {exc}",
            )

    def _call_remote(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._call_remote_async(name, arguments))
        raise RuntimeError("MemberCMCPClient.call_tool must run outside an active event loop")

    async def _call_remote_async(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
        except ModuleNotFoundError as exc:
            raise RuntimeError("MCP client dependencies are not installed. Run pip install -r requirements.txt") from exc

        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            async with streamable_http_client(
                self.server_url,
                http_client=http_client,
            ) as (read_stream, write_stream, _get_session_id):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
                ) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(_content_text(result.content) or f"MCP tool failed: {name}")
        if result.structuredContent is not None:
            return result.structuredContent

        text = _content_text(result.content)
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise TypeError(f"MCP tool {name} returned non-object JSON")
        return parsed


def _content_text(content: list[Any]) -> str:
    return "\n".join(
        item.text
        for item in content
        if getattr(item, "type", None) == "text" and getattr(item, "text", None)
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
