from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import health, interview, knowledge, materials, planning, profile, workflows
from app.core.config import get_settings


settings = get_settings()
logger = logging.getLogger("baoyan-agent")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-agent middleware system for CS baoyan application support.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(planning.router, prefix="/api/planning", tags=["planning"])
app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])


@app.on_event("startup")
def log_startup_settings() -> None:
    logger.info(
        "App startup: provider=%s model=%s has_api_key=%s agent_sdk_enabled=%s agent_sdk_model=%s loaded_env_files=%s",
        settings.llm_provider,
        settings.llm_model,
        bool(settings.llm_api_key),
        settings.agent_sdk_enabled,
        settings.agent_sdk_model,
        settings.loaded_env_files or ["none"],
    )
