from fastapi import APIRouter

from app.models import PlanRequest, PlanResponse
from app.services.store import store
from app.workflows import execute_planning

router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
def generate_plan(payload: PlanRequest) -> PlanResponse:
    response = execute_planning(payload.profile)
    store.add_workflow(response.workflow)
    return response
