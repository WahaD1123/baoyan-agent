from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents_sdk.runtime import AgentSdkRuntimeUnavailable, get_agent_sdk_runtime
from app.models import (
    Advisor,
    AdvisorMatchRequest,
    AdvisorMatchResponse,
    AdvisorMatchResult,
    AgentResult,
    Document,
    KnowledgeQuery,
    KnowledgeResponse,
    RetrievedChunk,
    ToolCallTrace,
    WorkflowRun,
    WorkflowStep,
)
from app.services.llm import model_name_for_task
from app.services.member_b_mcp import MCPToolResult, MemberBMCPClient

try:
    from agents import Agent, ModelSettings, RunContextWrapper, Runner, function_tool
except ModuleNotFoundError:  # pragma: no cover
    Agent = None  # type: ignore[assignment]
    ModelSettings = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]

    class RunContextWrapper:  # type: ignore[no-redef]
        pass

    def function_tool(func):  # type: ignore[no-untyped-def]
        return func


UTC = timezone.utc


@dataclass
class KnowledgeAgentContext:
    query: KnowledgeQuery
    mcp_client: MemberBMCPClient
    workflow_steps: list[WorkflowStep] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    chunks: list[RetrievedChunk] = field(default_factory=list)
    answer: str = ""
    catalog_count: int = 0


@dataclass
class AdvisorAgentContext:
    request: AdvisorMatchRequest
    mcp_client: MemberBMCPClient
    workflow_steps: list[WorkflowStep] = field(default_factory=list)
    advisors: list[Advisor] = field(default_factory=list)
    matches: list[AdvisorMatchResult] = field(default_factory=list)


@function_tool
def knowledge_catalog_tool(ctx: RunContextWrapper[KnowledgeAgentContext], limit: int = 20) -> dict[str, Any]:
    """List knowledge-base documents before answering a question."""
    result = ctx.context.mcp_client.call_tool(
        "knowledge.list_documents",
        {"limit": limit, "include_content": False},
    )
    ctx.context.catalog_count = int(result.data.get("count", 0))
    _append_tool_step(ctx.context.workflow_steps, "List knowledge documents through MCP", "knowledge.list_documents", result)
    return result.data


@function_tool
def knowledge_query_tool(ctx: RunContextWrapper[KnowledgeAgentContext]) -> dict[str, Any]:
    """Answer the user's question with the Member B knowledge-base QA tool."""
    result = ctx.context.mcp_client.call_tool(
        "knowledge.query",
        {
            "question": ctx.context.query.question,
            "top_k": ctx.context.query.top_k,
        },
    )
    _apply_knowledge_payload(ctx.context, result.data)
    _append_tool_step(ctx.context.workflow_steps, "Query knowledge base through MCP", "knowledge.query", result)
    return result.data


@function_tool
def advisor_catalog_tool(ctx: RunContextWrapper[AdvisorAgentContext], limit: int = 20) -> dict[str, Any]:
    """List advisor candidates before matching."""
    result = ctx.context.mcp_client.call_tool("advisor.list", {"limit": limit})
    ctx.context.advisors = [Advisor.model_validate(item) for item in result.data.get("advisors", [])]
    _append_tool_step(ctx.context.workflow_steps, "List advisors through MCP", "advisor.list", result)
    return result.data


@function_tool
def advisor_match_tool(ctx: RunContextWrapper[AdvisorAgentContext]) -> dict[str, Any]:
    """Match advisors against the supplied student profile."""
    result = ctx.context.mcp_client.call_tool(
        "advisor.match",
        {
            "profile": ctx.context.request.profile.model_dump(mode="json"),
            "top_k": ctx.context.request.top_k,
        },
    )
    _apply_advisor_payload(ctx.context, result.data)
    _append_tool_step(ctx.context.workflow_steps, "Match advisors through MCP", "advisor.match", result)
    return result.data


class MemberBKnowledgeExecutor:
    def __init__(self, mcp_client: MemberBMCPClient | None = None) -> None:
        self.mcp_client = mcp_client or MemberBMCPClient()
        self.runtime = get_agent_sdk_runtime()

    def execute(self, query: KnowledgeQuery) -> KnowledgeResponse:
        context = KnowledgeAgentContext(query=query, mcp_client=self.mcp_client)
        if not self.runtime.is_enabled():
            raise AgentSdkRuntimeUnavailable("OpenAI Agents SDK runtime is required for Member B knowledge execution")

        final_answer = self._run_agent(context)
        if not context.answer:
            raise RuntimeError("Member B knowledge agent did not call knowledge.query")

        workflow = WorkflowRun(
            workflow_type="knowledge",
            status="completed",
            steps=[
                *context.workflow_steps,
                _agent_step(
                    name="Synthesize knowledge answer",
                    capability="knowledge.answer.generate",
                    agent_name="MemberBKnowledgeAgent",
                    input_summary=query.question,
                    output=final_answer,
                    references=[document.title for document in context.documents],
                    model_task="knowledge",
                    reason="OpenAI Agents SDK generated the user-facing answer from MCP evidence.",
                ),
            ],
            final_result=final_answer,
            plan_source="planner",
            planner_summary="OpenAI Agents SDK orchestrated Member B knowledge MCP tools.",
        )
        return KnowledgeResponse(
            answer=final_answer,
            documents=context.documents,
            chunks=context.chunks,
            workflow=workflow,
        )

    def _run_agent(self, context: KnowledgeAgentContext) -> str:
        if Agent is None or ModelSettings is None or Runner is None:
            raise AgentSdkRuntimeUnavailable("OpenAI Agents SDK is not installed")
        agent = Agent[KnowledgeAgentContext](
            name="MemberBKnowledgeAgent",
            model=self.runtime.build_model(),
            model_settings=ModelSettings(temperature=0.2),
            instructions=(
                "You are the knowledge-base orchestration agent for a CS baoyan assistant. "
                "Call knowledge_catalog_tool first, then knowledge_query_tool. "
                "Write the final answer in Chinese for the student. Keep citations and missing-information notes. "
                "Do not reveal internal MCP, tool, or SDK details."
            ),
            tools=[knowledge_catalog_tool, knowledge_query_tool],
        )
        result = Runner.run_sync(
            agent,
            f"User question: {context.query.question}\nAnswer with knowledge-base evidence. top_k={context.query.top_k}.",
            context=context,
            max_turns=5,
        )
        return str(result.final_output).strip()


