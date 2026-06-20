from fastapi import APIRouter

from app.agents_sdk.runtime import get_agent_sdk_runtime
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "baoyan-agent"}


@router.get("/health/llm")
def llm_health() -> dict[str, str | bool]:
    settings = get_settings()
    agent_sdk_runtime = get_agent_sdk_runtime()
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "has_api_key": bool(settings.llm_api_key),
        "agent_sdk_enabled": settings.agent_sdk_enabled,
        "agent_sdk_runtime_active": agent_sdk_runtime.is_enabled(),
        "agent_sdk_model": settings.agent_sdk_model,
        "loaded_env_files": ", ".join(settings.loaded_env_files) if settings.loaded_env_files else "none",
        "expected_env_files": ", ".join(settings.expected_env_files),
    }
