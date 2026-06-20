from typing import Any

from app.models import Advisor, Document, DocumentType, StudentProfile
from app.services.library_router import route_chunks_for_documents, route_documents_by_library
from app.services.store import store
from app.tools.document_processing import prepare_document
from app.tools.web_crawler import crawl_url


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
    from app.workflows.engine import run_ingest_workflow

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
    from app.workflows.engine import run_ingest_workflow

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
    return {
        "question": question,
        "answer": _draft_knowledge_answer(question, documents, chunks),
        "documents": [_document_summary(document, include_content=True) for document in documents],
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        "workflow": {
            "type": "knowledge",
            "status": "completed",
            "steps": ["Route documents from local knowledge library", "Collect citation chunks"],
            "final_result": f"Retrieved {len(documents)} documents and {len(chunks)} chunks.",
        },
    }


def knowledge_list_documents(limit: int = 20, include_content: bool = False) -> dict[str, Any]:
    documents = store.refresh_documents()
    return {
        "count": len(documents),
        "documents": [_document_summary(document, include_content) for document in documents[:limit]],
    }


def advisor_add_url(url: str, title: str = "") -> dict[str, Any]:
    from app.workflows.engine import run_ingest_workflow

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


def _draft_knowledge_answer(question: str, documents: list[Document], chunks: list[Any]) -> str:
    if not documents:
        return (
            f"资料库暂未命中与“{question}”直接相关的材料。"
            "建议先上传通知、经验贴或导师主页，再进行基于资料的问答。"
        )
    lines = [f"已根据资料库中与“{question}”相关的材料整理出初步答案。"]
    for document in documents[:3]:
        summary = str(document.analysis.get("summary") or document.extracted or "").strip()
        if summary:
            lines.append(f"- {document.title}: {summary[:220]}")
        else:
            lines.append(f"- {document.title}: {document.content[:220]}")
    if chunks:
        lines.append("引用片段：")
        for index, chunk in enumerate(chunks[:3], start=1):
            lines.append(f"[{index}] {chunk.document_title}: {chunk.text[:180]}")
    else:
        lines.append("当前资料有结构化记录，但缺少可展示的引用片段。")
    return "\n".join(lines)


def advisor_match(profile: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    from app.workflows.engine import score_advisors

    student = StudentProfile.model_validate(profile)
    matches = score_advisors(student, store.advisors, top_k)
    return {
        "matches": [match.model_dump(mode="json") for match in matches],
        "workflow": {
            "type": "advisor_match",
            "status": "completed",
            "steps": ["Score advisors from local advisor library"],
            "final_result": f"Scored {len(matches)} advisor candidates.",
        },
    }


def member_b_tool_names() -> list[str]:
    return list(_TOOL_HANDLERS)


ToolHandler = Any

_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "knowledge.add_text": knowledge_add_text,
    "knowledge.add_url": knowledge_add_url,
    "knowledge.query": knowledge_query,
    "knowledge.list_documents": knowledge_list_documents,
    "advisor.add_url": advisor_add_url,
    "advisor.list": advisor_list,
    "advisor.match": advisor_match,
}


def dispatch_local_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown Member B tool: {name}")
    return handler(**arguments)
