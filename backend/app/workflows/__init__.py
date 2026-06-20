__all__ = [
    "run_advisor_match_workflow",
    "run_ingest_workflow",
    "run_interview_workflow",
    "run_knowledge_workflow",
    "run_material_email_workflow",
    "run_material_workflow",
    "execute_planning",
    "execute_advisor_match",
    "execute_knowledge_query",
    "run_planning_workflow",
    "run_resume_highlights_workflow",
    "run_statement_workflow",
    "score_advisors",
]


def __getattr__(name: str):
    if name in {
        "run_advisor_match_workflow",
        "run_ingest_workflow",
        "run_knowledge_workflow",
        "score_advisors",
    }:
        from app.workflows import engine

        return getattr(engine, name)
    if name in {"execute_planning", "run_planning_workflow"}:
        from app.workflows import member_a_executor

        return getattr(member_a_executor, name)
    if name in {"execute_advisor_match", "execute_knowledge_query"}:
        from app.workflows import member_b_executor

        return getattr(member_b_executor, name)
    if name in {
        "run_interview_workflow",
        "run_material_email_workflow",
        "run_material_workflow",
        "run_resume_highlights_workflow",
        "run_statement_workflow",
    }:
        from app.workflows import member_c_executor

        return getattr(member_c_executor, name)
    raise AttributeError(f"module 'app.workflows' has no attribute {name!r}")
