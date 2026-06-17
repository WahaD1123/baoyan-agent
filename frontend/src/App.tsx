import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { sampleAdvisors, sampleDocuments, sampleProfile } from "./api/mockData";
import { KnowledgePage } from "./pages/KnowledgePage";
import { MaterialsPage } from "./pages/MaterialsPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ProfilePage } from "./pages/ProfilePage";
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

type PageKey = "profile" | "planning" | "knowledge" | "materials";

const navItems: { key: PageKey; label: string }[] = [
  { key: "profile", label: "个人背景" },
  { key: "planning", label: "院校规划" },
  { key: "knowledge", label: "资料问答" },
  { key: "materials", label: "材料与面试" },
];

const pageDescriptions: Record<PageKey, string> = {
  profile: "先填写你的背景信息，系统会分析优势、短板和下一步准备重点。",
  planning: "根据你的画像生成冲刺、稳妥、保底院校建议和准备节奏。",
  knowledge: "上传院校通知、导师主页和经验贴，快速查询材料要求和方向信息。",
  materials: "生成联系邮件和模拟面试题，帮助你更快进入准备状态。",
};

function App() {
  const [page, setPage] = useState<PageKey>("profile");
  const [profile, setProfile] = useState<StudentProfile>(sampleProfile);
  const [analysis, setAnalysis] = useState<ProfileAnalysis | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>(sampleDocuments);
  const [advisors, setAdvisors] = useState<Advisor[]>(sampleAdvisors);
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([]);
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [matches, setMatches] = useState<AdvisorMatchResult[]>([]);
  const [plan, setPlan] = useState("填写背景后，一键生成适合你的申请规划。");
  const [recommendations, setRecommendations] = useState<SchoolRecommendation[]>([]);
  const [timeline, setTimeline] = useState<string[]>([]);
  const [planningEvidence, setPlanningEvidence] = useState<string[]>([]);
  const [answer, setAnswer] = useState("上传或添加资料后，可以直接询问报名材料、截止时间和考核形式。");
  const [email, setEmail] = useState("系统会根据你的画像和导师信息生成联系邮件初稿。");
  const [interview, setInterview] = useState("系统会围绕你的项目经历和目标方向生成模拟面试题。");
  const [serviceReady, setServiceReady] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [analyzingProfile, setAnalyzingProfile] = useState(false);
  const [planning, setPlanning] = useState(false);

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
      setPage("planning");
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
    } finally {
      setPlanning(false);
    }
  }

  async function addTextDocument(payload: { title: string; doc_type: string; content: string; source: string }) {
    const result = await api.addTextDocument(payload);
    setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
    pushWorkflow(result.workflow);
  }

  async function addUrlDocument(payload: { title?: string; doc_type: string; url: string }) {
    const result = await api.addUrlDocument(payload);
    setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
    pushWorkflow(result.workflow);
  }

  async function uploadPdfDocument(file: File, docType: string, title: string) {
    const result = await api.uploadPdfDocument(file, docType, title);
    setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
    pushWorkflow(result.workflow);
  }

  async function addAdvisorUrl(url: string, title?: string) {
    const result = await api.addAdvisorUrl(url, title);
    setAdvisors((items) => [result.advisor, ...items.filter((item) => item.id !== result.advisor.id)]);
    setDocuments((items) => [result.document, ...items.filter((item) => item.id !== result.document.id)]);
    pushWorkflow(result.workflow);
  }

  async function searchAdvisor(payload: { university: string; direction: string; keywords: string[] }) {
    const result = await api.searchAdvisors(payload);
    setAdvisors(result.advisors);
    setAnswer(result.message);
  }

  async function askKnowledge(question: string) {
    const result = await api.askKnowledge(question);
    setAnswer(result.answer);
    setChunks(result.chunks);
    pushWorkflow(result.workflow);
  }

  async function matchAdvisors() {
    const result = await api.matchAdvisors(profile);
    setMatches(result.matches);
    setAdvisors(result.matches.map((match) => match.advisor));
    setAnswer("已根据你的研究兴趣和项目背景生成导师匹配建议。");
    pushWorkflow(result.workflow);
  }

  async function generateEmail() {
    const result = await api.generateEmail(profile, advisors[0]);
    setEmail(result.content);
    pushWorkflow(result.workflow);
  }

  async function generateInterview() {
    const result = await api.generateInterview(profile);
    setInterview(result.content);
    pushWorkflow(result.workflow);
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
            interview={interview}
            onEmail={generateEmail}
            onInterview={generateInterview}
          />
        )}
      </main>
    </div>
  );
}

export default App;
