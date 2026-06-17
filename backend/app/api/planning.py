from fastapi import APIRouter

from app.models import PlanRequest, PlanResponse
from app.services.planning_service import analyze_profile, build_timeline, recommend_schools, retrieve_planning_evidence
from app.services.store import store
from app.workflows import run_planning_workflow

router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
def generate_plan(payload: PlanRequest) -> PlanResponse:
    workflow = run_planning_workflow(payload.profile)
    store.add_workflow(workflow)
    analysis = analyze_profile(payload.profile)
    evidence_chunks = retrieve_planning_evidence(payload.profile, store.documents)
    recommendations = recommend_schools(payload.profile, analysis, store.documents, evidence_chunks)
    timeline = build_timeline(payload.profile, recommendations)
    evidence = list(dict.fromkeys(chunk.document_title for chunk in evidence_chunks))
    return PlanResponse(
        plan=workflow.final_result,
        analysis=analysis,
        recommendations=recommendations,
        timeline=timeline,
        evidence=evidence,
        workflow=workflow,
    )
