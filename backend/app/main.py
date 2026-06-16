from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, interview, knowledge, materials, planning, profile, workflows
from app.core.config import get_settings


settings = get_settings()

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
