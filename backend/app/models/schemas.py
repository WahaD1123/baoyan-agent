from datetime import datetime
from typing import Literal
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


class DocumentCreate(BaseModel):
    title: str
    doc_type: Literal["notice", "experience", "advisor", "resume", "paper", "other"] = "other"
    content: str
    source: str = "manual"


class Document(DocumentCreate):
    id: str = Field(default_factory=lambda: new_id("doc"))
    keywords: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Advisor(BaseModel):
    id: str = Field(default_factory=lambda: new_id("advisor"))
    name: str
    university: str
    department: str = "Computer Science"
    research_areas: list[str] = Field(default_factory=list)
    homepage: str = ""
    summary: str = ""


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
    workflow: WorkflowRun


class AdvisorMatchRequest(BaseModel):
    profile: StudentProfile
    top_k: int = Field(default=3, ge=1, le=10)


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
