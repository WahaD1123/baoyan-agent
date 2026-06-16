from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class StudentProfile(BaseModel):
    id: str = Field(default_factory=lambda: new_id("profile"))
    name: str = "Demo Student"
    university: str = "Xiamen University"
    major: str = "Computer Science"
    rank_percent: float = Field(default=10, ge=0, le=100)
    research_interests: list[str] = Field(default_factory=lambda: ["AI", "systems"])
    projects: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=lambda: ["Shanghai", "Beijing"])
    preferred_schools: list[str] = Field(default_factory=list)
    notes: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


DocumentType = Literal["notice", "experience", "advisor", "resume", "paper", "other"]
SourceType = Literal["text", "pdf", "url", "sample"]


class DocumentChunk(BaseModel):
    id: str = Field(default_factory=lambda: new_id("chunk"))
    document_id: str = ""
    index: int = 0
    text: str
    keywords: list[str] = Field(default_factory=list)


class DocumentCreate(BaseModel):
    title: str
    doc_type: DocumentType = "other"
    content: str
    source: str = "manual"
    source_type: SourceType = "text"
    extracted: dict[str, Any] = Field(default_factory=dict)


class Document(DocumentCreate):
    id: str = Field(default_factory=lambda: new_id("doc"))
    keywords: list[str] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievedChunk(BaseModel):
    document_id: str
    document_title: str
    chunk_id: str
    text: str
    score: float
    hit_reason: str


class Advisor(BaseModel):
    id: str = Field(default_factory=lambda: new_id("advisor"))
    name: str
    university: str
    department: str = "Computer Science"
    research_areas: list[str] = Field(default_factory=list)
    homepage: str = ""
    summary: str = ""
    representative_works: list[str] = Field(default_factory=list)
    suitable_background: str = ""
    source_document_id: str = ""


class AgentResult(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent"))
    agent_name: str
    input_summary: str
    output: str
    references: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowStep(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    agent_result: AgentResult | None = None


class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("workflow"))
    workflow_type: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    steps: list[WorkflowStep] = Field(default_factory=list)
    final_result: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanRequest(BaseModel):
    profile: StudentProfile
    target: str = "CS baoyan application"


class PlanResponse(BaseModel):
    plan: str
    schools: list[str]
    timeline: list[str]
    workflow: WorkflowRun


class KnowledgeQuery(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=10)


class KnowledgeResponse(BaseModel):
    answer: str
    documents: list[Document]
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    workflow: WorkflowRun


class AdvisorMatchRequest(BaseModel):
    profile: StudentProfile
    top_k: int = Field(default=3, ge=1, le=10)


class AdvisorMatchResult(BaseModel):
    advisor: Advisor
    score: float
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    contact_suggestion: str = ""


class AdvisorMatchResponse(BaseModel):
    matches: list[AdvisorMatchResult]
    workflow: WorkflowRun


class UrlDocumentRequest(BaseModel):
    url: str
    doc_type: DocumentType = "notice"
    title: str = ""


class AdvisorUrlRequest(BaseModel):
    url: str
    title: str = ""


class AdvisorSearchRequest(BaseModel):
    university: str = ""
    direction: str = ""
    keywords: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)


class CrawlResult(BaseModel):
    url: str
    status: Literal["success", "failed"]
    title: str = ""
    content: str = ""
    extracted: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class EmailGenerationRequest(BaseModel):
    profile: StudentProfile
    advisor: Advisor | None = None
    purpose: str = "summer camp application"


class InterviewRequest(BaseModel):
    profile: StudentProfile
    target_school: str = "Target University"
    direction: str = "AI"


class MaterialResponse(BaseModel):
    content: str
    workflow: WorkflowRun
