from __future__ import annotations

from dataclasses import dataclass

from app.agents_sdk import member_c as member_c_sdk
from app.agents_sdk.member_c import MemberCAgentSdkLLM
from app.workflows.member_c_executor import MemberCWorkflowExecutor


class FakeRuntime:
    def __init__(self, *, enabled: bool = True, error: Exception | None = None) -> None:
        self.enabled = enabled
        self.error = error
        self.models: list[str] = []
        self.model_requests: list[tuple[str, float | None]] = []

    def is_enabled(self) -> bool:
        return self.enabled

    def build_model(
        self,
        model_name: str | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        if self.error is not None:
            raise self.error
        selected = model_name or "default-model"
        self.models.append(selected)
        self.model_requests.append((selected, timeout_seconds))
        return selected


class RecordingFallback:
    def __init__(self, output: str = "fallback output") -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, task: str = "general") -> str:
        self.calls.append((prompt, task))
        return self.output


@dataclass
class FakeRunResult:
    final_output: str


def test_member_c_sdk_llm_uses_shared_runtime_and_task_model(monkeypatch) -> None:
    runtime = FakeRuntime()
    fallback = RecordingFallback()
    captured: dict[str, object] = {}

    monkeypatch.setattr(member_c_sdk, "model_name_for_task", lambda task: f"{task}-model")

    def fake_run_sync(agent, prompt: str, *, max_turns: int):  # type: ignore[no-untyped-def]
        captured.update(agent=agent, prompt=prompt, max_turns=max_turns)
        return FakeRunResult(final_output="SDK generated material")

    monkeypatch.setattr(member_c_sdk.Runner, "run_sync", fake_run_sync)

    llm = MemberCAgentSdkLLM(
        runtime=runtime,
        fallback=fallback,
        timeout_seconds=45.0,
    )

    output = llm.generate("grounded material prompt", task="material")

    assert output == "SDK generated material"
    assert runtime.models == ["material-model"]
    assert runtime.model_requests == [("material-model", 45.0)]
    assert captured["prompt"] == "grounded material prompt"
    assert captured["max_turns"] == 1
    assert captured["agent"].name == "MemberCMaterialAgent"  # type: ignore[union-attr]
    assert llm.last_call.source == "sdk"
    assert llm.last_call.model_name == "material-model"
    assert llm.last_call.fallback_reason == ""
    assert fallback.calls == []


def test_member_c_sdk_llm_falls_back_once_when_sdk_fails(monkeypatch) -> None:
    runtime = FakeRuntime(error=TimeoutError("SDK timed out"))
    fallback = RecordingFallback("fallback output\n\n[DashScope fallback: ReadTimeout]")
    monkeypatch.setattr(member_c_sdk, "model_name_for_task", lambda task: f"{task}-model")

    llm = MemberCAgentSdkLLM(runtime=runtime, fallback=fallback)

    output = llm.generate("critic prompt", task="critic_structured")

    assert output == "fallback output"
    assert fallback.calls == [("critic prompt", "critic_structured")]
    assert llm.last_call.source == "fallback"
    assert llm.last_call.model_name == "critic_structured-model"
    assert llm.last_call.fallback_reason == (
        "TimeoutError: SDK timed out; DashScope fallback: ReadTimeout"
    )


def test_member_c_executor_shares_sdk_llm_across_default_agents(monkeypatch) -> None:
    sdk_llm = RecordingFallback()
    monkeypatch.setattr(
        "app.workflows.member_c_executor.build_member_c_agent_llm",
        lambda: sdk_llm,
    )

    executor = MemberCWorkflowExecutor()

    assert executor.material_agent.llm is sdk_llm
    assert executor.interview_agent.llm is sdk_llm
    assert executor.critic_agent.llm is sdk_llm
