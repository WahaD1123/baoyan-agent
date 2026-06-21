from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents_sdk.runtime import AgentSdkRuntime, get_agent_sdk_runtime
from app.services.llm import get_llm_provider, model_name_for_task

try:
    from agents import Agent, ModelSettings, Runner
except ModuleNotFoundError:  # pragma: no cover
    Agent = None  # type: ignore[assignment]
    ModelSettings = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]


logger = logging.getLogger("baoyan-agent.member-c-sdk")


class AgentLLM(Protocol):
    def generate(self, prompt: str, task: str = "general") -> str: ...


@dataclass(frozen=True)
class MemberCAgentCall:
    source: Literal["sdk", "fallback"]
    model_name: str
    fallback_reason: str = ""


_TASK_CONFIG = {
    "material": (
        "MemberCMaterialAgent",
        "Generate restrained Chinese CS baoyan application material. Use only facts in the "
        "provided grounded context and never invent metrics, publications, tools, advisor work, "
        "or contact details. Return only the requested material.",
    ),
    "interview": (
        "MemberCInterviewAgent",
        "Generate Chinese CS baoyan mock interview questions grounded in the supplied profile "
        "and evidence. Preserve the requested categories and return only the interview content.",
    ),
    "critic_structured": (
        "MemberCCriticAgent",
        "Act as a strict CS baoyan material reviewer. Return only the requested JSON object. "
        "Except for JSON field names, write all content in Simplified Chinese and identify "
        "unsupported claims.",
    ),
}


class MemberCAgentSdkLLM:
    """AgentLLM adapter backed by the shared OpenAI Agents SDK runtime."""

    def __init__(
        self,
        runtime: AgentSdkRuntime | None = None,
        fallback: AgentLLM | None = None,
    ) -> None:
        self.runtime = runtime or get_agent_sdk_runtime()
        self.fallback = fallback or get_llm_provider()
        self.last_call: MemberCAgentCall | None = None

    def generate(self, prompt: str, task: str = "general") -> str:
        model_name = model_name_for_task(task)
        try:
            output = self._run_sdk(prompt, task, model_name)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Member C SDK fallback for task=%s model=%s due to %s",
                task,
                model_name,
                reason,
            )
            self.last_call = MemberCAgentCall(
                source="fallback",
                model_name=model_name,
                fallback_reason=reason,
            )
            return self.fallback.generate(prompt, task=task)

        self.last_call = MemberCAgentCall(source="sdk", model_name=model_name)
        return output

    def _run_sdk(self, prompt: str, task: str, model_name: str) -> str:
        if not self.runtime.is_enabled():
            raise RuntimeError("OpenAI Agents SDK runtime is disabled")
        if Agent is None or ModelSettings is None or Runner is None:
            raise RuntimeError("OpenAI Agents SDK is not installed")

        agent_name, instructions = _TASK_CONFIG.get(
            task,
            (
                "MemberCAgent",
                "Complete the requested CS baoyan task in Simplified Chinese using only supplied facts.",
            ),
        )
        agent = Agent(
            name=agent_name,
            model=self.runtime.build_model(model_name),
            model_settings=ModelSettings(temperature=0.2),
            instructions=instructions,
        )
        result = Runner.run_sync(agent, prompt, max_turns=1)
        return str(result.final_output).strip()


def build_member_c_agent_llm() -> AgentLLM:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return get_llm_provider()
    return MemberCAgentSdkLLM()
