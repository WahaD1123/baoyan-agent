from app.agents import (
    AdvisorMatchAgent,
    CriticAgent,
    InterviewAgent,
    KnowledgeAgent,
    MaterialAgent,
    PlannerAgent,
    ProfileAgent,
    SchoolRecommendAgent,
)
from app.models import Advisor, AdvisorMatchResult, Document, RetrievedChunk, StudentProfile, WorkflowRun, WorkflowStep
from app.services.llm import get_llm_provider
from app.services.planning_service import (
    analyze_profile,
    build_timeline,
    format_plan_summary,
    recommend_schools,
    retrieve_planning_evidence,
)
from app.services.store import store


def _workflow(workflow_type: str, steps: list[WorkflowStep], final_result: str) -> WorkflowRun:
    return WorkflowRun(workflow_type=workflow_type, steps=steps, final_result=final_result)


def run_planning_workflow(profile: StudentProfile) -> WorkflowRun:
    analysis = analyze_profile(profile)
    evidence_chunks = retrieve_planning_evidence(profile, store.documents)
    recommendations = recommend_schools(profile, analysis, store.documents, evidence_chunks)
    timeline = build_timeline(profile, recommendations)
    evidence_titles = list(dict.fromkeys(chunk.document_title for chunk in evidence_chunks))
    profile_text = (
        f"{profile.name}, rank top {profile.rank_percent}%, GPA {profile.gpa}, "
        f"interests: {', '.join(profile.research_interests)}"
    )
    profile_result = ProfileAgent().run(profile_text)
    school_prompt = (
        f"{profile_result.output}\n"
        f"Structured analysis: overall={analysis.overall_score}, "
        f"strengths={'; '.join(analysis.strengths)}, weaknesses={'; '.join(analysis.weaknesses)}\n"
        f"Retrieved evidence titles: {', '.join(evidence_titles) or 'none'}"
    )
    school_result = SchoolRecommendAgent().run(school_prompt)
    planner_prompt = format_plan_summary(profile, analysis, recommendations, timeline, evidence_titles)
    planner_result = PlannerAgent().run(planner_prompt)
    planner_result.output = planner_prompt
    return _workflow(
        "planning",
        [
            WorkflowStep(name="Analyze student profile", agent_result=profile_result),
            WorkflowStep(name="Recommend sprint/stable/safe schools", agent_result=school_result),
            WorkflowStep(name="Generate application timeline", agent_result=planner_result),
        ],
        planner_result.output,
    )


def run_knowledge_workflow(question: str, documents: list[Document], chunks: list[RetrievedChunk] | None = None) -> WorkflowRun:
    refs = [doc.title for doc in documents]
    analyses = "\n\n".join(
        (
            f"Document: {doc.title}\n"
            f"Type: {doc.doc_type}\n"
            f"Full analysis summary: {doc.analysis.get('summary', '')}\n"
            f"Structured fields: {doc.analysis.get('structured_fields', doc.extracted)}\n"
            f"Important dates: {doc.analysis.get('important_dates', [])}\n"
            f"Requirements: {doc.analysis.get('requirements', [])}\n"
            f"Risks: {doc.analysis.get('risks', [])}"
        )
        for doc in documents
    )
    evidence = "\n\n".join(
        f"[{idx + 1}] {chunk.document_title} score={chunk.score}\n{chunk.text}"
        for idx, chunk in enumerate(chunks or [])
    )
    prompt = (
        f"Question: {question}\n"
        f"Full document analyses from ingestion:\n{analyses or 'none'}\n\n"
        f"Original citation chunks:\n{evidence or ', '.join(refs)}\n"
        "Answer in Chinese. If relevant documents are provided, prefer the structured full-document analysis and support it with original citation chunks. "
        "If no relevant document is provided, clearly say the knowledge base has no matching evidence, then answer from general reasoning without citing unrelated sources."
    )
    result = KnowledgeAgent().run(prompt, refs)
    critic = CriticAgent().run(
        f"Check whether this RAG answer is grounded and cites sources.\nQuestion: {question}\nAnswer:\n{result.output}",
        refs,
    )
    return _workflow(
        "knowledge",
        [
            WorkflowStep(name="Route question over full library catalog and read selected evidence", agent_result=result),
            WorkflowStep(name="Grounding critic review", agent_result=critic),
        ],
        f"{result.output}\n\n引用来源: {', '.join(refs) if refs else '资料库未命中，以上为通用建议'}",
    )