class MemberBAdvisorExecutor:
    def __init__(self, mcp_client: MemberBMCPClient | None = None) -> None:
        self.mcp_client = mcp_client or MemberBMCPClient()
        self.runtime = get_agent_sdk_runtime()

    def execute(self, request: AdvisorMatchRequest) -> AdvisorMatchResponse:
        context = AdvisorAgentContext(request=request, mcp_client=self.mcp_client)
        if not self.runtime.is_enabled():
            raise AgentSdkRuntimeUnavailable("OpenAI Agents SDK runtime is required for Member B advisor execution")

        final_summary = self._run_agent(context)
        if not context.matches:
            raise RuntimeError("Member B advisor agent did not call advisor.match")

        workflow = WorkflowRun(
            workflow_type="advisor_match",
            status="completed",
            steps=[
                *context.workflow_steps,
                _agent_step(
                    name="Synthesize advisor matching summary",
                    capability="advisor.match.generate",
                    agent_name="MemberBAdvisorAgent",
                    input_summary=f"profile={request.profile.name}, top_k={request.top_k}",
                    output=final_summary,
                    references=[f"{item.advisor.name} - {item.advisor.university}" for item in context.matches],
                    model_task="advisor",
                    reason="OpenAI Agents SDK generated the advisor matching summary from MCP results.",
                ),
            ],
            final_result=final_summary,
            plan_source="planner",
            planner_summary="OpenAI Agents SDK orchestrated Member B advisor MCP tools.",
        )
        return AdvisorMatchResponse(matches=context.matches, workflow=workflow)

    def _run_agent(self, context: AdvisorAgentContext) -> str:
        if Agent is None or ModelSettings is None or Runner is None:
            raise AgentSdkRuntimeUnavailable("OpenAI Agents SDK is not installed")
        agent = Agent[AdvisorAgentContext](
            name="MemberBAdvisorAgent",
            model=self.runtime.build_model(),
            model_settings=ModelSettings(temperature=0.2),
            instructions=(
                "You are the advisor-matching orchestration agent for a CS baoyan assistant. "
                "Call advisor_catalog_tool first, then advisor_match_tool. "
                "Write a concise Chinese summary of the top matches, risks, and contact strategy. "
                "Do not reveal internal MCP, tool, or SDK details."
            ),
            tools=[advisor_catalog_tool, advisor_match_tool],
        )
        result = Runner.run_sync(
            agent,
            f"Student profile: {context.request.profile.model_dump_json()}\nMatch the top {context.request.top_k} advisors.",
            context=context,
            max_turns=5,
        )
        return str(result.final_output).strip()


def execute_knowledge_query(query: KnowledgeQuery) -> KnowledgeResponse:
    return MemberBKnowledgeExecutor().execute(query)


def execute_advisor_match(request: AdvisorMatchRequest) -> AdvisorMatchResponse:
    return MemberBAdvisorExecutor().execute(request)


def _apply_knowledge_payload(context: KnowledgeAgentContext, payload: dict[str, Any]) -> None:
    context.answer = str(payload.get("answer", ""))
    context.documents = [Document.model_validate(item) for item in payload.get("documents", [])]
    context.chunks = [RetrievedChunk.model_validate(item) for item in payload.get("chunks", [])]


def _apply_advisor_payload(context: AdvisorAgentContext, payload: dict[str, Any]) -> None:
    context.matches = [AdvisorMatchResult.model_validate(item) for item in payload.get("matches", [])]
    context.advisors = [item.advisor for item in context.matches] or context.advisors


def _append_tool_step(
    steps: list[WorkflowStep],
    name: str,
    capability: str,
    result: MCPToolResult,
) -> None:
    started_at = datetime.now(UTC)
    steps.append(
        WorkflowStep(
            name=name,
            status="completed",
            step_type="tool",
            capability=capability,
            decision_reason="Member B context collection through MCP.",
            started_at=started_at,
            completed_at=started_at,
            duration_ms=result.duration_ms,
            tool_call=ToolCallTrace(
                tool_name=capability,
                transport=result.transport,
                arguments_summary="see MCP request",
                result_summary=_json_summary(result.data),
                duration_ms=result.duration_ms,
                fallback_reason=result.fallback_reason or "",
            ),
        )
    )


def _agent_step(
    name: str,
    capability: str,
    agent_name: str,
    input_summary: str,
    output: str,
    references: list[str],
    model_task: str,
    reason: str,
) -> WorkflowStep:
    started_at = datetime.now(UTC)
    return WorkflowStep(
        name=name,
        status="completed",
        step_type="agent",
        capability=capability,
        decision_reason=reason,
        model_name=model_name_for_task(model_task),
        started_at=started_at,
        completed_at=started_at,
        duration_ms=0,
        agent_result=AgentResult(
            agent_name=agent_name,
            input_summary=input_summary,
            output=output,
            references=references,
        ),
    )


def _json_summary(value: object, limit: int = 420) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."
