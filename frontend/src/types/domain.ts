export type StudentProfile = {
  id: string;
  name: string;
  university: string;
  major: string;
  rank_percent: number;
  gpa: number;
  english_score: string;
  target_degree: string;
  risk_preference: "conservative" | "balanced" | "aggressive";
  research_interests: string[];
  projects: string[];
  competitions: string[];
  publications: string[];
  target_regions: string[];
  preferred_schools: string[];
  notes: string;
  updated_at: string;
};

export type DocumentItem = {
  id: string;
  title: string;
  doc_type: string;
  source_type: string;
  content: string;
  source: string;
  keywords: string[];
  chunks: DocumentChunk[];
  extracted: Record<string, unknown>;
  analysis?: Record<string, unknown>;
  created_at: string;
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  index: number;
  text: string;
  keywords: string[];
};

export type RetrievedChunk = {
  document_id: string;
  document_title: string;
  chunk_id: string;
  text: string;
  score: number;
  hit_reason: string;
};

export type Advisor = {
  id: string;
  name: string;
  university: string;
  department: string;
  research_areas: string[];
  homepage: string;
  summary: string;
  representative_works: string[];
  suitable_background: string;
  source_document_id: string;
};

export type AdvisorMatchResult = {
  advisor: Advisor;
  score: number;
  reasons: string[];
  risks: string[];
  contact_suggestion: string;
};

export type AgentResult = {
  id: string;
  agent_name: string;
  input_summary: string;
  output: string;
  references: string[];
  created_at: string;
};

export type WorkflowStep = {
  name: string;
  status: string;
  agent_result?: AgentResult;
};

export type WorkflowRun = {
  id: string;
  workflow_type: string;
  status: string;
  steps: WorkflowStep[];
  final_result: string;
  created_at: string;
};

export type ProfileAnalysis = {
  overall_score: number;
  academic_score: number;
  research_score: number;
  project_score: number;
  competition_score: number;
  language_score: number;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  summary: string;
};

export type SchoolRecommendation = {
  school_name: string;
  program_name: string;
  level: "challenge" | "stable" | "safe";
  match_score: number;
  reasons: string[];
  risks: string[];
  todo: string[];
  evidence: string[];
  materials: string[];
  exam_format: string[];
  deadline: string;
  agent_insight: string;
};
