from fastapi import APIRouter

from app.models import InterviewRequest, MaterialResponse
from app.services.store import store
from app.workflows import run_interview_workflow

router = APIRouter()


@router.post("/mock", response_model=MaterialResponse)
def generate_mock_interview(payload: InterviewRequest) -> MaterialResponse:
    workflow = run_interview_workflow(payload.profile, payload.target_school, payload.direction)
    store.add_workflow(workflow)
    return MaterialResponse(content=workflow.final_result, workflow=workflow)
