import type {
  Advisor,
  AdvisorMatchResult,
  DocumentItem,
  ProfileAnalysis,
  RetrievedChunk,
  SchoolRecommendation,
  StudentProfile,
  WorkflowRun,
} from "../types/domain";
import { sampleAdvisors, sampleDocuments, sampleProfile, sampleWorkflow } from "./mockData";

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
      { provider: "mock", model: "qwen-plus", base_url: "", has_api_key: false }
    ),
  getProfile: () => request<StudentProfile>("/api/profile", undefined, sampleProfile),
  saveProfile: (profile: StudentProfile) =>
    request<StudentProfile>(
      "/api/profile",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(profile) },
      profile
    ),
  analyzeProfile: (profile: StudentProfile) =>
    request<ProfileAnalysis>(
      "/api/profile/analyze",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(profile) }
    ),
  getDocuments: () => request<DocumentItem[]>("/api/knowledge/documents"),
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
        created_at: new Date().toISOString(),
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
          created_at: new Date().toISOString(),
        },
        workflow: sampleWorkflow,
      }
    ),
  addUrlDocument: (payload: { url: string; doc_type: string; title?: string }) =>
    request<{ document: DocumentItem; extracted: Record<string, unknown>; workflow: WorkflowRun }>(
      "/api/knowledge/documents/url",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify(payload) },
      {
        document: sampleDocuments[0],
        extracted: sampleDocuments[0].extracted,
        workflow: sampleWorkflow,
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
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ question }) }
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
          reasons: ["研究方向与个人画像匹配。"],
          risks: [],
          contact_suggestion: "建议在邮件中突出相关项目，并附上简历。",
        })),
        workflow: sampleWorkflow,
      }
    ),
  generatePlan: (profile: StudentProfile) =>
    request<{
      plan: string;
      analysis: ProfileAnalysis;
      recommendations: SchoolRecommendation[];
      timeline: string[];
      evidence: string[];
      workflow: WorkflowRun;
    }>(
      "/api/planning/generate",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile }) }
    ),
  generateEmail: (profile: StudentProfile, advisor?: Advisor) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/materials/email",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, advisor }) },
      { content: "老师您好，我是示例同学，想向您简要介绍我的研究背景与申请意向。", workflow: sampleWorkflow }
    ),
  generateResumeHighlights: (profile: StudentProfile) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/materials/resume-highlights",
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({
          profile,
          target_direction: profile.research_interests.join(" / ") || "AI systems"
        })
      },
      {
        content:
          "## 简历亮点\n1. 围绕多智能体保研助手完成任务拆解、接口联调和 workflow 展示。\n2. 将课程推荐系统经历整理为用户画像与推荐逻辑实践。\n\n## 质量检查\n建议补充项目规模、技术栈和可量化结果。",
        workflow: sampleWorkflow
      }
    ),
  generateStatement: (profile: StudentProfile) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/materials/statement",
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({
          profile,
          target_school: profile.preferred_schools[0] || "目标院校",
          direction: profile.research_interests[0] || "AI",
          tone: "concise"
        })
      },
      {
        content:
          "## 个人陈述\n我希望围绕智能系统方向继续学习，把项目实践中的工程能力和研究问题结合起来。\n\n## 质量检查\n建议加入更具体的项目证据和目标导师方向。",
        workflow: sampleWorkflow
      }
    ),
  generateInterview: (profile: StudentProfile) =>
    request<{ content: string; workflow: WorkflowRun }>(
      "/api/interview/mock",
      { method: "POST", headers: jsonHeaders, body: JSON.stringify({ profile, target_school: "SJTU", direction: "AI" }) },
      {
        content:
          "1. 请介绍你最核心的项目。\n2. 请解释注意力机制的基本思想。\n3. 如果继续优化这个系统，你会优先改进哪里？",
        workflow: sampleWorkflow,
      }
    ),
  getWorkflows: () => request<WorkflowRun[]>("/api/workflows", undefined, [sampleWorkflow]),
};
