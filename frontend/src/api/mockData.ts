import type { Advisor, DocumentItem, StudentProfile, WorkflowRun } from "../types/domain";

export const sampleProfile: StudentProfile = {
  id: "profile_demo",
  name: "Demo Student",
  university: "Xiamen University",
  major: "Computer Science",
  rank_percent: 8,
  research_interests: ["machine learning", "agent systems"],
  projects: ["Multi-agent baoyan assistant", "Course recommendation system"],
  competitions: ["Lanqiao Cup provincial prize"],
  publications: [],
  target_regions: ["Shanghai", "Beijing"],
  preferred_schools: ["Shanghai Jiao Tong University", "Zhejiang University"],
  notes: "Interested in AI systems and RAG applications.",
  updated_at: new Date().toISOString()
};

export const sampleDocuments: DocumentItem[] = [
  {
    id: "doc_notice",
    title: "SJTU CS Summer Camp Notice",
    doc_type: "notice",
    content: "Requires resume, transcript, ranking certificate, research statement, and possible coding test.",
    source: "sample",
    keywords: ["SJTU", "resume", "coding test"],
    created_at: new Date().toISOString()
  },
  {
    id: "doc_advisor",
    title: "Advisor Wang homepage note",
    doc_type: "advisor",
    content: "Research areas include machine learning systems, LLM agents, and trustworthy AI applications.",
    source: "sample",
    keywords: ["LLM", "agent", "machine learning"],
    created_at: new Date().toISOString()
  }
];

export const sampleAdvisors: Advisor[] = [
  {
    id: "advisor_wang",
    name: "Prof. Wang",
    university: "Shanghai Jiao Tong University",
    department: "Computer Science",
    research_areas: ["machine learning", "LLM agents", "AI systems"],
    homepage: "https://example.edu/wang",
    summary: "Works on agent systems and applied machine learning."
  },
  {
    id: "advisor_chen",
    name: "Prof. Chen",
    university: "Zhejiang University",
    department: "Computer Science",
    research_areas: ["database", "information retrieval", "RAG"],
    homepage: "https://example.edu/chen",
    summary: "Works on retrieval systems and data management."
  }
];

export const sampleWorkflow: WorkflowRun = {
  id: "workflow_demo",
  workflow_type: "planning",
  status: "completed",
  created_at: new Date().toISOString(),
  final_result: "Generated sprint/stable/safe school strategy and application timeline.",
  steps: [
    {
      name: "Analyze student profile",
      status: "completed",
      agent_result: {
        id: "agent_profile",
        agent_name: "ProfileAgent",
        input_summary: "Rank top 8%, interests in ML and agent systems.",
        output: "Strong profile for AI systems programs.",
        references: [],
        created_at: new Date().toISOString()
      }
    },
    {
      name: "Generate application timeline",
      status: "completed",
      agent_result: {
        id: "agent_planner",
        agent_name: "PlannerAgent",
        input_summary: "Recommended schools and deadlines.",
        output: "Prepare materials, contact advisors, then practice interviews.",
        references: ["SJTU CS Summer Camp Notice"],
        created_at: new Date().toISOString()
      }
    }
  ]
};
