import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { sampleAdvisors, sampleProfile } from "./api/mockData";
import { KnowledgePage } from "./pages/KnowledgePage";
import { MaterialsPage, type MaterialGeneration } from "./pages/MaterialsPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ProfilePage } from "./pages/ProfilePage";
import { WorkflowPage } from "./pages/WorkflowPage";
import type {
  Advisor,
  AdvisorMatchResult,
  DocumentItem,
  ProfileAnalysis,
  RetrievedChunk,
  SchoolRecommendation,
  StudentProfile,
  WorkflowRun,
} from "./types/domain";

type PageKey = "profile" | "planning" | "knowledge" | "materials" | "workflows";

const navItems: { key: PageKey; label: string }[] = [
  { key: "profile", label: "个人背景" },
  { key: "planning", label: "院校规划" },
  { key: "knowledge", label: "资料问答" },
  { key: "materials", label: "材料与面试" },
  { key: "workflows", label: "\u6267\u884c\u8bb0\u5f55" },
];

const pageDescriptions: Record<PageKey, string> = {
  profile: "先填写你的背景信息，系统会分析优势、短板和下一步准备重点。",
  planning: "根据你的画像生成冲刺、稳妥、保底院校建议和准备节奏。",
  knowledge: "上传院校通知、导师主页和经验贴，快速查询材料要求和方向信息。",
  materials: "生成联系邮件和模拟面试题，帮助你更快进入准备状态。",
  workflows: "\u67e5\u770b Planner\u3001MCP \u5de5\u5177\u3001Agent\u3001\u6a21\u578b\u8def\u7531\u548c Critic \u91cd\u5199\u7684\u5b8c\u6574\u6267\u884c\u8f68\u8ff9\u3002",
};

