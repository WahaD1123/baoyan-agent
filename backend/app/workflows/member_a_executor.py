from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter

from agents import Agent, ModelSettings, RunContextWrapper, Runner, function_tool

from app.agents_sdk.runtime import AgentSdkRuntimeUnavailable, get_agent_sdk_runtime
from app.models import (
    AgentResult,
    PlanResponse,
    ProfileAnalysis,
    SchoolRecommendation,
    StudentProfile,
    ToolCallTrace,
    WorkflowRun,
    WorkflowStep,
)
from app.services.llm import get_llm_provider
from app.services.member_a_mcp import MemberAMCPClient, MCPToolResult
from app.services.planning_service import (
    analyze_profile,
    build_timeline,
    format_plan_summary,
    recommend_schools,
    retrieve_planning_evidence,
)
from app.services.store import store
from app.tools.member_a_tools import chunk_titles, validate_analysis, validate_recommendations


@dataclass
class PlanningAgentContext:
    profile: StudentProfile
    mcp_client: MemberAMCPClient
    workflow_steps: list[WorkflowStep] = field(default_factory=list)
    analysis: ProfileAnalysis | None = None
    recommendations: list[SchoolRecommendation] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    evidence_titles: list[str] = field(default_factory=list)


@function_tool
def profile_analyze_tool(ctx: RunContextWrapper[PlanningAgentContext]) -> dict[str, object]:
    """Analyze the student's profile and return structured competitiveness scores."""
    result = ctx.context.mcp_client.call_tool(
        "planning.profile_analyze",
        {"profile": ctx.context.profile.model_dump(mode="json")},
    )
    ctx.context.analysis = validate_analysis(result.data)
    _append_tool_step(ctx.context, "Analyze profile through MCP", "planning.profile_analyze", result)
    return result.data


@function_tool
def retrieve_planning_evidence_tool(ctx: RunContextWrapper[PlanningAgentContext], top_k: int = 5) -> dict[str, object]:
    """Retrieve planning evidence from the knowledge base for school planning."""
    result = ctx.context.mcp_client.call_tool(
        "planning.retrieve_evidence",
        {"profile": ctx.context.profile.model_dump(mode="json"), "top_k": top_k},
    )
    ctx.context.evidence_titles = chunk_titles(result.data)
    _append_tool_step(ctx.context, "Retrieve planning evidence through MCP", "planning.retrieve_evidence", result)
    return result.data


@function_tool
def recommend_schools_tool(ctx: RunContextWrapper[PlanningAgentContext], top_k: int = 3) -> dict[str, object]:
    """Recommend challenge, stable, and safe schools grounded in the profile and evidence."""
    result = ctx.context.mcp_client.call_tool(
        "planning.recommend_schools",
        {"profile": ctx.context.profile.model_dump(mode="json"), "top_k": top_k},
    )
    if not ctx.context.analysis and "analysis" in result.data:
        ctx.context.analysis = validate_analysis(result.data)
    ctx.context.recommendations = validate_recommendations(result.data)
    ctx.context.evidence_titles = chunk_titles(result.data) or ctx.context.evidence_titles
    _append_tool_step(ctx.context, "Recommend schools through MCP", "planning.recommend_schools", result)
    return result.data


@function_tool
def build_timeline_tool(ctx: RunContextWrapper[PlanningAgentContext]) -> dict[str, object]:
    """Build a four-stage planning timeline for the student."""
    result = ctx.context.mcp_client.call_tool(
        "planning.build_timeline",
        {"profile": ctx.context.profile.model_dump(mode="json")},
    )
    ctx.context.timeline = [str(item) for item in result.data.get("timeline", [])]
    _append_tool_step(ctx.context, "Build planning timeline through MCP", "planning.build_timeline", result)
    return result.data


