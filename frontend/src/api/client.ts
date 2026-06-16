import { sampleAdvisors, sampleDocuments, sampleProfile, sampleWorkflow } from "./mockData";
import type { Advisor, DocumentItem, StudentProfile, WorkflowRun } from "../types/domain";

const jsonHeaders = { "Content-Type": "application/json" };

async function request<T>(path: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const response = await fetch(path, options);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  } catch {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`Request failed: ${path}`);
  }
}

export const api = {
  getProfile: () => request<StudentProfile>("/api/profile", undefined, sampleProfile),
  saveProfile: (profile: StudentProfile) =>
    request<StudentProfile>(
      "/api/profile",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(profile) },
      profile
    ),
  getDocuments: () => request<DocumentItem[]>("/api/knowledge/documents", undefined, sampleDocuments),
  addDocument: (payload: Pick<DocumentItem, "title" | "doc_type" | "content" | "source">) =>
    request<DocumentItem>(
      "/api/knowledge/documents",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) },
      { ...payload, id: `doc_${Date.now()}`, keywords: [], created_at: new Date().toISOString() }
    ),
  askKnowledge: (question: string) =>
    request<{ answer: string; documents: DocumentItem[]; workflow: WorkflowRun }>(
      "/api/knowledge/query",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ question }) },
      { answer: "Mock RAG answer based on uploaded materials.", documents: sampleDocuments, workflow: sampleWorkflow }
    ),
  getAdvisors: () => request<Advisor[]>("/api/knowledge/advisors", undefined, sampleAdvisors),
  matchAdvisors: (profile: StudentProfile) =>
    request<{ advisors: Advisor[]; workflow: WorkflowRun }>(
      "/api/knowledge/advisors/match",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile }) },
      { advisors: sampleAdvisors, workflow: sampleWorkflow }
    ),
  generatePlan: (profile: StudentProfile) =>
    request<{ plan: string; schools: string[]; timeline: string[]; workflow: WorkflowRun }>(
      "/api/planning/generate",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile }) },
      {
        plan: "Mock plan: sprint SJTU, stable ZJU, safe XMU. Prepare materials and contact advisors.",
        schools: ["Sprint: SJTU CS", "Stable: ZJU CS", "Safe: XMU AI Lab"],
        timeline: ["Week 1: materials", "Week 2: advisor emails", "Week 3: interview practice"],
        workflow: sampleWorkflow
      }
    ),
  generateEmail: (profile: StudentProfile, advisor?: Advisor) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/materials/email",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, advisor }) },
      { content: "Dear Professor, I am writing to introduce my research background and application interest...", workflow: sampleWorkflow }
    ),
  generateInterview: (profile: StudentProfile) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/interview/mock",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, target_school: "SJTU", direction: "AI" }) },
      { content: "1. Please introduce your research project.\n2. Explain self-attention.\n3. How would you improve your system?", workflow: sampleWorkflow }
    ),
  getWorkflows: () => request<WorkflowRun[]>("/api/workflows", undefined, [sampleWorkflow])
};