function App() {
  const [page, setPage] = useState<PageKey>("profile");
  const [profile, setProfile] = useState<StudentProfile>(sampleProfile);
  const [analysis, setAnalysis] = useState<ProfileAnalysis | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>(sampleAdvisors);
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([]);
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [matches, setMatches] = useState<AdvisorMatchResult[]>([]);
  const [plan, setPlan] = useState("填写背景后，一键生成适合你的申请规划。");
  const [recommendations, setRecommendations] = useState<SchoolRecommendation[]>([]);
  const [timeline, setTimeline] = useState<string[]>([]);
  const [planningEvidence, setPlanningEvidence] = useState<string[]>([]);
  const [answer, setAnswer] = useState("上传或添加资料后，可以直接询问报名材料、截止时间和考核形式。");
  const [email, setEmail] = useState("点击“生成导师邮件”后，这里会生成可继续修改的联系初稿。");
  const [resumeHighlights, setResumeHighlights] = useState("点击“生成简历亮点”后，这里会把项目、竞赛和研究兴趣整理成可放进简历的表达。");
  const [statement, setStatement] = useState("点击“生成个人陈述”后，这里会生成申请动机与研究兴趣片段。");
  const [interview, setInterview] = useState("点击“生成面试题”后，这里会展示围绕个人项目和目标方向的模拟问题。");
  const [serviceReady, setServiceReady] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [analyzingProfile, setAnalyzingProfile] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [askingKnowledge, setAskingKnowledge] = useState(false);
  const [documentBusy, setDocumentBusy] = useState(false);
  const [advisorBusy, setAdvisorBusy] = useState(false);
  const [advisorSearchBusy, setAdvisorSearchBusy] = useState(false);
  const [matchingAdvisors, setMatchingAdvisors] = useState(false);
  const [generatingMaterial, setGeneratingMaterial] = useState<MaterialGeneration | null>(null);
  const [knowledgeStatus, setKnowledgeStatus] = useState("资料库已就绪，可以导入资料、提问或匹配导师。");

  useEffect(() => {
    Promise.all([api.getProfile(), api.getDocuments(), api.getAdvisors(), api.getWorkflows(), api.getLlmHealth()]).then(
      ([nextProfile, nextDocuments, nextAdvisors, nextWorkflows, nextLlm]) => {
        setProfile(nextProfile);
        setDocuments(nextDocuments);
        setAdvisors(nextAdvisors);
        setWorkflows(nextWorkflows);
        setServiceReady(nextLlm.has_api_key || nextLlm.provider === "mock");
      }
    );
  }, []);

  const currentTitle = useMemo(
    () => navItems.find((item) => item.key === page)?.label ?? "保研申请助手",
    [page]
  );

  function pushWorkflow(workflow: WorkflowRun) {
    setWorkflows((items) => [workflow, ...items.filter((item) => item.id !== workflow.id)]);
  }

  async function saveProfile(nextProfile: StudentProfile) {
    setSavingProfile(true);
    try {
      const saved = await api.saveProfile(nextProfile);
      setProfile(saved);
    } finally {
      setSavingProfile(false);
    }
  }

  async function analyzeProfile(nextProfile: StudentProfile) {
    setAnalyzingProfile(true);
    try {
      const result = await api.analyzeProfile(nextProfile);
      setAnalysis(result);
      setProfile(nextProfile);
    } finally {
      setAnalyzingProfile(false);
    }
  }

  async function generatePlan() {
    setPlanning(true);
    try {
      const result = await api.generatePlan(profile);
      setPlan(result.plan);
      setAnalysis(result.analysis);
      setRecommendations(result.recommendations);
      setTimeline(result.timeline);
      setPlanningEvidence(result.evidence);
      pushWorkflow(result.workflow);
      setPage("planning");
    } finally {
      setPlanning(false);
    }
  }

  async function addTextDocument(payload: { title: string; doc_type: string; content: string; source: string }) {
    setDocumentBusy(true);
    setKnowledgeStatus("正在解析文本资料，生成全文分析和引用片段...");
    try {
      const result = await api.addTextDocument(payload);
      setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`文本资料「${result.document.title}」已完成入库和全文分析。`);
    } finally {
      setDocumentBusy(false);
    }
  }

  async function addUrlDocument(payload: { title?: string; doc_type: string; url: string }) {
    setDocumentBusy(true);
    setKnowledgeStatus("正在抓取网页、清洗正文，并生成全文分析...");
    try {
      const result = await api.addUrlDocument(payload);
      setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`网页资料「${result.document.title}」已完成入库和全文分析。`);
    } finally {
      setDocumentBusy(false);
    }
  }

  async function uploadPdfDocument(file: File, docType: string, title: string) {
    setDocumentBusy(true);
    setKnowledgeStatus("正在解析 PDF 正文，抽取结构化字段和引用片段...");
    try {
      const result = await api.uploadPdfDocument(file, docType, title);
      setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`PDF「${result.document.title}」已完成入库和全文分析。`);
    } finally {
      setDocumentBusy(false);
    }
  }

  async function addAdvisorUrl(url: string, title?: string) {
    setAdvisorBusy(true);
    setKnowledgeStatus("正在抓取导师主页，抽取姓名、单位、研究方向和适合背景...");
    try {
      const result = await api.addAdvisorUrl(url, title);
      setAdvisors((items) => [result.advisor, ...items.filter((item) => item.id !== result.advisor.id)]);
      setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`导师「${result.advisor.name}」已入库，可用于匹配。`);
    } finally {
      setAdvisorBusy(false);
    }
  }

  async function searchAdvisor(payload: { university: string; direction: string; keywords: string[] }) {
    setAdvisorSearchBusy(true);
    setKnowledgeStatus("正在检索本地导师库...");
    try {
      const result = await api.searchAdvisors(payload);
      setAdvisors(result.advisors);
      setAnswer(result.message);
      setKnowledgeStatus(`已找到 ${result.advisors.length} 位候选导师。`);
    } finally {
      setAdvisorSearchBusy(false);
    }
  }

  async function askKnowledge(question: string) {
    setAskingKnowledge(true);
    setChunks([]);
    setKnowledgeStatus("正在读取全文分析结果并召回引用片段...");
    setAnswer("正在读取资料库、核对引用来源，并组织回答...");
    try {
      const result = await api.askKnowledge(question);
      setAnswer(result.answer);
      setChunks(result.chunks);
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`问答完成，已返回 ${result.chunks.length} 条引用片段。`);
    } finally {
      setAskingKnowledge(false);
    }
  }

  async function matchAdvisors() {
    setMatchingAdvisors(true);
    setKnowledgeStatus("正在读取用户画像和导师结构化资料，计算匹配分数...");
    try {
      const result = await api.matchAdvisors(profile);
      setMatches(result.matches);
      setAdvisors(result.matches.map((match) => match.advisor));
      setAnswer("已根据你的研究兴趣和项目背景生成导师匹配建议。");
      pushWorkflow(result.workflow);
      setKnowledgeStatus(`导师匹配完成，生成 ${result.matches.length} 条推荐结果。`);
    } finally {
      setMatchingAdvisors(false);
    }
  }

  async function generateEmail() {
    setGeneratingMaterial("email");
    try {
      const result = await api.generateEmail(profile, advisors[0]);
      setEmail(result.content);
      pushWorkflow(result.workflow);
    } finally {
      setGeneratingMaterial(null);
    }
  }

  async function generateResumeHighlights() {
    setGeneratingMaterial("resume");
    try {
      const result = await api.generateResumeHighlights(profile);
      setResumeHighlights(result.content);
      pushWorkflow(result.workflow);
    } finally {
      setGeneratingMaterial(null);
    }
  }

  async function generateStatement() {
    setGeneratingMaterial("statement");
    try {
      const result = await api.generateStatement(profile);
      setStatement(result.content);
      pushWorkflow(result.workflow);
    } finally {
      setGeneratingMaterial(null);
    }
  }

  async function generateInterview() {
    setGeneratingMaterial("interview");
    try {
      const result = await api.generateInterview(profile);
      setInterview(result.content);
      pushWorkflow(result.workflow);
    } finally {
      setGeneratingMaterial(null);
    }
  }

  async function refreshWorkflows() {
    setWorkflows(await api.getWorkflows());
  }

  return (
    <div className="siteShell">
      <header className="heroStage">
        <nav className="siteNav">
          <button className="wordmark" onClick={() => setPage("profile")}>
            <span>保</span>
            <strong>保研申请助手</strong>
          </button>
          <div className="navLinks">
            {navItems.map((item) => (
              <button
                className={page === item.key ? "active" : ""}
                key={item.key}
                onClick={() => setPage(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <button className="navCta" onClick={() => setPage("profile")}>
            开始填写
          </button>
        </nav>

        <div className="heroGrid">
          <div className="heroCopy">
            <p className="heroKicker">CS 保研申请工作台</p>
            <h1>
              先看清自己
              <span>再决定投哪里</span>
            </h1>
            <p>
              这套系统会先分析你的背景，再生成冲刺、稳妥、保底院校建议，并补上后续材料和面试准备节奏。
            </p>
            <div className="heroActions">
              <button onClick={() => setPage("profile")}>填写背景</button>
              <button className="ghostButton" onClick={() => setPage("planning")}>
                查看规划
              </button>
            </div>
          </div>

          <div className="heroVisual" aria-hidden="true">
            <div className="visualPanel mainPanel">
              <span>第一步</span>
              <strong>完成背景画像</strong>
              <p>把排名、绩点、项目、竞赛和目标方向整理清楚，后续推荐才会真正有针对性。</p>
            </div>
            <div className="visualPanel advisorPanel">
              <span>第二步</span>
              <strong>生成院校梯度</strong>
              <p>系统会把推荐结果分成冲刺、稳妥、保底三档，并提示风险和准备重点。</p>
            </div>
            <div className="visualPanel notePanel">
              <span>第三步</span>
              <strong>进入材料准备</strong>
              <p>完成规划后，再继续联系导师、生成邮件和做模拟面试，学习成本会更低。</p>
            </div>
            <div className="visualLine lineOne" />
            <div className="visualLine lineTwo" />
          </div>
        </div>
      </header>

      <main className="workspace">
        <div className="workspaceIntro">
          <div>
            <p className="eyebrow">当前模块</p>
            <h2>{currentTitle}</h2>
            <p>{pageDescriptions[page]}</p>
          </div>
          <div className="statusPill">{serviceReady ? "服务可用" : "演示模式"}</div>
        </div>

        {page === "profile" && (
          <ProfilePage
            analysis={analysis}
            onAnalyze={analyzeProfile}
            onProfileChange={setProfile}
            onSave={saveProfile}
            onStartPlanning={generatePlan}
            profile={profile}
            saving={savingProfile}
            analyzing={analyzingProfile}
            planning={planning}
          />
        )}
        {page === "planning" && (
          <PlanningPage
            profile={profile}
            analysis={analysis}
            plan={plan}
            recommendations={recommendations}
            timeline={timeline}
            evidence={planningEvidence}
            onGenerate={generatePlan}
            loading={planning}
          />
        )}
        {page === "knowledge" && (
          <KnowledgePage
            documents={documents}
            advisors={advisors}
            answer={answer}
            isAsking={askingKnowledge}
            documentBusy={documentBusy}
            advisorBusy={advisorBusy}
            advisorSearchBusy={advisorSearchBusy}
            matchingAdvisors={matchingAdvisors}
            statusText={knowledgeStatus}
            chunks={chunks}
            matches={matches}
            onAddText={addTextDocument}
            onAddUrl={addUrlDocument}
            onUploadPdf={uploadPdfDocument}
            onAddAdvisorUrl={addAdvisorUrl}
            onSearchAdvisor={searchAdvisor}
            onAsk={askKnowledge}
            onMatch={matchAdvisors}
          />
        )}
        {page === "materials" && (
          <MaterialsPage
            email={email}
            resumeHighlights={resumeHighlights}
            statement={statement}
            interview={interview}
            generating={generatingMaterial}
            onEmail={generateEmail}
            onResumeHighlights={generateResumeHighlights}
            onStatement={generateStatement}
            onInterview={generateInterview}
          />
        )}
        {page === "workflows" && (
          <WorkflowPage workflows={workflows} onRefresh={refreshWorkflows} />
        )}
      </main>
    </div>
  );
}

export default App;
