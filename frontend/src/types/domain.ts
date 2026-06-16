export type StudentProfile = {
  id: string;
  name: string;
  university: string;
  major: string;
  rank_percent: number;
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
