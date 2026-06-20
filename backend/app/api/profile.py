from datetime import datetime
import logging

from fastapi import APIRouter

from app.models import ProfileAnalysis, StudentProfile
from app.services.planning_service import analyze_profile
from app.services.store import store

router = APIRouter()
logger = logging.getLogger("baoyan-agent.profile")


@router.get("", response_model=StudentProfile)
def get_profile() -> StudentProfile:
    return store.profile


@router.post("", response_model=StudentProfile)
def save_profile(profile: StudentProfile) -> StudentProfile:
    profile.updated_at = datetime.utcnow()
    store.profile = profile
    return store.profile


@router.post("/analyze", response_model=ProfileAnalysis)
def analyze_current_profile(profile: StudentProfile) -> ProfileAnalysis:
    logger.info("Analyze profile requested for %s", profile.name)
    return analyze_profile(profile)