def score_advisors(profile: StudentProfile, advisors: list[Advisor], top_k: int = 3) -> list[AdvisorMatchResult]:
    interests = {item.lower() for item in profile.research_interests}
    project_text = " ".join(profile.projects + profile.publications + profile.competitions + [profile.notes]).lower()
    preferred = {item.lower() for item in profile.preferred_schools + profile.target_regions}
    results: list[AdvisorMatchResult] = []
    for advisor in advisors:
        area_hits = [area for area in advisor.research_areas if area.lower() in interests or area.lower() in project_text]
        keyword_hits = [
            interest for interest in interests
            if interest in " ".join(advisor.research_areas + [advisor.summary, advisor.suitable_background]).lower()
        ]
        school_hit = any(item in f"{advisor.university} {advisor.department}".lower() for item in preferred)
        score = min(100.0, 35 + len(area_hits) * 18 + len(keyword_hits) * 12 + (15 if school_hit else 0))
        reasons = []
        if area_hits:
            reasons.append(f"研究方向直接命中: {', '.join(area_hits)}")
        if keyword_hits:
            reasons.append(f"用户兴趣与导师简介相关: {', '.join(keyword_hits)}")
        if school_hit:
            reasons.append("学校或地区偏好匹配")
        if not reasons:
            reasons.append("基础方向相关，但需要进一步核对主页和论文")
        risks = []
        if score < 60:
            risks.append("匹配证据偏少，建议补充项目经历或查看更多导师资料")
        if not advisor.homepage:
            risks.append("缺少导师主页链接，来源可信度需要人工确认")
        results.append(
            AdvisorMatchResult(
                advisor=advisor,
                score=round(score, 1),
                reasons=reasons,
                risks=risks,
                contact_suggestion=f"邮件中突出 {', '.join(profile.research_interests[:2]) or '研究兴趣'} 与导师方向的连接，并附上项目摘要。",
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def run_advisor_match_workflow(
    profile: StudentProfile,
    advisors: list[Advisor],
    matches: list[AdvisorMatchResult] | None = None,
) -> WorkflowRun:
    refs = [f"{advisor.name} - {advisor.university}" for advisor in advisors]
    match_lines = "\n".join(
        f"{item.advisor.name}: {item.score}, reasons={'; '.join(item.reasons)}"
        for item in (matches or [])
    )
    result = AdvisorMatchAgent().run(
        f"Profile interests: {', '.join(profile.research_interests)}. Candidate advisors: {', '.join(refs)}\nScores:\n{match_lines}",
        refs,
    )
    critic = CriticAgent().run(
        f"Check whether advisor matching reasons are grounded.\nProfile: {profile.model_dump()}\nMatches:\n{match_lines}",
        refs,
    )
    return _workflow(
        "advisor_match",
        [
            WorkflowStep(name="Score advisors by profile fit", agent_result=result),
            WorkflowStep(name="Critic review match reasons", agent_result=critic),
        ],
        result.output,
    )


def run_ingest_workflow(document: Document, source_label: str) -> WorkflowRun:
    summary = get_llm_provider().generate(
        (
            f"资料标题: {document.title}\n"
            f"类型: {document.doc_type}\n"
            f"结构化字段: {document.extracted}\n"
            f"全文分析结果: {document.analysis}\n"
            f"正文材料:\n{document.content[:2500]}"
        ),
        task="extract",
    )
    result = KnowledgeAgent().run(
        f"Ingest {source_label}: {document.title}. Extracted keys: {', '.join(document.extracted.keys())}",
        [document.title],
    )
    result.output = summary
    return _workflow(
        "knowledge_ingest",
        [
            WorkflowStep(name=f"Parse and analyze full {source_label}", agent_result=result),
        ],
        f"已入库并完成全文分析: {document.title} ({len(document.chunks)} chunks)",
    )


def _profile_brief(profile: StudentProfile) -> str:
    return (
        f"姓名: {profile.name}\n"
        f"学校专业: {profile.university} / {profile.major}\n"
        f"排名: Top {profile.rank_percent}%\n"
        f"研究兴趣: {', '.join(profile.research_interests) or '未填写'}\n"
        f"项目经历: {', '.join(profile.projects) or '未填写'}\n"
        f"竞赛经历: {', '.join(profile.competitions) or '未填写'}\n"
        f"论文经历: {', '.join(profile.publications) or '未填写'}\n"
        f"补充说明: {profile.notes or '无'}"
    )


def _run_material_generation(
    workflow_type: str,
    title: str,
    prompt: str,
    references: list[str] | None = None,
) -> WorkflowRun:
    refs = references or []
    draft = MaterialAgent().run(prompt, refs)
    review = CriticAgent().run(
        (
            f"请审查以下保研申请材料是否具体、克制、有证据，指出空话和改写建议。\n"
            "仅输出总体评价、最多 3 条证据风险和最多 3 条改写建议。"
            "不要使用 Markdown 表格，总字数控制在 400 字以内。\n"
            f"材料类型: {title}\n"
            f"材料内容:\n{draft.output}"
        ),
        [*refs, draft.id],
    )
    return _workflow(
        workflow_type,
        [
            WorkflowStep(name=f"Generate {title}", agent_result=draft),
            WorkflowStep(name=f"Critic review {title}", agent_result=review),
        ],
        f"## {title}\n{draft.output}\n\n## 质量检查\n{review.output}",
    )


def run_material_email_workflow(profile: StudentProfile, advisor: Advisor | None, purpose: str) -> WorkflowRun:
    advisor_text = (
        f"{advisor.name}，{advisor.university}{advisor.department}，方向: {', '.join(advisor.research_areas)}"
        if advisor
        else "目标导师，方向待补充"
    )
    prompt = (
        "material_kind=advisor_email\n"
        "请生成一封中文导师联系邮件，语气礼貌克制，包含称呼、自我介绍、研究匹配、附件说明和结尾。\n"
        "正文控制在 600 字以内。只使用学生画像和导师信息中已有事实，缺失联系方式使用占位符，不得编造。\n"
        f"申请目的: {purpose}\n"
        f"学生画像:\n{_profile_brief(profile)}\n"
        f"导师信息: {advisor_text}"
    )
    refs = [f"{advisor.name} - {advisor.university}"] if advisor else []
    return _run_material_generation("material_email", "导师联系邮件", prompt, refs)


def run_resume_highlights_workflow(profile: StudentProfile, target_direction: str) -> WorkflowRun:
    prompt = (
        "material_kind=resume_highlights\n"
        "请把学生经历改写成 4 条中文保研简历亮点。每条使用 动作-方法-结果-匹配方向 的结构，每条不超过 100 字。"
        "只使用画像中的事实；没有量化结果时明确写待补充，不得编造指标、技术栈或奖项等级。\n"
        f"目标方向: {target_direction}\n"
        f"学生画像:\n{_profile_brief(profile)}"
    )
    return _run_material_generation("resume_highlights", "简历亮点", prompt, profile.projects)


def run_statement_workflow(profile: StudentProfile, target_school: str, direction: str, tone: str) -> WorkflowRun:
    prompt = (
        "material_kind=personal_statement\n"
        "请生成一段中文个人陈述片段，包含研究兴趣来源、项目经历支撑、目标方向匹配和后续计划。\n"
        "正文控制在 700 字以内，只使用学生画像中的事实，不得编造课程成绩、实验指标、论文或工具经验。\n"
        f"目标学校: {target_school}\n"
        f"申请方向: {direction}\n"
        f"语气要求: {tone}\n"
        f"学生画像:\n{_profile_brief(profile)}"
    )
    return _run_material_generation("personal_statement", "个人陈述", prompt, [target_school, direction])


def run_material_workflow(profile: StudentProfile, advisor: Advisor | None, purpose: str) -> WorkflowRun:
    return run_material_email_workflow(profile, advisor, purpose)


def run_interview_workflow(profile: StudentProfile, target_school: str, direction: str) -> WorkflowRun:
    interview = InterviewAgent().run(
        (
            "interview_kind=categorized_mock\n"
            "请生成中文 CS 保研模拟面试题，按项目追问、专业基础、科研方向、英文面试、复盘建议分类。"
            "项目追问最多 4 题、专业基础最多 4 题、科研方向最多 3 题、英文面试最多 2 题、复盘建议最多 2 条，"
            "总题量控制在 15 题以内。不要输出面试官自我介绍、提示语或 Markdown 表格。\n"
            f"目标学校: {target_school}\n"
            f"申请方向: {direction}\n"
            f"学生画像:\n{_profile_brief(profile)}"
        )
    )
    review = CriticAgent().run(
        (
            "请审查以下模拟面试题是否覆盖项目、基础、科研和英文表达，并指出还缺少哪些追问。\n"
            "仅输出总体评价、最多 3 条缺失点和最多 3 条改进建议。"
            "不要使用 Markdown 表格，总字数控制在 400 字以内。\n"
            f"面试题内容:\n{interview.output}"
        ),
        [interview.id, target_school, direction],
    )
    return _workflow(
        "interview",
        [
            WorkflowStep(name="Generate categorized mock interview", agent_result=interview),
            WorkflowStep(name="Critic review interview", agent_result=review),
        ],
        f"## 模拟面试题\n{interview.output}\n\n## 质量检查\n{review.output}",
    )
