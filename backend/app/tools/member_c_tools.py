from collections.abc import Callable
from typing import Any

from app.models import Advisor, StudentProfile
from app.services.store import store
from app.tools.retrieval import hybrid_retrieve


def build_profile_context(profile: dict[str, Any]) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    evidence = [
        *student.projects,
        *student.competitions,
        *student.publications,
    ]
    return {
        "name": student.name,
        "university": student.university,
        "major": student.major,
        "rank_percent": student.rank_percent,
        "gpa": student.gpa,
        "english_score": student.english_score,
        "research_interests": student.research_interests,
        "preferred_schools": student.preferred_schools,
        "target_regions": student.target_regions,
        "evidence": evidence,
        "notes": student.notes,
    }


def build_advisor_context(advisor: dict[str, Any] | None) -> dict[str, Any]:
    if not advisor:
        return {"available": False, "message": "No advisor was supplied."}
    item = Advisor.model_validate(advisor)
    return {
        "available": True,
        "id": item.id,
        "name": item.name,
        "university": item.university,
        "department": item.department,
        "research_areas": item.research_areas,
        "summary": item.summary,
        "representative_works": item.representative_works,
        "suitable_background": item.suitable_background,
        "homepage": item.homepage,
    }


def search_knowledge(query: str, top_k: int = 3) -> dict[str, Any]:
    documents = store.refresh_documents()
    chunks = hybrid_retrieve(documents, query, top_k)
    return {
        "query": query,
        "evidence": [
            {
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "score": chunk.score,
                "hit_reason": chunk.hit_reason,
            }
            for chunk in chunks
        ],
    }


def retrieve_interview_evidence(
    profile: dict[str, Any],
    target_school: str,
    direction: str,
    top_k: int = 4,
) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    query = " ".join(
        [
            target_school,
            direction,
            *student.research_interests,
            "面试 项目追问 专业基础 科研方向 英文面试",
        ]
    )
    retrieved = search_knowledge(query, top_k)
    return {
        "target_school": target_school,
        "direction": direction,
        "projects": student.projects,
        "publications": student.publications,
        "competitions": student.competitions,
        "research_interests": student.research_interests,
        "knowledge_evidence": retrieved["evidence"],
    }


ToolHandler = Callable[..., dict[str, Any]]

_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "profile.build_context": build_profile_context,
    "advisor.get_context": build_advisor_context,
    "knowledge.search": search_knowledge,
    "interview.retrieve_evidence": retrieve_interview_evidence,
}


def dispatch_local_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown Member C tool: {name}")
    return handler(**arguments)


def member_c_tool_names() -> list[str]:
    return list(_TOOL_HANDLERS)
