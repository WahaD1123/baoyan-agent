from fastapi import APIRouter

from app.models import EmailGenerationRequest, MaterialResponse
from app.services.store import store
from app.workflows import run_material_workflow

router = APIRouter()


@router.post("/email", response_model=MaterialResponse)
def generate_email(payload: EmailGenerationRequest) -> MaterialResponse:
    workflow = run_material_workflow(payload.profile, payload.advisor, payload.purpose)
    store.add_workflow(workflow)
    return MaterialResponse(content=workflow.final_result, workflow=workflow)
