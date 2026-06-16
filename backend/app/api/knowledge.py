from fastapi import APIRouter

from app.models import (
    Advisor,
    AdvisorMatchRequest,
    Document,
    DocumentCreate,
    KnowledgeQuery,
    KnowledgeResponse,
)
from app.services.store import store
from app.tools.retrieval import search_documents
from app.workflows import run_advisor_match_workflow, run_knowledge_workflow

router = APIRouter()


@router.get("/documents", response_model=list[Document])
def list_documents() -> list[Document]:
    return store.documents


@router.post("/documents", response_model=Document)
def add_document(payload: DocumentCreate) -> Document:
    keywords = sorted({word.strip(".,;:").lower() for word in payload.content.split()[:20] if len(word) > 3})
    document = Document(**payload.model_dump(), keywords=keywords)
    store.documents.insert(0, document)
    return document


@router.post("/query", response_model=KnowledgeResponse)
def query_knowledge(payload: KnowledgeQuery) -> KnowledgeResponse:
    docs = search_documents(store.documents, payload.question, payload.top_k)
    workflow = run_knowledge_workflow(payload.question, docs)
    store.add_workflow(workflow)
    return KnowledgeResponse(answer=workflow.final_result, documents=docs, workflow=workflow)


@router.get("/advisors", response_model=list[Advisor])
def list_advisors() -> list[Advisor]:
    return store.advisors


@router.post("/advisors/match")
def match_advisors(payload: AdvisorMatchRequest) -> dict[str, object]:
    matched = store.advisors[: payload.top_k]
    workflow = run_advisor_match_workflow(payload.profile, matched)
    store.add_workflow(workflow)
    return {"advisors": matched, "workflow": workflow}
