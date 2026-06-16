import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { sampleAdvisors, sampleDocuments, sampleProfile, sampleWorkflow } from "./api/mockData";
import { KnowledgePage } from "./pages/KnowledgePage";
import { MaterialsPage } from "./pages/MaterialsPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ProfilePage } from "./pages/ProfilePage";
import { WorkflowPage } from "./pages/WorkflowPage";
import type { Advisor, DocumentItem, StudentProfile, WorkflowRun } from "./types/domain";

type PageKey = "profile" | "knowledge" | "planning" | "materials" | "workflows";

const navItems: { key: PageKey; label: string }[] = [
  { key: "profile", label: "用户画像" },
  { key: "knowledge", label: "知识库与导师" },
  { key: "planning", label: "申请规划" },
  { key: "materials", label: "材料与面试" },
  { key: "workflows", label: "Workflow" }
];

function App() {
  const [page, setPage] = useState<PageKey>("profile");
  const [profile, setProfile] = useState<StudentProfile>(sampleProfile);
  const [documents, setDocuments] = useState<DocumentItem[]>(sampleDocuments);
  const [advisors, setAdvisors] = useState<Advisor[]>(sampleAdvisors);
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([sampleWorkflow]);
  const [plan, setPlan] = useState("Click generate to run ProfileAgent, SchoolRecommendAgent, and PlannerAgent.");
  const [schools, setSchools] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<string[]>([]);
  const [answer, setAnswer] = useState("Click RAG query to ask the knowledge base.");
  const [email, setEmail] = useState("Click generate email to create an advisor contact draft.");
  const [interview, setInterview] = useState("Click generate interview to create mock questions.");

  useEffect(() => {
    Promise.all([api.getProfile(), api.getDocuments(), api.getAdvisors(), api.getWorkflows()]).then(
      ([nextProfile, nextDocuments, nextAdvisors, nextWorkflows]) => {
        setProfile(nextProfile);
        setDocuments(nextDocuments);
        setAdvisors(nextAdvisors);
        setWorkflows(nextWorkflows);
      }
    );
  }, []);

  const currentTitle = useMemo(
    () => navItems.find((item) => item.key === page)?.label ?? "Baoyan Agent",
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
    setWorkflows((items) => [result.workflow, ...items.filter((item) => item.id !== result.workflow.id)]);
  }

  async function askKnowledge() {
    const result = await api.askKnowledge("What materials are required for CS summer camp?");
    setAnswer(result.answer);
    setWorkflows((items) => [result.workflow, ...items.filter((item) => item.id !== result.workflow.id)]);
  }

  async function matchAdvisors() {
    const result = await api.matchAdvisors(profile);
    setAdvisors(result.advisors);
    setAnswer(result.workflow.final_result);
    setWorkflows((items) => [result.workflow, ...items.filter((item) => item.id !== result.workflow.id)]);
  }

  async function generateEmail() {
    const result = await api.generateEmail(profile, advisors[0]);
    setEmail(result.content);
    setWorkflows((items) => [result.workflow, ...items.filter((item) => item.id !== result.workflow.id)]);
  }

  async function generateInterview() {
    const result = await api.generateInterview(profile);
    setInterview(result.content);
    setWorkflows((items) => [result.workflow, ...items.filter((item) => item.id !== result.workflow.id)]);
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <span>BA</span>
          <div>
            <strong>Baoyan Agent</strong>
            <small>CS application middleware</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              className={page === item.key ? "active" : ""}
              key={item.key}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Multi-Agent Middleware System</p>
            <h1>{currentTitle}</h1>
          </div>
          <div className="statusPill">Mock LLM Ready</div>
        </header>

        {page === "profile" && <ProfilePage profile={profile} />}
        {page === "knowledge" && (
          <KnowledgePage
            documents={documents}
            advisors={advisors}
            answer={answer}
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
