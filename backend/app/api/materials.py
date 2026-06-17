from fastapi import APIRouter

from app.models import EmailGenerationRequest, MaterialResponse, ResumeHighlightRequest, StatementRequest
from app.services.store import store
from app.workflows import run_material_email_workflow, run_resume_highlights_workflow, run_statement_workflow

router = APIRouter()


@router.post("/email", response_model=MaterialResponse)
def generate_email(payload: EmailGenerationRequest) -> MaterialResponse:
    workflow = run_material_email_workflow(payload.profile, payload.advisor, payload.purpose)
    store.add_workflow(workflow)
    return MaterialResponse(content=workflow.final_result, workflow=workflow)


@router.post("/resume-highlights", response_model=MaterialResponse)
def generate_resume_highlights(payload: ResumeHighlightRequest) -> MaterialResponse:
    workflow = run_resume_highlights_workflow(payload.profile, payload.target_direction)
    store.add_workflow(workflow)
    return MaterialResponse(content=workflow.final_result, workflow=workflow)


@router.post("/statement", response_model=MaterialResponse)
def generate_statement(payload: StatementRequest) -> MaterialResponse:
    workflow = run_statement_workflow(payload.profile, payload.target_school, payload.direction, payload.tone)
    store.add_workflow(workflow)
    return MaterialResponse(content=workflow.final_result, workflow=workflow)
