from typing import Any

from app.models import Advisor, Document, DocumentType, StudentProfile
from app.services.library_router import route_chunks_for_documents, route_documents_by_library
from app.services.store import store
from app.tools.document_processing import prepare_document
from app.tools.web_crawler import crawl_url
from app.workflows.engine import run_advisor_match_workflow, run_ingest_workflow, run_knowledge_workflow, score_advisors


def _workflow_summary(workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "type": workflow.workflow_type,
        "status": workflow.status,
        "steps": [step.name for step in workflow.steps],
        "final_result": workflow.final_result,
    }


def _document_summary(document: Document, include_content: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": document.id,
        "title": document.title,
        "doc_type": document.doc_type,
        "source_type": document.source_type,
        "source": document.source,
        "keywords": document.keywords,
        "chunk_count": len(document.chunks),
        "extracted": document.extracted,
        "analysis": document.analysis,
        "created_at": document.created_at.isoformat(),
    }
    if include_content:
        data["content"] = document.content
        data["chunks"] = [chunk.model_dump(mode="json") for chunk in document.chunks]
    return data


def _advisor_summary(advisor: Advisor) -> dict[str, Any]:
    return advisor.model_dump(mode="json")


def knowledge_add_text(
    title: str,
    content: str,
    doc_type: DocumentType = "other",
    source: str = "mcp_text",
) -> dict[str, Any]:
    document = prepare_document(
        Document(
            title=title or "Untitled text material",
            doc_type=doc_type,
            content=content,
            source=source,
            source_type="text",
        )
    )
    store.add_document(document)
    workflow = run_ingest_workflow(document, "mcp_text")
    store.add_workflow(workflow)
    return {"document": _document_summary(document), "workflow": _workflow_summary(workflow)}


def knowledge_add_url(url: str, doc_type: DocumentType = "notice", title: str = "") -> dict[str, Any]:
    crawled = crawl_url(url)
    if crawled.status == "failed":
        return {"status": "failed", "error": crawled.error or "Failed to crawl URL", "url": url}

    document = prepare_document(
        Document(
            title=title or crawled.title or url,
            doc_type=doc_type,
            content=crawled.content,
            source=url,
            source_type="url",
        )
    )
    store.add_document(document)
    workflow = run_ingest_workflow(document, "mcp_url")
    store.add_workflow(workflow)
    return {"status": "success", "document": _document_summary(document), "workflow": _workflow_summary(workflow)}


def knowledge_query(question: str, top_k: int = 3) -> dict[str, Any]:
    documents = route_documents_by_library(question, store.documents, top_k)
    chunks = route_chunks_for_documents(question, documents, top_k)
    workflow = run_knowledge_workflow(question, documents, chunks)
    store.add_workflow(workflow)
    return {
        "question": question,
        "answer": workflow.final_result,
        "documents": [_document_summary(document) for document in documents],
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        "workflow": _workflow_summary(workflow),
    }


def knowledge_list_documents(limit: int = 20, include_content: bool = False) -> dict[str, Any]:
    documents = store.refresh_documents()
    return {
        "count": len(documents),
        "documents": [_document_summary(document, include_content) for document in documents[:limit]],
    }


def advisor_add_url(url: str, title: str = "") -> dict[str, Any]:
    crawled = crawl_url(url)
    if crawled.status == "failed":
        return {"status": "failed", "error": crawled.error or "Failed to crawl advisor URL", "url": url}

    document = prepare_document(
        Document(
            title=title or crawled.title or url,
            doc_type="advisor",
            content=crawled.content,
            source=url,
            source_type="url",
        )
    )
    store.add_document(document)
    extracted = document.extracted
    advisor = Advisor(
        name=str(extracted.get("name") or document.title),
        university=str(extracted.get("university") or ""),
        department=str(extracted.get("department") or "Computer Science"),
        research_areas=[str(item) for item in extracted.get("research_areas", document.keywords[:5])],
        homepage=url,
        summary=str(document.analysis.get("summary") or extracted.get("llm_summary") or document.content[:400]),
        representative_works=[str(item) for item in extracted.get("representative_works", [])],
        suitable_background=str(extracted.get("suitable_background") or ""),
        source_document_id=document.id,
    )
    store.add_advisor(advisor)
    workflow = run_ingest_workflow(document, "mcp_advisor_url")
    store.add_workflow(workflow)
    return {
        "status": "success",
        "advisor": _advisor_summary(advisor),
        "document": _document_summary(document),
        "workflow": _workflow_summary(workflow),
    }


def advisor_list(limit: int = 20) -> dict[str, Any]:
    return {
        "count": len(store.advisors),
        "advisors": [_advisor_summary(advisor) for advisor in store.advisors[:limit]],
    }


def advisor_match(profile: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    student = StudentProfile.model_validate(profile)
    matches = score_advisors(student, store.advisors, top_k)
    workflow = run_advisor_match_workflow(student, [item.advisor for item in matches], matches)
    store.add_workflow(workflow)
    return {
        "matches": [match.model_dump(mode="json") for match in matches],
        "workflow": _workflow_summary(workflow),
    }


def member_b_tool_names() -> list[str]:
    return [
        "knowledge.add_text",
        "knowledge.add_url",
        "knowledge.query",
        "knowledge.list_documents",
        "advisor.add_url",
        "advisor.list",
        "advisor.match",
    ]
