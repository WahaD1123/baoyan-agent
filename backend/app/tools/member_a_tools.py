from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.models import ProfileAnalysis, RetrievedChunk, SchoolRecommendation, StudentProfile
from app.services.planning_service import (
    analyze_profile,
    build_timeline,
    recommend_schools,
    retrieve_planning_evidence,
)
from app.services.store import store


def planning_profile_analyze(profile: dict[str, Any]) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    analysis = analyze_profile(student)
    return {
        "analysis": analysis.model_dump(mode="json"),
    }


def planning_retrieve_evidence(profile: dict[str, Any], top_k: int = 5) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    documents = store.refresh_documents()
    chunks = retrieve_planning_evidence(student, documents)[:top_k]
    return {
        "evidence_titles": list(dict.fromkeys(chunk.document_title for chunk in chunks)),
        "chunks": [_chunk_payload(chunk) for chunk in chunks],
    }


def planning_recommend_schools(profile: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    documents = store.refresh_documents()
    analysis = analyze_profile(student)
    chunks = retrieve_planning_evidence(student, documents)
    recommendations = recommend_schools(student, analysis, documents, chunks)[:top_k]
    return {
        "analysis": analysis.model_dump(mode="json"),
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "evidence_titles": list(dict.fromkeys(chunk.document_title for chunk in chunks)),
    }


def planning_build_timeline(profile: dict[str, Any]) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    documents = store.refresh_documents()
    analysis = analyze_profile(student)
    chunks = retrieve_planning_evidence(student, documents)
    recommendations = recommend_schools(student, analysis, documents, chunks)
    timeline = build_timeline(student, recommendations)
    return {
        "timeline": timeline,
    }


ToolHandler = Callable[..., dict[str, Any]]

_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "planning.profile_analyze": planning_profile_analyze,
    "planning.retrieve_evidence": planning_retrieve_evidence,
    "planning.recommend_schools": planning_recommend_schools,
    "planning.build_timeline": planning_build_timeline,
}


def dispatch_local_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown Member A tool: {name}")
    return handler(**arguments)


def member_a_tool_names() -> list[str]:
    return list(_TOOL_HANDLERS)


def validate_analysis(payload: dict[str, Any]) -> ProfileAnalysis:
    return ProfileAnalysis.model_validate(payload["analysis"])


def validate_recommendations(payload: dict[str, Any]) -> list[SchoolRecommendation]:
    return [SchoolRecommendation.model_validate(item) for item in payload.get("recommendations", [])]


def chunk_titles(payload: dict[str, Any]) -> list[str]:
    return [str(item) for item in payload.get("evidence_titles", [])]


def _chunk_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "document_id": chunk.document_id,
        "document_title": chunk.document_title,
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "score": chunk.score,
        "hit_reason": chunk.hit_reason,
    }
