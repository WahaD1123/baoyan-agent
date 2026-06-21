from __future__ import annotations

from functools import lru_cache

from agents import AsyncOpenAI, OpenAIChatCompletionsModel, set_default_openai_client

from app.core.config import get_settings


class AgentSdkRuntimeUnavailable(RuntimeError):
    pass


class AgentSdkRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = bool(
            self.settings.agent_sdk_enabled
            and self.settings.llm_api_key
            and self.settings.llm_provider.lower() == "dashscope"
        )
        self._clients: dict[float, AsyncOpenAI] = {}

    def is_enabled(self) -> bool:
        return self.enabled

    def build_model(
        self,
        model_name: str | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> OpenAIChatCompletionsModel:
        if not self.enabled:
            raise AgentSdkRuntimeUnavailable("OpenAI Agents SDK runtime is disabled by configuration")
        client = self._get_client(timeout_seconds)
        return OpenAIChatCompletionsModel(
            model=model_name or self.settings.agent_sdk_model,
            openai_client=client,
        )

    def _get_client(self, timeout_seconds: float | None = None) -> AsyncOpenAI:
        timeout = timeout_seconds or self.settings.agent_sdk_timeout_seconds
        if timeout not in self._clients:
            self._clients[timeout] = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=(self.settings.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/"),
                timeout=timeout,
                max_retries=0,
            )
            set_default_openai_client(self._clients[timeout], use_for_tracing=False)
        return self._clients[timeout]


@lru_cache
def get_agent_sdk_runtime() -> AgentSdkRuntime:
    return AgentSdkRuntime()
