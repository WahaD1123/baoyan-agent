from fastapi import APIRouter, HTTPException

from app.models import WorkflowRun
from app.services.store import store

router = APIRouter()


@router.get("", response_model=list[WorkflowRun])
def list_workflows() -> list[WorkflowRun]:
    return store.workflows


@router.get("/{workflow_id}", response_model=WorkflowRun)
def get_workflow(workflow_id: str) -> WorkflowRun:
    for workflow in store.workflows:
        if workflow.id == workflow_id:
            return workflow
    raise HTTPException(status_code=404, detail="Workflow not found")
