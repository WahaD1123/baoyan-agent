import { sampleAdvisors, sampleDocuments, sampleProfile, sampleWorkflow } from "./mockData";
import type { Advisor, AdvisorMatchResult, DocumentItem, RetrievedChunk, StudentProfile, WorkflowRun } from "../types/domain";

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
  getLlmHealth: () =>
    request<{ provider: string; model: string; base_url: string; has_api_key: boolean }>(
      "/api/health/llm",
      undefined,
      { provider: "mock", model: "qwen-vl-max", base_url: "", has_api_key: false }
    ),
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
      {
        ...payload,
        source_type: "text",
        id: `doc_${Date.now()}`,
        keywords: [],
        chunks: [],
        extracted: {},
        created_at: new Date().toISOString()
      }
    ),
  addTextDocument: (payload: Pick<DocumentItem, "title" | "doc_type" | "content" | "source">) =>
    request<{ document: DocumentItem; workflow: WorkflowRun }>(
      "/api/knowledge/documents/text",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ ...payload, source_type: "text" }) },
      {
        document: {
          ...payload,
          source_type: "text",
          id: `doc_${Date.now()}`,
          keywords: [],
          chunks: [],
          extracted: {},
          created_at: new Date().toISOString()
        },
        workflow: sampleWorkflow
      }
    ),
  addUrlDocument: (payload: { url: string; doc_type: string; title?: string }) =>
    request<{ document: DocumentItem; extracted: Record<string, unknown>; workflow: WorkflowRun }>(
      "/api/knowledge/documents/url",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) },
      {
        document: sampleDocuments[0],
        extracted: sampleDocuments[0].extracted,
        workflow: sampleWorkflow
      }
    ),
  uploadPdfDocument: (file: File, docType: string, title: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    form.append("title", title);
    return request<{ document: DocumentItem; workflow: WorkflowRun }>(
      "/api/knowledge/documents/upload",
      { method: "POST", body: form },
      { document: sampleDocuments[0], workflow: sampleWorkflow }
    );
  },
  askKnowledge: (question: string) =>
    request<{ answer: string; documents: DocumentItem[]; chunks: RetrievedChunk[]; workflow: WorkflowRun }>(
      "/api/knowledge/query",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ question }) },
      { answer: "演示回答：请先加入真实资料，系统会基于资料内容回答并展示引用片段。", documents: sampleDocuments, chunks: [], workflow: sampleWorkflow }
    ),
  getAdvisors: () => request<Advisor[]>("/api/knowledge/advisors", undefined, sampleAdvisors),
  addAdvisorUrl: (url: string, title?: string) =>
    request<{ advisor: Advisor; document: DocumentItem; workflow: WorkflowRun }>(
      "/api/knowledge/advisors/url",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ url, title }) },
      { advisor: sampleAdvisors[0], document: sampleDocuments[1], workflow: sampleWorkflow }
    ),
  searchAdvisors: (payload: { university?: string; direction?: string; keywords?: string[] }) =>
    request<{ advisors: Advisor[]; message: string }>(
      "/api/knowledge/advisors/search",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) },
      { advisors: sampleAdvisors, message: "已展示本地导师库中的示例候选。" }
    ),
  matchAdvisors: (profile: StudentProfile) =>
    request<{ matches: AdvisorMatchResult[]; workflow: WorkflowRun }>(
      "/api/knowledge/advisors/match",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile }) },
      {
        matches: sampleAdvisors.map((advisor, index) => ({
          advisor,
          score: 88 - index * 8,
          reasons: ["研究方向与个人画像匹配"],
          risks: [],
          contact_suggestion: "建议在邮件中突出相关项目，并附上简洁版简历。"
        })),
        workflow: sampleWorkflow
      }
    ),
  generatePlan: (profile: StudentProfile) =>
    request<{ plan: string; schools: string[]; timeline: string[]; workflow: WorkflowRun }>(
      "/api/planning/generate",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile }) },
      {
        plan: "演示规划：冲刺上海交通大学，稳妥选择浙江大学，保底厦门大学相关实验室。先补齐材料，再联系导师，最后集中练习面试。",
        schools: ["冲刺：上海交通大学计算机", "稳妥：浙江大学计算机", "保底：厦门大学人工智能方向"],
        timeline: ["第 1 周：整理材料", "第 2 周：联系导师", "第 3 周：模拟面试"],
        workflow: sampleWorkflow
      }
    ),
  generateEmail: (profile: StudentProfile, advisor?: Advisor) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/materials/email",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, advisor }) },
      { content: "老师您好，我是示例同学，想向您简要介绍我的研究背景与申请意向……", workflow: sampleWorkflow }
    ),
  generateInterview: (profile: StudentProfile) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/interview/mock",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, target_school: "SJTU", direction: "AI" }) },
      { content: "1. 请介绍你的核心项目。\n2. 请解释注意力机制的基本思想。\n3. 如果继续优化这个系统，你会优先改进哪里？", workflow: sampleWorkflow }
    ),
  getWorkflows: () => request<WorkflowRun[]>("/api/workflows", undefined, [sampleWorkflow])
};
