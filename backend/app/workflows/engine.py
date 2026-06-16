from app.agents import (
    AdvisorMatchAgent,
    CriticAgent,
    InterviewAgent,
    KnowledgeAgent,
    MaterialAgent,
    PlannerAgent,
    ProfileAgent,
    SchoolRecommendAgent,
)
from app.models import Advisor, Document, StudentProfile, WorkflowRun, WorkflowStep


def _workflow(workflow_type: str, steps: list[WorkflowStep], final_result: str) -> WorkflowRun:
    return WorkflowRun(workflow_type=workflow_type, steps=steps, final_result=final_result)


def run_planning_workflow(profile: StudentProfile) -> WorkflowRun:
    profile_text = f"{profile.name}, rank top {profile.rank_percent}%, interests: {', '.join(profile.research_interests)}"
    profile_result = ProfileAgent().run(profile_text)
    school_result = SchoolRecommendAgent().run(profile_result.output)
    planner_result = PlannerAgent().run(school_result.output)
    return _workflow(
        "planning",
        [
            WorkflowStep(name="Analyze student profile", agent_result=profile_result),
            WorkflowStep(name="Recommend sprint/stable/safe schools", agent_result=school_result),
            WorkflowStep(name="Generate application timeline", agent_result=planner_result),
        ],
        planner_result.output,
    )


def run_knowledge_workflow(question: str, documents: list[Document]) -> WorkflowRun:
    refs = [doc.title for doc in documents]
    result = KnowledgeAgent().run(f"Question: {question}. Documents: {', '.join(refs)}", refs)
    return _workflow(
        "knowledge",
        [WorkflowStep(name="Retrieve documents and answer", agent_result=result)],
        result.output,
    )


def run_advisor_match_workflow(profile: StudentProfile, advisors: list[Advisor]) -> WorkflowRun:
    refs = [f"{advisor.name} - {advisor.university}" for advisor in advisors]
    result = AdvisorMatchAgent().run(
        f"Profile interests: {', '.join(profile.research_interests)}. Candidate advisors: {', '.join(refs)}",
        refs,
    )
    return _workflow(
        "advisor_match",
        [WorkflowStep(name="Match advisors by research fit", agent_result=result)],
        result.output,
    )


def run_material_workflow(profile: StudentProfile, advisor: Advisor | None, purpose: str) -> WorkflowRun:
    advisor_text = f"{advisor.name} at {advisor.university}" if advisor else "target advisor"
    draft = MaterialAgent().run(
        f"Generate contact email for {profile.name} to {advisor_text}. Purpose: {purpose}"
    )
    review = CriticAgent().run(draft.output, [draft.id])
    return _workflow(
        "material",
        [
            WorkflowStep(name="Generate application material", agent_result=draft),
            WorkflowStep(name="Critic review", agent_result=review),
        ],
        f"{draft.output}\n\nQuality check:\n{review.output}",
    )


def run_interview_workflow(profile: StudentProfile, target_school: str, direction: str) -> WorkflowRun:
    interview = InterviewAgent().run(
        f"Generate mock interview questions for {profile.name}, target: {target_school}, direction: {direction}"
    )
    review = CriticAgent().run(interview.output, [interview.id])
    return _workflow(
        "interview",
        [
            WorkflowStep(name="Generate mock interview", agent_result=interview),
            WorkflowStep(name="Critic review", agent_result=review),
        ],
        f"{interview.output}\n\nQuality check:\n{review.output}",
    )
