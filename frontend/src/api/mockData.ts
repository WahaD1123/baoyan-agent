import type { Advisor, DocumentItem, StudentProfile, WorkflowRun } from "../types/domain";

export const sampleProfile: StudentProfile = {
  id: "profile_demo",
  name: "示例同学",
  university: "厦门大学",
  major: "计算机科学与技术",
  rank_percent: 8,
  research_interests: ["机器学习", "智能系统"],
  projects: ["多智能体保研助手", "课程推荐系统"],
  competitions: ["蓝桥杯省级奖项"],
  publications: [],
  target_regions: ["上海", "北京"],
  preferred_schools: ["上海交通大学", "浙江大学"],
  notes: "希望申请人工智能系统与检索问答方向。",
  updated_at: new Date().toISOString()
};

export const sampleDocuments: DocumentItem[] = [
  {
    id: "doc_notice",
    title: "上海交通大学计算机夏令营通知",
    doc_type: "notice",
    source_type: "sample",
    content: "需要准备个人简历、成绩单、排名证明、科研陈述，可能包含机考或专业面试。",
    source: "sample",
    keywords: ["上海交通大学", "个人简历", "机考"],
    chunks: [],
    extracted: { materials: ["个人简历", "成绩单", "排名证明"], exam_format: ["机考", "专业面试"] },
    created_at: new Date().toISOString()
  },
  {
    id: "doc_advisor",
    title: "王老师主页摘要",
    doc_type: "advisor",
    source_type: "sample",
    content: "研究方向包括机器学习系统、大模型应用和可信人工智能。",
    source: "sample",
    keywords: ["大模型应用", "智能系统", "机器学习"],
    chunks: [],
    extracted: { name: "王老师", research_areas: ["大模型应用", "机器学习系统"] },
    created_at: new Date().toISOString()
  }
];

export const sampleAdvisors: Advisor[] = [
  {
    id: "advisor_wang",
    name: "王老师",
    university: "上海交通大学",
    department: "计算机科学与工程系",
    research_areas: ["机器学习", "智能系统", "大模型应用"],
    homepage: "https://example.edu/wang",
    summary: "关注智能系统和应用机器学习，适合有工程项目经验的学生。",
    representative_works: ["面向可信应用的智能系统研究"],
    suitable_background: "有机器学习项目、系统开发或科研训练经历的学生。",
    source_document_id: "doc_advisor"
  },
  {
    id: "advisor_chen",
    name: "陈老师",
    university: "浙江大学",
    department: "计算机科学与技术学院",
    research_areas: ["数据库", "信息检索", "检索增强问答"],
    homepage: "https://example.edu/chen",
    summary: "关注检索系统与数据管理，适合对搜索、问答和数据库感兴趣的学生。",
    representative_works: ["面向问答场景的数据管理研究"],
    suitable_background: "适合有数据库、搜索系统或问答项目经历的学生。",
    source_document_id: ""
  }
];

export const sampleWorkflow: WorkflowRun = {
  id: "workflow_demo",
  workflow_type: "申请规划",
  status: "completed",
  created_at: new Date().toISOString(),
  final_result: "已生成院校梯度、材料准备节奏和导师联系建议。",
  steps: [
    {
      name: "分析学生画像",
      status: "completed",
      agent_result: {
        id: "agent_profile",
        agent_name: "画像分析",
        input_summary: "专业排名前 8%，方向为机器学习和智能系统。",
        output: "背景适合申请人工智能系统相关项目。",
        references: [],
        created_at: new Date().toISOString()
      }
    },
    {
      name: "生成申请节奏",
      status: "completed",
      agent_result: {
        id: "agent_planner",
        agent_name: "申请规划",
        input_summary: "结合推荐院校与截止时间。",
        output: "先准备材料，再联系导师，最后进行面试练习。",
        references: ["上海交通大学计算机夏令营通知"],
        created_at: new Date().toISOString()
      }
    }
  ]
};
