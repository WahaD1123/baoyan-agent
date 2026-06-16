from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models import (
    Advisor,
    AdvisorMatchRequest,
    AdvisorMatchResponse,
    AdvisorSearchRequest,
    AdvisorUrlRequest,
    Document,
    DocumentCreate,
    KnowledgeQuery,
    KnowledgeResponse,
    UrlDocumentRequest,
)
from app.services.store import store
from app.tools.document_processing import extract_text_from_pdf, prepare_document
from app.tools.retrieval import hybrid_retrieve, search_documents
from app.tools.web_crawler import crawl_url
from app.workflows import run_advisor_match_workflow, run_ingest_workflow, run_knowledge_workflow, score_advisors

router = APIRouter()


@router.get("/documents", response_model=list[Document])
def list_documents() -> list[Document]:
    return store.documents


@router.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: str) -> Document:
    for document in store.documents:
        if document.id == document_id:
            return document
    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/documents", response_model=Document)
def add_document(payload: DocumentCreate) -> Document:
    document = prepare_document(Document(**payload.model_dump()))
    store.add_document(document)
    return document


@router.post("/documents/text", response_model=dict)
def add_text_document(payload: DocumentCreate) -> dict[str, object]:
    data = payload.model_dump()
    data["source_type"] = data.get("source_type") or "text"
    document = prepare_document(Document(**data))
    store.add_document(document)
    workflow = run_ingest_workflow(document, "text")
    store.add_workflow(workflow)
    return {"document": document, "workflow": workflow}


@router.post("/documents/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("notice"),
    title: str = Form(""),
) -> dict[str, object]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF upload is supported in the MVP")
    content = extract_text_from_pdf(await file.read())
    if not content.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this PDF")
    document = prepare_document(
        Document(
            title=title or file.filename,
            doc_type=doc_type,  # type: ignore[arg-type]
            content=content,
            source=file.filename,
            source_type="pdf",
        )
    )
    store.add_document(document)
    workflow = run_ingest_workflow(document, "pdf")
    store.add_workflow(workflow)
    return {"document": document, "workflow": workflow}


@router.post("/documents/url", response_model=dict)
def add_url_document(payload: UrlDocumentRequest) -> dict[str, object]:
    crawled = crawl_url(payload.url)
    if crawled.status == "failed":
        raise HTTPException(status_code=400, detail=crawled.error or "Failed to crawl URL")
    document = prepare_document(
        Document(
            title=payload.title or crawled.title,
            doc_type=payload.doc_type,
            content=crawled.content,
            source=payload.url,
            source_type="url",
        )
    )
    store.add_document(document)
    workflow = run_ingest_workflow(document, "url")
    store.add_workflow(workflow)
    return {"document": document, "extracted": document.extracted, "workflow": workflow}


@router.post("/query", response_model=KnowledgeResponse)
def query_knowledge(payload: KnowledgeQuery) -> KnowledgeResponse:
    chunks = hybrid_retrieve(store.documents, payload.question, payload.top_k)
    doc_ids = {chunk.document_id for chunk in chunks}
    docs = [document for document in store.documents if document.id in doc_ids] or search_documents(store.documents, payload.question, payload.top_k)
    workflow = run_knowledge_workflow(payload.question, docs, chunks)
    store.add_workflow(workflow)
    return KnowledgeResponse(answer=workflow.final_result, documents=docs, chunks=chunks, workflow=workflow)


@router.get("/advisors", response_model=list[Advisor])
def list_advisors() -> list[Advisor]:
    return store.advisors


@router.post("/advisors/url", response_model=dict)
def add_advisor_from_url(payload: AdvisorUrlRequest) -> dict[str, object]:
    crawled = crawl_url(payload.url)
    if crawled.status == "failed":
        raise HTTPException(status_code=400, detail=crawled.error or "Failed to crawl advisor URL")
    document = prepare_document(
        Document(
            title=payload.title or crawled.title,
            doc_type="advisor",
            content=crawled.content,
            source=payload.url,
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
        homepage=payload.url,
        summary=str(extracted.get("llm_summary") or document.content[:400]),
        representative_works=[str(item) for item in extracted.get("representative_works", [])],
        suitable_background=str(extracted.get("suitable_background") or ""),
        source_document_id=document.id,
    )
    store.add_advisor(advisor)
    workflow = run_ingest_workflow(document, "advisor_url")
    store.add_workflow(workflow)
    return {"advisor": advisor, "document": document, "workflow": workflow}


@router.post("/advisors/search", response_model=dict)
def search_advisors(payload: AdvisorSearchRequest) -> dict[str, object]:
    query = " ".join([payload.university, payload.direction, *payload.keywords]).strip().lower()
    candidates = []
    for advisor in store.advisors:
        haystack = " ".join(
            [advisor.name, advisor.university, advisor.department, advisor.summary, " ".join(advisor.research_areas)]
        ).lower()
        if not query or any(term for term in query.split() if term in haystack):
            candidates.append(advisor)
    return {
        "advisors": candidates[: payload.limit],
        "message": "MVP searches local advisor library first. Paste a homepage URL for real-time crawl.",
    }


@router.post("/advisors/match", response_model=AdvisorMatchResponse)
def match_advisors(payload: AdvisorMatchRequest) -> AdvisorMatchResponse:
    matches = score_advisors(payload.profile, store.advisors, payload.top_k)
    workflow = run_advisor_match_workflow(payload.profile, [item.advisor for item in matches], matches)
    store.add_workflow(workflow)
    return AdvisorMatchResponse(matches=matches, workflow=workflow)
