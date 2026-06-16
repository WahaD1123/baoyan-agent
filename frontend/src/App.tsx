import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { sampleAdvisors, sampleDocuments, sampleProfile, sampleWorkflow } from "./api/mockData";
import { KnowledgePage } from "./pages/KnowledgePage";
import { MaterialsPage } from "./pages/MaterialsPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ProfilePage } from "./pages/ProfilePage";
import { WorkflowPage } from "./pages/WorkflowPage";
import type {
  Advisor,
  AdvisorMatchResult,
  DocumentItem,
  RetrievedChunk,
  StudentProfile,
  WorkflowRun
} from "./types/domain";

type PageKey = "profile" | "knowledge" | "planning" | "materials" | "workflows";

const navItems: { key: PageKey; label: string }[] = [
  { key: "profile", label: "我的画像" },
  { key: "knowledge", label: "资料库" },
  { key: "planning", label: "院校规划" },
  { key: "materials", label: "材料面试" },
  { key: "workflows", label: "执行记录" }
];

const pageDescriptions: Record<PageKey, string> = {
  profile: "先确认个人背景，再让后续推荐更贴近你的申请目标。",
  knowledge: "把院校通知、导师主页、经验贴和 PDF 统一整理成可查询资料。",
  planning: "根据画像和资料，生成冲稳保策略与准备节奏。",
  materials: "围绕导师联系、申请邮件和模拟面试快速生成初稿。",
  workflows: "查看每一次生成背后的步骤，方便课程展示和小组协作。"
};

function App() {
  const [page, setPage] = useState<PageKey>("knowledge");
  const [profile, setProfile] = useState<StudentProfile>(sampleProfile);
  const [documents, setDocuments] = useState<DocumentItem[]>(sampleDocuments);
  const [advisors, setAdvisors] = useState<Advisor[]>(sampleAdvisors);
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([sampleWorkflow]);
  const [chunks, setChunks] = useState<RetrievedChunk[]>([]);
  const [matches, setMatches] = useState<AdvisorMatchResult[]>([]);
  const [plan, setPlan] = useState("点击“生成规划”后，这里会展示院校梯度、时间安排和准备建议。");
  const [schools, setSchools] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<string[]>([]);
  const [answer, setAnswer] = useState("上传或抓取资料后，可以直接询问报名材料、截止时间、考核形式等问题。");
  const [email, setEmail] = useState("点击“生成导师邮件”后，这里会生成可继续修改的联系初稿。");
  const [interview, setInterview] = useState("点击“生成面试题”后，这里会展示围绕个人项目和目标方向的模拟问题。");
  const [serviceReady, setServiceReady] = useState(false);

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
    () => navItems.find((item) => item.key === page)?.label ?? "保研申请助理",
    [page]
  );

  async function refreshWorkflows() {
    setWorkflows(await api.getWorkflows());
  }

  async function generatePlan() {
    const result = await api.generatePlan(profile);
    setPlan(result.plan);
    setSchools(result.schools);
    setTimeline(result.timeline);
    pushWorkflow(result.workflow);
  }

  function pushWorkflow(workflow: WorkflowRun) {
    setWorkflows((items) => [workflow, ...items.filter((item) => item.id !== workflow.id)]);
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
    setAnswer(result.workflow.final_result);
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
          <button className="wordmark" onClick={() => setPage("knowledge")}>
            <span>保</span>
            <strong>保研申请助理</strong>
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
          <button className="navCta" onClick={() => setPage("knowledge")}>开始整理</button>
        </nav>

        <div className="heroGrid">
          <div className="heroCopy">
            <p className="heroKicker">CS 保研申请工作台</p>
            <h1>
              从资料到联系，
              <span>一次理清。</span>
            </h1>
            <p>
              整理院校通知、导师主页和经验贴，生成有引用的问答、导师匹配建议与申请准备清单。
            </p>
            <div className="heroActions">
              <button onClick={() => setPage("knowledge")}>进入资料库</button>
              <button className="ghostButton" onClick={() => setPage("planning")}>生成申请规划</button>
            </div>
          </div>

          <div className="heroVisual" aria-hidden="true">
            <div className="visualPanel mainPanel">
              <span>今日重点</span>
              <strong>补齐夏令营材料清单</strong>
              <p>已整理截止时间、报名入口、考核形式和推荐准备动作。</p>
            </div>
            <div className="visualPanel advisorPanel">
              <span>导师候选</span>
              <strong>6 位可优先联系</strong>
              <p>按研究方向、项目经历和学校偏好排序。</p>
            </div>
            <div className="visualPanel notePanel">
              <span>引用依据</span>
              <strong>12 条资料片段</strong>
              <p>每个回答都能回到原始通知或主页。</p>
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
          <div className="statusPill">{serviceReady ? "智能服务已连接" : "演示模式"}</div>
        </div>

        {page === "profile" && <ProfilePage profile={profile} />}
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
        {page === "planning" && (
          <PlanningPage
            profile={profile}
            plan={plan}
            schools={schools}
            timeline={timeline}
            onGenerate={generatePlan}
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
        {page === "workflows" && <WorkflowPage workflows={workflows} onRefresh={refreshWorkflows} />}
      </main>
    </div>
  );
}

export default App;
