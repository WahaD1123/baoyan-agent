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
    evidence = "\n\n".join(
        f"[{idx + 1}] {chunk.document_title} score={chunk.score}\n{chunk.text}"
        for idx, chunk in enumerate(chunks or [])
    )
    prompt = (
        f"Question: {question}\n"
        f"Retrieved evidence:\n{evidence or ', '.join(refs)}\n"
        "Answer in Chinese. Cite source titles explicitly. If evidence is insufficient, say what is missing."
    )
    result = KnowledgeAgent().run(prompt, refs)
    critic = CriticAgent().run(
        f"Check whether this RAG answer is grounded and cites sources.\nQuestion: {question}\nAnswer:\n{result.output}",
        refs,
    )
    return _workflow(
        "knowledge",
        [
            WorkflowStep(name="Hybrid retrieve document chunks", agent_result=result),
            WorkflowStep(name="Grounding critic review", agent_result=critic),
        ],
        f"{result.output}\n\n引用来源: {', '.join(refs) if refs else '无'}",
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
        f"资料标题: {document.title}\n类型: {document.doc_type}\n结构化字段: {document.extracted}\n正文摘要材料:\n{document.content[:2500]}",
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
            WorkflowStep(name=f"Parse {source_label}", agent_result=result),
        ],
        f"已入库: {document.title} ({len(document.chunks)} chunks)",
    )


def run_material_workflow(profile: StudentProfile, advisor: Advisor | None, purpose: str) -> WorkflowRun:
    advisor_text = f"{advisor.name} at {advisor.university}" if advisor else "target advisor"
    draft = MaterialAgent().run(
        f"Generate contact email for {profile.name} to {advisor_text}. Purpose: {purpose}"
    )
    review = CriticAgent().run(draft.output, [draft.id])
    return _workflow(
        "material",
        [
            WorkflowStep(name="Generate application material", agent_result=draft),
            WorkflowStep(name="Critic review", agent_result=review),
        ],
        f"{draft.output}\n\nQuality check:\n{review.output}",
    )


def run_interview_workflow(profile: StudentProfile, target_school: str, direction: str) -> WorkflowRun:
    interview = InterviewAgent().run(
        f"Generate mock interview questions for {profile.name}, target: {target_school}, direction: {direction}"
    )
    review = CriticAgent().run(interview.output, [interview.id])
    return _workflow(
        "interview",
        [
            WorkflowStep(name="Generate mock interview", agent_result=interview),
            WorkflowStep(name="Critic review", agent_result=review),
        ],
        f"{interview.output}\n\nQuality check:\n{review.output}",
    )
