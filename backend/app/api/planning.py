from fastapi import APIRouter

from app.models import PlanRequest, PlanResponse
from app.services.store import store
from app.workflows import run_planning_workflow

router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
def generate_plan(payload: PlanRequest) -> PlanResponse:
    workflow = run_planning_workflow(payload.profile)
    store.add_workflow(workflow)
    schools = [
        "Sprint: Shanghai Jiao Tong University CS",
        "Stable: Zhejiang University CS",
        "Safe: Xiamen University AI Lab",
    ]
    timeline = [
        "Week 1: finish resume, ranking certificate, and project summary",
        "Week 2: upload notices and shortlist advisors",
        "Week 3: send advisor emails and practice coding tests",
        "Week 4: mock interviews and material review",
    ]
    return PlanResponse(plan=workflow.final_result, schools=schools, timeline=timeline, workflow=workflow)
