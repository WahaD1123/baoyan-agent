from types import SimpleNamespace

from app.services import llm as llm_module


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self.content}}]}


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        llm_api_key="test-key",
        llm_base_url="https://example.test/v1",
        llm_model="qwen3.7-plus",
        llm_critic_model="qwen3.6-flash",
        llm_critic_max_tokens=400,
        llm_planner_model="qwen3.6-flash",
        llm_planner_max_tokens=500,
        llm_member_c_model="qwen3.6-flash",
        llm_member_c_fallback_model="qwen3.6-flash",
        llm_member_c_max_tokens=1200,
    )


def test_critic_uses_shared_flash_route(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, _url: str, *, headers: dict, json: dict) -> FakeResponse:
            calls.append({"timeout": self.timeout, "headers": headers, "payload": json})
            return FakeResponse("critic result")

    monkeypatch.setattr(llm_module, "get_settings", _settings)
    monkeypatch.setattr(llm_module.httpx, "Client", FakeClient)

    output = llm_module.DashScopeProvider().generate("review this", task="critic")

    assert output == "critic result"
    assert calls[0]["payload"]["model"] == "qwen3.6-flash"
    assert calls[0]["payload"]["max_tokens"] == 400


def test_member_c_generation_uses_fast_model_without_duplicate_retry(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
            calls.append({"timeout": self.timeout, "payload": json})
            return FakeResponse("flash result")

    monkeypatch.setattr(llm_module, "get_settings", _settings)
    monkeypatch.setattr(llm_module.httpx, "Client", FakeClient)

    output = llm_module.DashScopeProvider().generate("write material", task="material")

    assert output == "flash result"
    assert [call["payload"]["model"] for call in calls] == ["qwen3.6-flash"]
    assert all(call["payload"]["max_tokens"] == 1200 for call in calls)


def test_workflow_planner_uses_fast_bounded_route(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, _url: str, *, headers: dict, json: dict) -> FakeResponse:
            calls.append({"timeout": self.timeout, "headers": headers, "payload": json})
            return FakeResponse('{"goal":"generate_statement","steps":[]}')

    monkeypatch.setattr(llm_module, "get_settings", _settings)
    monkeypatch.setattr(llm_module.httpx, "Client", FakeClient)

    output = llm_module.DashScopeProvider().generate("plan this", task="workflow_planner")

    assert output.startswith('{"goal"')
    assert calls[0]["payload"]["model"] == "qwen3.6-flash"
    assert calls[0]["payload"]["max_tokens"] == 500