class MemberAPlanningExecutor:
    def __init__(self, mcp_client: MemberAMCPClient | None = None) -> None:
        self.mcp_client = mcp_client or MemberAMCPClient()
        self.runtime = get_agent_sdk_runtime()

    def execute(self, profile: StudentProfile) -> PlanResponse:
        context = PlanningAgentContext(profile=profile, mcp_client=self.mcp_client)
        plan_text: str
        plan_source: str
        if self.runtime.is_enabled():
            try:
                plan_text = self._run_agent(context)
                plan_source = "planner"
            except Exception:
                self._ensure_context(context)
                plan_text = self._fallback_summary(context)
                plan_source = "fallback"
        else:
            self._ensure_context(context)
            plan_text = self._fallback_summary(context)
            plan_source = "fallback"

        self._ensure_context(context)
        workflow = WorkflowRun(
            workflow_type="planning",
            status="completed",
            steps=[
                *context.workflow_steps,
                self._agent_step(plan_text, plan_source),
            ],
            final_result=plan_text,
            plan_source=plan_source,  # type: ignore[arg-type]
            planner_summary=(
                "OpenAI Agents SDK orchestrated MCP planning tools."
                if plan_source == "planner"
                else "Fell back to deterministic planning synthesis after MCP data collection."
            ),
        )
        return PlanResponse(
            plan=plan_text,
            analysis=context.analysis or analyze_profile(profile),
            recommendations=context.recommendations,
            timeline=context.timeline,
            evidence=context.evidence_titles,
            workflow=workflow,
        )

    def _run_agent(self, context: PlanningAgentContext) -> str:
        model = self.runtime.build_model()
        agent = Agent[PlanningAgentContext](
            name="MemberAPlanningAgent",
            model=model,
            model_settings=ModelSettings(temperature=0.2),
            instructions=(
                "You are the planning orchestrator for a CS baoyan assistant. "
                "You must call these tools in order: profile_analyze_tool, "
                "retrieve_planning_evidence_tool, recommend_schools_tool, build_timeline_tool. "
                "Then write a personalized Chinese planning summary for the student. "
                "Do not reveal internal workflow steps, tools, MCP, or system implementation. "
                "You must mention concrete school names, explain why the ladder is arranged this way, "
                "mention at least one real weakness from the profile, and point out the next two most important actions. "
                "Avoid empty phrases like '系统建议' or generic templates. "
                "Do not invent metrics, publications, deadlines, or other unsupported facts."
            ),
            tools=[
                profile_analyze_tool,
                retrieve_planning_evidence_tool,
                recommend_schools_tool,
                build_timeline_tool,
            ],
        )
        prompt = (
            "请生成面向学生的保研规划摘要。先调用工具获取画像、证据、院校推荐和时间线，再基于工具结果作答。"
            "输出中文纯文本，不要用 Markdown 表格。"
            f"\n学生姓名：{context.profile.name}"
            f"\n研究兴趣：{', '.join(context.profile.research_interests) or '未填写'}"
            f"\n风险偏好：{context.profile.risk_preference}"
        )
        result = Runner.run_sync(
            agent,
            prompt,
            context=context,
            max_turns=6,
        )
        return str(result.final_output).strip()

    def _ensure_context(self, context: PlanningAgentContext) -> None:
        if context.analysis is None:
            payload = self.mcp_client.call_tool(
                "planning.profile_analyze",
                {"profile": context.profile.model_dump(mode="json")},
            )
            context.analysis = validate_analysis(payload.data)
            _append_tool_step(context, "Backfill profile analysis", "planning.profile_analyze", payload)
        if not context.evidence_titles:
            payload = self.mcp_client.call_tool(
                "planning.retrieve_evidence",
                {"profile": context.profile.model_dump(mode="json"), "top_k": 5},
            )
            context.evidence_titles = chunk_titles(payload.data)
            _append_tool_step(context, "Backfill planning evidence", "planning.retrieve_evidence", payload)
        if not context.recommendations:
            payload = self.mcp_client.call_tool(
                "planning.recommend_schools",
                {"profile": context.profile.model_dump(mode="json"), "top_k": 3},
            )
            if context.analysis is None and "analysis" in payload.data:
                context.analysis = validate_analysis(payload.data)
            context.recommendations = validate_recommendations(payload.data)
            context.evidence_titles = chunk_titles(payload.data) or context.evidence_titles
            _append_tool_step(context, "Backfill school recommendations", "planning.recommend_schools", payload)
        if not context.timeline:
            payload = self.mcp_client.call_tool(
                "planning.build_timeline",
                {"profile": context.profile.model_dump(mode="json")},
            )
            context.timeline = [str(item) for item in payload.data.get("timeline", [])]
            _append_tool_step(context, "Backfill planning timeline", "planning.build_timeline", payload)

    def _fallback_summary(self, context: PlanningAgentContext) -> str:
        if context.analysis is None:
            raise AgentSdkRuntimeUnavailable("Planning context is incomplete")
        return format_plan_summary(
            context.profile,
            context.analysis,
            context.recommendations,
            context.timeline,
            context.evidence_titles,
        )

    def _agent_step(self, plan_text: str, plan_source: str) -> WorkflowStep:
        started_at = datetime.now(UTC)
        return WorkflowStep(
            name="Synthesize planning summary",
            status="completed",
            step_type="agent",
            capability="planning.summary.generate",
            decision_reason=(
                "OpenAI Agents SDK generated the user-facing plan summary."
                if plan_source == "planner"
                else "Fallback summary generated after deterministic MCP retrieval."
            ),
            model_name=(
                self.runtime.settings.agent_sdk_model
                if plan_source == "planner"
                else getattr(get_llm_provider(), "model", "mock")
            ),
            started_at=started_at,
            completed_at=started_at,
            duration_ms=0,
            agent_result=AgentResult(
                agent_name="MemberAPlanningAgent" if plan_source == "planner" else "PlanningFallback",
                input_summary="profile + evidence + recommendations + timeline",
                output=plan_text,
                references=[],
            ),
        )


def execute_planning(profile: StudentProfile) -> PlanResponse:
    return MemberAPlanningExecutor().execute(profile)


def run_planning_workflow(profile: StudentProfile) -> WorkflowRun:
    return execute_planning(profile).workflow


def _append_tool_step(
    context: PlanningAgentContext,
    name: str,
    capability: str,
    result: MCPToolResult,
) -> None:
    started_at = datetime.now(UTC)
    context.workflow_steps.append(
        WorkflowStep(
            name=name,
            status="completed",
            step_type="tool",
            capability=capability,
            decision_reason="Planning context collection for Member A.",
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


def _json_summary(value: object, limit: int = 420) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."
