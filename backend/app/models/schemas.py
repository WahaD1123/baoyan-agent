from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class StudentProfile(BaseModel):
    id: str = Field(default_factory=lambda: new_id("profile"))
    name: str = "张三"
    university: str = "厦门大学"
    major: str = "计算机科学与技术"
    rank_percent: float = Field(default=10, ge=0, le=100)
    gpa: float = Field(default=3.7, ge=0, le=4.5)
    english_score: str = "CET-6 500"
    target_degree: str = "master"
    risk_preference: Literal["conservative", "balanced", "aggressive"] = "balanced"
    research_interests: list[str] = Field(default_factory=lambda: ["机器学习", "智能体系统"])
    projects: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=lambda: ["上海", "北京"])
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
    analysis: dict[str, Any] = Field(default_factory=dict)


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


class CriticDecision(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    summary: str
    issues: list[str] = Field(default_factory=list, max_length=3)
    suggestions: list[str] = Field(default_factory=list, max_length=3)
    user_inputs: list[str] = Field(default_factory=list, max_length=5)


class ToolCallTrace(BaseModel):
    tool_name: str
    transport: Literal["mcp", "local_fallback"] = "mcp"
    arguments_summary: str = ""
    result_summary: str = ""
    duration_ms: int = Field(default=0, ge=0)
    fallback_reason: str = ""


class WorkflowStep(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "completed"
    agent_result: AgentResult | None = None
    step_type: Literal["planner", "tool", "agent", "condition"] = "agent"
    capability: str = ""
    decision_reason: str = ""
    model_name: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = Field(default=0, ge=0)
    tool_call: ToolCallTrace | None = None
    error: str = ""


class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("workflow"))
    workflow_type: str
    status: Literal["pending", "running", "completed", "failed"] = "completed"
    steps: list[WorkflowStep] = Field(default_factory=list)
    final_result: str = ""
    plan_source: Literal["fixed", "planner", "fallback"] = "fixed"
    planner_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanRequest(BaseModel):
    profile: StudentProfile
    target: str = "CS baoyan application"


class ProfileAnalysis(BaseModel):
    overall_score: int
    academic_score: int
    research_score: int
    project_score: int
    competition_score: int
    language_score: int
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = ""


class EvidenceReference(BaseModel):
    title: str
    url: str = ""


class SchoolRecommendation(BaseModel):
    school_name: str
    program_name: str
    level: Literal["challenge", "stable", "safe"]
    match_score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    todo: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    exam_format: list[str] = Field(default_factory=list)
    deadline: str = ""
    notice_url: str = ""
    agent_insight: str = ""


class PlanResponse(BaseModel):
    plan: str
    analysis: ProfileAnalysis
    recommendations: list[SchoolRecommendation]
    timeline: list[str]
    evidence: list[str] = Field(default_factory=list)
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


class ResumeHighlightRequest(BaseModel):
    profile: StudentProfile
    target_direction: str = "AI systems"


class StatementRequest(BaseModel):
    profile: StudentProfile
    target_school: str = "Target University"
    direction: str = "AI"
    tone: str = "concise"


class InterviewRequest(BaseModel):
    profile: StudentProfile
    target_school: str = "Target University"
    direction: str = "AI"


class MaterialResponse(BaseModel):
    content: str
    workflow: WorkflowRun
