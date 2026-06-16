from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "baoyan-agent"}


@router.get("/health/llm")
def llm_health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "has_api_key": bool(settings.llm_api_key),
    }
