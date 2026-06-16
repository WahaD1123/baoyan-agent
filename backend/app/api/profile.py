from datetime import datetime

from fastapi import APIRouter

from app.models import StudentProfile
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
