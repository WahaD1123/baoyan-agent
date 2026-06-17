from datetime import datetime

from fastapi import APIRouter

from app.models import ProfileAnalysis, StudentProfile
from app.services.planning_service import analyze_profile
from app.services.store import store

router = APIRouter()


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
    return analyze_profile(profile)
