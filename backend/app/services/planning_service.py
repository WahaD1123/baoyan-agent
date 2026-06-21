from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Iterable

from app.models import Document, EvidenceReference, ProfileAnalysis, RetrievedChunk, SchoolRecommendation, StudentProfile
from app.services.llm import get_llm_provider
from app.tools.retrieval import hybrid_retrieve

logger = logging.getLogger("baoyan-agent.planning")

SCHOOL_DISPLAY_MAP = {
    "tsinghua university": "清华大学",
    "peking university": "北京大学",
    "beijing university": "北京大学",
    "shanghai jiao tong university": "上海交通大学",
    "fudan university": "复旦大学",
    "zhejiang university": "浙江大学",
    "nanjing university": "南京大学",
    "university of science and technology of china": "中国科学技术大学",
    "beihang university": "北京航空航天大学",
    "harbin institute of technology": "哈尔滨工业大学",
    "southeast university": "东南大学",
    "sun yat-sen university": "中山大学",
    "xiamen university": "厦门大学",
}


@dataclass(frozen=True)
class SchoolCatalogItem:
    school_name: str
    aliases: tuple[str, ...]
    region: str
    directions: tuple[str, ...]
    base_difficulty: int
    program_name: str
    source: str = "catalog"


@dataclass(frozen=True)
class NoticeContext:
    evidence: tuple[tuple[str, str], ...]
    materials: tuple[str, ...]
    exam_format: tuple[str, ...]
    deadline: str
    website: str


SCHOOL_TIERS_RAW: dict[str, str] = {
    "T0": "清华大学、北京大学",
    "T1": "复旦大学、上海交通大学、浙江大学、中国科学技术大学、南京大学、中国人民大学、中国科学院大学、北京航空航天大学、同济大学、哈尔滨工业大学、西安交通大学、北京理工大学",
    "T2": "武汉大学、华中科技大学、南开大学、天津大学、东南大学、中山大学、厦门大学、北京师范大学、华东师范大学、电子科技大学、华南理工大学、四川大学、中南大学、大连理工大学、西北工业大学、中央财经大学、上海财经大学、对外经济贸易大学、北京邮电大学、中国政法大学、外交学院、西安电子科技大学、上海科技大学、南方科技大学",
    "T3": "山东大学、重庆大学、湖南大学、吉林大学、东北大学、中国农业大学、兰州大学、北京交通大学、北京科技大学、华东理工大学、南京航空航天大学、南京理工大学、哈尔滨工程大学、北京外国语大学、上海外国语大学、中南财经政法大学、西南财经大学、华北电力大学、苏州大学、暨南大学、中国传媒大学、南京医科大学、天津医科大学、中国药科大学、中国海洋大学、中央民族大学",
    "T4": "北京工业大学、北京化工大学、北京林业大学、首都师范大学、天津工业大学、河北工业大学、太原理工大学、辽宁大学、大连海事大学、东北师范大学、东华大学、上海大学、南京邮电大学、河海大学、江南大学、南京林业大学、南京信息工程大学、南京师范大学、安徽大学、合肥工业大学、福州大学、南昌大学、中国矿业大学、 中国石油大学（华东）、郑州大学、中国地质大学（武汉）、武汉理工大学、华中师范大学、西南交通大学、西南大学、云南大学、西北大学、陕西师范大学、中国矿业大学（北京）、中国石油大学（北京）、中国地质大学（北京）、宁波大学、广州医科大学",
    "T5": "北京中医药大学、天津中医药大学、山西大学、内蒙古大学、延边大学、东北农业大学、东北林业大学、上海海洋大学、上海中医药大学、南京农业大学、南京中医药大学、河南大学、华中农业大学、湘潭大学、湖南师范大学、华南农业大学、广州中医药大学、华南师范大学、海南大学、广西大学、西南石油大学、成都理工大学、四川农业大学、成都中医药大学、贵州大学、西藏大学、长安大学、西北农林科技大学、青海大学、宁夏大学、新疆大学、石河子大学",
}

SPECIAL_SCHOOLS = {
    "北京协和医学院",
    "中国人民公安大学",
    "北京体育大学",
    "中央音乐学院",
    "中国音乐学院",
    "中央美术学院",
    "中央戏剧学院",
    "上海体育学院",
    "上海音乐学院",
    "中国美术学院",
    "国防科技大学",
    "海军军医大学",
    "空军军医大学",
}

TIER_BASE_DIFFICULTY = {
    "T0": 99,
    "T1": 94,
    "T2": 88,
    "T3": 82,
    "T4": 75,
    "T5": 68,
}

SCHOOL_TIER_MAP = {
    school.strip(): tier
    for tier, schools in SCHOOL_TIERS_RAW.items()
    for school in schools.replace(" ", "").split("、")
    if school.strip()
}

ENGLISH_TIER_MAP = {
    "tsinghua university": "T0",
    "peking university": "T0",
    "fudan university": "T1",
    "shanghai jiao tong university": "T1",
    "zhejiang university": "T1",
    "university of science and technology of china": "T1",
    "nanjing university": "T1",
    "beihang university": "T1",
    "harbin institute of technology": "T1",
    "xiamen university": "T2",
    "southeast university": "T2",
    "sun yat-sen university": "T2",
}


BASE_CATALOG: tuple[SchoolCatalogItem, ...] = (
    SchoolCatalogItem("Tsinghua University", ("tsinghua", "清华", "清华大学"), "beijing", ("ai", "systems", "theory"), 98, "CS Summer Camp"),
    SchoolCatalogItem("Peking University", ("pku", "peking university", "北大", "北京大学"), "beijing", ("ai", "theory", "nlp"), 97, "Information Science Program"),
    SchoolCatalogItem("Shanghai Jiao Tong University", ("sjtu", "shanghai jiao tong university", "上交", "上海交通大学"), "shanghai", ("ai", "machine learning", "systems", "agent", "retrieval"), 93, "CS Summer Camp"),
    SchoolCatalogItem("Fudan University", ("fudan", "复旦", "复旦大学"), "shanghai", ("ai", "nlp", "data"), 90, "Computer Science Program"),
    SchoolCatalogItem("Zhejiang University", ("zju", "浙江大学", "浙大"), "hangzhou", ("ai", "machine learning", "retrieval", "systems"), 88, "Computer Science Program"),
    SchoolCatalogItem("Nanjing University", ("nju", "南京大学", "南大"), "nanjing", ("ai", "software engineering", "systems"), 87, "Computer Science Program"),
    SchoolCatalogItem("University of Science and Technology of China", ("ustc", "中国科学技术大学", "中科大"), "hefei", ("ai", "systems", "theory"), 89, "CS Excellence Track"),
    SchoolCatalogItem("Beihang University", ("buaa", "北航", "北京航空航天大学"), "beijing", ("ai", "systems", "robotics"), 83, "Computer Science Program"),
    SchoolCatalogItem("Harbin Institute of Technology", ("hit", "哈工大", "哈尔滨工业大学"), "harbin", ("ai", "nlp", "robotics", "systems"), 84, "CS Summer Camp"),
    SchoolCatalogItem("Southeast University", ("seu", "东南大学"), "nanjing", ("ai", "software engineering", "computer vision"), 82, "CS Summer Program"),
    SchoolCatalogItem("Sun Yat-sen University", ("sysu", "中山大学", "中大"), "guangzhou", ("ai", "data", "systems"), 78, "Computer Science Program"),
    SchoolCatalogItem("Xiamen University", ("xmu", "厦门大学", "厦大"), "xiamen", ("ai", "systems", "software engineering"), 75, "AI Lab Track"),
)


def analyze_profile(profile: StudentProfile) -> ProfileAnalysis:
    academic_score = _score_academic(profile)
    research_score = _score_research(profile)
    project_score = _score_projects(profile)
    competition_score = _score_competitions(profile)
    language_score = _score_language(profile)

    weighted = (
        academic_score * 0.35
        + research_score * 0.25
        + project_score * 0.15
        + competition_score * 0.10
        + language_score * 0.15
    )
    overall_score = max(55, min(96, round(weighted)))

    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    if profile.rank_percent <= 10:
        strengths.append("专业排名具有竞争力，适合保留强校冲刺机会。")
    elif profile.rank_percent <= 20:
        strengths.append("专业排名处于中上区间，更适合围绕稳妥院校精细准备。")
    else:
        weaknesses.append("专业排名不是显著优势，推荐时要更强调项目和方向匹配。")

    if profile.publications:
        strengths.append("已有论文或投稿经历，可以增强科研潜力证明。")
    else:
        weaknesses.append("科研成果展示偏弱，强校筛选时容易处于劣势。")

    if len(profile.projects) >= 2:
        strengths.append("项目经历相对完整，适合提炼成简历亮点和面试主线。")
    else:
        weaknesses.append("项目数量偏少，建议补足一到两个可量化成果项目。")

    if "6" in profile.english_score.lower() or "ielts" in profile.english_score.lower() or "toefl" in profile.english_score.lower():
        strengths.append("英语成绩可以支撑大部分保研材料和英文面试场景。")
    else:
        suggestions.append("尽快补充英语成绩或英文表达能力证明，避免筛选阶段失分。")

    if not profile.preferred_schools:
        suggestions.append("先明确 3 到 5 所重点关注学校，便于系统生成更聚焦的院校规划。")

    suggestions.extend(
        [
            "把最能体现技术深度的项目整理成 STAR 结构，用于简历和面试表达。",
            "优先准备成绩单、排名证明、简历和项目摘要，形成统一材料包。",
        ]
    )

    heuristic = ProfileAnalysis(
        overall_score=overall_score,
        academic_score=academic_score,
        research_score=research_score,
        project_score=project_score,
        competition_score=competition_score,
        language_score=language_score,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=_unique_keep_order(suggestions),
        summary=(
            f"{profile.name} 当前更适合采用“冲刺 + 稳妥 + 保底”的组合申请策略。"
            "系统会结合你的背景、院校偏好和已导入通知，生成更有依据的规划结果。"
        ),
    )
    return _enrich_profile_analysis(profile, heuristic)


def retrieve_planning_evidence(profile: StudentProfile, documents: list[Document], top_k: int = 6) -> list[RetrievedChunk]:
    query_parts = [
        profile.major,
        *profile.research_interests[:4],
        *profile.preferred_schools[:4],
        *profile.target_regions[:3],
        "summer camp notice materials interview coding test advisor",
    ]
    query = " ".join(part for part in query_parts if part)
    docs = [doc for doc in documents if doc.doc_type in {"notice", "experience", "advisor"}]
    return hybrid_retrieve(docs, query, top_k)


def recommend_schools(
    profile: StudentProfile,
    analysis: ProfileAnalysis,
    documents: list[Document] | None = None,
    evidence_chunks: list[RetrievedChunk] | None = None,
) -> list[SchoolRecommendation]:
    docs = documents or []
    chunks = evidence_chunks or []
    candidates = _build_candidate_pool(profile, docs, chunks)
    scored = [_score_candidate(item, profile, analysis, docs, chunks) for item in candidates]

    picked: list[dict[str, Any]] = []
    for level in ("challenge", "stable", "safe"):
        chosen = _pick_for_level(scored, picked, level, analysis.overall_score)
        if chosen is not None:
            picked.append(chosen)

    picked = _ensure_preferred_school_presence(scored, picked, analysis.overall_score)
    picked = _backfill_missing_levels(scored, picked, analysis.overall_score)
    picked = sorted(picked, key=lambda item: ("challenge", "stable", "safe").index(item["level"]))

    recommendations = [_to_recommendation(item) for item in picked]
    return enrich_recommendations_with_agent(profile, analysis, recommendations)


def enrich_recommendations_with_agent(
    profile: StudentProfile,
    analysis: ProfileAnalysis,
    recommendations: list[SchoolRecommendation],
) -> list[SchoolRecommendation]:
    llm = get_llm_provider()
    enriched: list[SchoolRecommendation] = []
    for item in recommendations:
        evidence_titles = [entry.title for entry in item.evidence]
        prompt = (
            f"学生画像：排名前 {profile.rank_percent}%，GPA {profile.gpa}，方向 {', '.join(profile.research_interests)}。\n"
            f"学校：{item.school_name}，层级：{item.level}，匹配度：{item.match_score}。\n"
            f"规则层推荐理由：{'；'.join(item.reasons) or '暂无'}。\n"
            f"规则层风险提示：{'；'.join(item.risks) or '暂无'}。\n"
            f"规则层待办：{'；'.join(item.todo) or '暂无'}。\n"
            f"材料要求：{'；'.join(item.materials) or '暂无'}。\n"
            f"考核形式：{'；'.join(item.exam_format) or '暂无'}。\n"
            f"截止时间：{item.deadline or '暂无'}。\n"
            f"依据资料：{'；'.join(evidence_titles) or '暂无'}。\n"
            "请严格基于以上信息输出 JSON，对应字段为 reasons, risks, todo, insight。\n"
            "要求：\n"
            "1. 每个字段都必须用中文。\n"
            "2. reasons/risk/todo 都输出 2 到 3 条短句数组。\n"
            "3. insight 输出 1 到 2 句自然语言建议。\n"
            "4. 不要编造不存在的通知、导师或材料要求。\n"
            "5. 只输出 JSON，不要加解释。"
        )
        response = llm.generate(prompt, task="school")
        parsed = _parse_agent_school_payload(response)
        enriched.append(
            item.model_copy(
                update={
                    "reasons": parsed.get("reasons", item.reasons),
                    "risks": parsed.get("risks", item.risks),
                    "todo": parsed.get("todo", item.todo),
                    "agent_insight": parsed.get("insight", item.agent_insight),
                }
            )
        )
    return enriched


def build_timeline(profile: StudentProfile, recommendations: list[SchoolRecommendation]) -> list[str]:
    challenge_school = recommendations[0].school_name if recommendations else "目标院校"
    return [
        "第 1 周：补齐成绩单、排名证明、简历和项目摘要，形成统一材料包。",
        f"第 2 周：围绕 {challenge_school} 和稳妥院校整理报名要求，筛选导师名单。",
        "第 3 周：完善联系邮件，准备机考、项目追问和英文自我介绍。",
        "第 4 周：进行模拟面试和材料复盘，查漏补缺后提交申请。",
    ]


def format_plan_summary(
    profile: StudentProfile,
    analysis: ProfileAnalysis,
    recommendations: list[SchoolRecommendation],
    timeline: list[str],
    evidence_titles: list[str] | None = None,
) -> str:
    llm = get_llm_provider()
    rec_lines = [
        (
            f"{item.school_name} / {_level_label(item.level)} / 匹配度{item.match_score} / "
            f"理由:{'；'.join(item.reasons[:2]) or '暂无'} / "
            f"风险:{'；'.join(item.risks[:2]) or '暂无'}"
        )
        for item in recommendations
    ]
    strength_text = "；".join(analysis.strengths[:2]) or "暂无"
    weakness_text = "；".join(analysis.weaknesses[:2]) or "暂无明显短板"
    next_actions = "；".join(timeline[:2]) or "尽快整理材料并确认目标院校"
    prompt = (
        "你是保研规划顾问，请写一段真正个性化的中文规划摘要。\n"
        "要求：\n"
        "1. 必须点名学校，不要只说冲刺、稳妥、保底。\n"
        "2. 必须结合学生优势和短板，不能写空泛套话。\n"
        "3. 必须指出当前最应该先做的两件事。\n"
        "4. 不要解释系统流程，不要出现“系统建议”“综合判断如下”这类模板表达。\n"
        "5. 不得编造不存在的实验指标、论文、奖项、导师信息或截止日期。\n"
        "6. 输出 3 到 5 句自然中文。\n"
        f"学生：{profile.name}，综合分{analysis.overall_score}，学业分{analysis.academic_score}，科研分{analysis.research_score}。\n"
        f"优势：{strength_text}。\n"
        f"短板：{weakness_text}。\n"
        f"院校结果：{' | '.join(rec_lines)}。\n"
        f"接下来：{next_actions}。\n"
        f"参考资料：{'；'.join(evidence_titles or []) or '暂无'}。"
    )
    return " ".join(llm.generate(prompt, task="planner").split())


def _build_candidate_pool(
    profile: StudentProfile,
    documents: list[Document],
    evidence_chunks: list[RetrievedChunk],
) -> list[SchoolCatalogItem]:
    items = {item.school_name: item for item in BASE_CATALOG}

    for school in profile.preferred_schools:
        canonical = _canonical_school_name(school)
        if _is_special_school(canonical) and not _special_school_allowed(canonical, profile):
            continue
        if canonical not in items:
            items[canonical] = SchoolCatalogItem(
                school_name=canonical,
                aliases=(canonical.lower(), school.lower(), school),
                region=_guess_region_from_name(canonical, profile),
                directions=tuple(term.lower() for term in profile.research_interests[:4]) or ("computer science",),
                base_difficulty=_effective_base_difficulty(canonical, 84),
                program_name="Preferred School Program",
                source="preferred",
            )

    for school in _extract_school_candidates_from_documents(documents, evidence_chunks):
        canonical = _canonical_school_name(school)
        if _is_special_school(canonical) and not _special_school_allowed(canonical, profile):
            continue
        if canonical not in items:
            items[canonical] = SchoolCatalogItem(
                school_name=canonical,
                aliases=(canonical.lower(), school.lower(), school),
                region=_guess_region_from_name(canonical, profile),
                directions=tuple(term.lower() for term in profile.research_interests[:4]) or ("computer science",),
                base_difficulty=_effective_base_difficulty(canonical, 82),
                program_name="Knowledge Base Notice",
                source="knowledge",
            )

    return list(items.values())


def _extract_school_candidates_from_documents(documents: list[Document], evidence_chunks: list[RetrievedChunk]) -> list[str]:
    doc_ids = {chunk.document_id for chunk in evidence_chunks}
    candidates: list[str] = []
    for document in documents:
        if document.doc_type != "notice" or (doc_ids and document.id not in doc_ids):
            continue
        for value in (
            str(document.extracted.get("school_or_unit") or "").strip(),
            document.title.strip(),
        ):
            school = _match_catalog_school(value) or _extract_school_like_phrase(value)
            if school:
                candidates.append(school)
    return _unique_keep_order(candidates)


def _score_candidate(
    item: SchoolCatalogItem,
    profile: StudentProfile,
    analysis: ProfileAnalysis,
    documents: list[Document],
    evidence_chunks: list[RetrievedChunk],
) -> dict[str, Any]:
    interest_terms = {_normalize_term(term) for term in profile.research_interests}
    region_terms = {_normalize_term(term) for term in profile.target_regions}
    preferred_terms = {_normalize_term(term) for term in profile.preferred_schools}
    direction_terms = {_normalize_term(term) for term in item.directions}
    notice_context = _candidate_notice_context(item, documents, evidence_chunks)
    effective_difficulty = _effective_base_difficulty(item.school_name, item.base_difficulty)
    difficulty_gap = analysis.overall_score - effective_difficulty

    score = 64 + round((analysis.overall_score - 70) * 0.65)
    score += round(difficulty_gap * 0.9)
    reasons: list[str] = []
    risks: list[str] = []
    todo: list[str] = [
        "整理与目标方向最相关的项目，准备简历亮点描述。",
        "提前确认报名材料和截止时间。",
    ]

    alias_hit = any(_normalize_term(alias) in preferred_terms for alias in item.aliases) or _normalize_term(item.school_name) in preferred_terms
    region_hit = _normalize_term(item.region) in region_terms
    direction_hit = any(term in direction_terms for term in interest_terms)
    if alias_hit:
        score += 8
        reasons.append("该院校在你的偏好名单中，申请目标更明确。")

    if region_hit:
        score += 5
        reasons.append("地域偏好匹配，后续选校范围更聚焦。")

    if direction_hit:
        score += 7
        reasons.append("研究兴趣与学校方向标签存在直接重合。")

    if profile.rank_percent <= 10:
        score += 4
        reasons.append("排名基础较强，能够满足主流强校筛选门槛。")
    elif profile.rank_percent > 20:
        risks.append("排名不是显著优势，需要依赖项目和材料表达补强。")

    if profile.publications:
        score += 4
        reasons.append("已有论文或投稿经历，可增强科研潜力判断。")
    else:
        risks.append("科研成果偏少，建议把项目实验结果写得更具体。")

    if notice_context.evidence:
        score += min(6, len(notice_context.evidence) * 2)
        reasons.append("知识库中已有该校通知或相关资料，可补充更具体的申请信息。")
        todo.append("优先核对知识库中的通知要求，补齐材料和考核准备。")
    if notice_context.exam_format:
        reasons.append("系统已识别该校通知中的考核形式，可提前针对性准备。")
        if any("机考" in item_text or "coding" in item_text.lower() for item_text in notice_context.exam_format):
            risks.append("该校通知包含机考或编码测试，建议提前安排刷题和上机练习。")
    if notice_context.materials:
        reasons.append("系统已识别主要材料要求，可直接进入材料准备阶段。")

    if difficulty_gap < -10:
        risks.append("学校整体竞争强度较高，当前背景更适合作为冲刺选项。")
    elif difficulty_gap > 8:
        reasons.append("从当前背景看，这所学校更适合作为稳妥或保底布局。")

    if item.source == "preferred":
        todo.append("该校来自你的偏好补充，建议尽快核对真实通知和导师方向。")
    if item.source == "knowledge":
        todo.append("该校来自已导入通知，建议结合资料进一步筛选导师。")

    return {
        "school_name": item.school_name,
        "program_name": item.program_name,
        "score": max(52, min(95, score)),
        "difficulty_gap": difficulty_gap,
        "base_difficulty": effective_difficulty,
        "tier": _school_tier(item.school_name),
        "preferred_hit": alias_hit,
        "preferred_rank": _preferred_school_rank(item.school_name, profile),
        "region_hit": region_hit,
        "direction_hit": direction_hit,
        "source_priority": _source_priority(item.source),
        "source": item.source,
        "reasons": _unique_keep_order(reasons) or ["整体背景与该校方向基本匹配。"],
        "risks": _unique_keep_order(risks),
        "todo": _unique_keep_order(todo),
        "evidence": list(notice_context.evidence),
        "materials": list(notice_context.materials),
        "exam_format": list(notice_context.exam_format),
        "deadline": notice_context.deadline,
        "notice_url": notice_context.website,
    }


def _candidate_notice_context(
    item: SchoolCatalogItem,
    documents: list[Document],
    evidence_chunks: list[RetrievedChunk],
) -> NoticeContext:
    doc_ids = {chunk.document_id for chunk in evidence_chunks}
    titles: list[str] = []
    evidence_pairs: list[tuple[str, str]] = []
    materials: list[str] = []
    exam_format: list[str] = []
    deadline = ""
    website = ""

    for document in documents:
        if document.doc_type != "notice":
            continue
        if doc_ids and document.id not in doc_ids:
            continue
        haystack = _normalize_term(f"{document.title} {document.content} {document.extracted}")
        if not any(_normalize_term(alias) in haystack for alias in item.aliases):
            continue
        titles.append(document.title)
        url = str(document.extracted.get("website") or "").strip()
        if not url and str(document.source).startswith("http"):
            url = str(document.source).strip()
        evidence_pairs.append((document.title, url))
        materials.extend(str(value) for value in document.extracted.get("materials", []) if str(value).strip())
        exam_format.extend(str(value) for value in document.extracted.get("exam_format", []) if str(value).strip())
        if not deadline:
            deadline = str(document.extracted.get("deadline") or "").strip()
        if not website:
            website = url

    return NoticeContext(
        evidence=tuple(_unique_evidence_pairs(evidence_pairs)),
        materials=tuple(_unique_keep_order(materials)),
        exam_format=tuple(_unique_keep_order(exam_format)),
        deadline=deadline,
        website=website,
    )


def _pick_for_level(scored: list[dict[str, Any]], picked: list[dict[str, Any]], level: str, overall_score: int) -> dict[str, Any] | None:
    target_ranges = {
        "challenge": (overall_score + 1, overall_score + 12),
        "stable": (overall_score - 6, overall_score + 4),
        "safe": (overall_score - 16, overall_score - 2),
    }
    low, high = target_ranges[level]
    picked_names = {item["school_name"] for item in picked}
    pool: list[dict[str, Any]] = []
    for allowed_tiers in _tier_fallback_sequence(overall_score, level):
        pool = [
            item for item in scored
            if item["school_name"] not in picked_names
            and low <= item["score"] <= high
            and item.get("tier") in allowed_tiers
            and _level_allowed(item, level, overall_score)
        ]
        if pool:
            break
        pool = [
            item for item in scored
            if item["school_name"] not in picked_names
            and item.get("tier") in allowed_tiers
            and _level_allowed(item, level, overall_score)
        ]
        if pool:
            break
    if not pool:
        return None

    def rank_key(item: dict[str, Any]) -> tuple[int, int, int, int, int, int, int]:
        target_difficulty = _target_difficulty_for_level(overall_score, level)
        closeness = -abs(int(item.get("base_difficulty", 0)) - target_difficulty)
        preferred_bonus = 1 if item.get("preferred_hit") else 0
        preferred_rank = -int(item.get("preferred_rank", 99))
        region_bonus = 1 if item.get("region_hit") else 0
        direction_bonus = 1 if item.get("direction_hit") else 0
        source_priority = int(item.get("source_priority", 0))
        evidence_bonus = len(item["evidence"])
        if level == "challenge":
            return (
                preferred_bonus,
                preferred_rank,
                region_bonus,
                direction_bonus,
                source_priority,
                item["score"],
                evidence_bonus,
            )
        return (
            preferred_bonus,
            preferred_rank,
            region_bonus,
            direction_bonus,
            source_priority,
            closeness,
            evidence_bonus,
            item["score"],
        )

    chosen = sorted(pool, key=rank_key, reverse=True)[0]
    chosen["level"] = level
    return chosen


def _level_allowed(item: dict[str, Any], level: str, overall_score: int) -> bool:
    base_difficulty = int(item.get("base_difficulty", 0))
    if item.get("tier") == "T0":
        return level == "challenge"
    if item.get("tier") == "T1" and level == "safe":
        return False
    if base_difficulty >= 93 and overall_score < 92:
        return level != "safe"
    return True


def _to_recommendation(item: dict[str, Any]) -> SchoolRecommendation:
    return SchoolRecommendation(
        school_name=_display_school_name(item["school_name"]),
        program_name=item["program_name"],
        level=item["level"],
        match_score=item["score"],
        reasons=item["reasons"],
        risks=item["risks"],
        todo=item["todo"],
        evidence=[EvidenceReference(title=title, url=url) for title, url in item["evidence"]],
        materials=item["materials"],
        exam_format=item["exam_format"],
        deadline=item["deadline"],
        notice_url=item.get("notice_url", ""),
        agent_insight="",
    )


def _parse_agent_school_payload(response: str) -> dict[str, Any]:
    text = response.strip()
    try:
        import json

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        data = json.loads(text[start : end + 1])
        normalized: dict[str, Any] = {}
        for key in ("reasons", "risks", "todo"):
            value = data.get(key)
            if isinstance(value, list):
                normalized[key] = [str(item).strip() for item in value if str(item).strip()]
        insight = data.get("insight")
        if isinstance(insight, str) and insight.strip():
            normalized["insight"] = insight.strip()
        return normalized
    except Exception:
        return {}


def _canonical_school_name(name: str) -> str:
    matched = _match_catalog_school(name)
    return matched or _display_school_name(name.strip())


def _match_catalog_school(text: str) -> str:
    normalized = _normalize_term(text)
    for item in BASE_CATALOG:
        if any(_normalize_term(alias) in normalized or normalized in _normalize_term(alias) for alias in item.aliases):
            return item.school_name
    return ""


def _extract_school_like_phrase(text: str) -> str:
    if "大学" in text:
        prefix = text.split("大学", 1)[0].strip()
        if prefix:
            return f"{prefix}大学"
    return ""


def _guess_region_from_name(school: str, profile: StudentProfile) -> str:
    lowered = school.lower()
    region_aliases = {
        "beijing": ("beijing", "北京"),
        "shanghai": ("shanghai", "上海"),
        "hangzhou": ("hangzhou", "杭州", "浙江"),
        "nanjing": ("nanjing", "南京"),
        "xiamen": ("xiamen", "厦门"),
        "guangzhou": ("guangzhou", "广州", "中山"),
        "hefei": ("hefei", "合肥"),
        "harbin": ("harbin", "哈尔滨"),
        "wuhan": ("wuhan", "武汉"),
        "tianjin": ("tianjin", "天津"),
        "chengdu": ("chengdu", "成都", "四川"),
        "xian": ("xian", "西安"),
        "qingdao": ("qingdao", "青岛", "山东"),
        "changsha": ("changsha", "长沙", "湖南"),
        "chongqing": ("chongqing", "重庆"),
    }
    for region, aliases in region_aliases.items():
        if any(alias.lower() in lowered for alias in aliases):
            return region
    return "other"


def _score_academic(profile: StudentProfile) -> int:
    rank_score = max(50, 100 - int(profile.rank_percent * 2.2))
    gpa_score = min(100, int(profile.gpa / 4.0 * 100))
    return round(rank_score * 0.6 + gpa_score * 0.4)


def _score_research(profile: StudentProfile) -> int:
    score = 58 + len(profile.publications) * 14 + len(profile.research_interests) * 4
    return max(55, min(95, score))


def _score_projects(profile: StudentProfile) -> int:
    score = 60 + len(profile.projects) * 10
    if profile.notes.strip():
        score += 5
    return max(55, min(95, score))


def _score_competitions(profile: StudentProfile) -> int:
    score = 58 + len(profile.competitions) * 10
    return max(50, min(90, score))


def _score_language(profile: StudentProfile) -> int:
    text = profile.english_score.lower()
    if "ielts" in text or "toefl" in text:
        return 88
    if "6" in text:
        return 82
    if "4" in text:
        return 72
    return 68


def _normalize_term(text: str) -> str:
    return text.strip().lower()


def _unique_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _unique_evidence_pairs(items: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for title, url in items:
        normalized = title.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append((normalized, url.strip()))
    return result


def _level_label(level: str) -> str:
    return {"challenge": "冲刺", "stable": "稳妥", "safe": "保底"}.get(level, level)


def _display_school_name(name: str) -> str:
    text = name.strip()
    return SCHOOL_DISPLAY_MAP.get(text.lower(), text)


def _school_tier(name: str) -> str:
    lowered = name.strip().lower()
    if lowered in ENGLISH_TIER_MAP:
        return ENGLISH_TIER_MAP[lowered]
    return SCHOOL_TIER_MAP.get(_display_school_name(name), "T4")


def _effective_base_difficulty(name: str, fallback: int) -> int:
    tier = _school_tier(name)
    return TIER_BASE_DIFFICULTY.get(tier, fallback)


def _is_special_school(name: str) -> bool:
    return _display_school_name(name) in SPECIAL_SCHOOLS


def _special_school_allowed(name: str, profile: StudentProfile) -> bool:
    school = _display_school_name(name)
    preferred = {_display_school_name(item) for item in profile.preferred_schools}
    return school in preferred or school in profile.notes


def _preferred_school_rank(name: str, profile: StudentProfile) -> int:
    display = _display_school_name(name)
    for index, school in enumerate(profile.preferred_schools):
        if _display_school_name(school) == display:
            return index
    return 99


def _source_priority(source: str) -> int:
    return {
        "preferred": 3,
        "catalog": 2,
        "knowledge": 1,
    }.get(source, 0)


def _tier_fallback_sequence(overall_score: int, level: str) -> list[set[str]]:
    primary = _allowed_tiers_for_level(overall_score, level)
    fallback_map = {
        "challenge": [primary, {"T0", "T1"}, {"T1", "T2"}, {"T2", "T3"}, {"T3", "T4"}],
        "stable": [primary, {"T1", "T2"}, {"T2", "T3"}, {"T3", "T4"}, {"T4", "T5"}],
        "safe": [primary, {"T2", "T3"}, {"T3", "T4"}, {"T4", "T5"}, {"T1", "T2"}],
    }
    deduped: list[set[str]] = []
    seen: set[tuple[str, ...]] = set()
    for tiers in fallback_map[level]:
        key = tuple(sorted(tiers))
        if key not in seen:
            seen.add(key)
            deduped.append(tiers)
    return deduped


def _best_level_for_candidate(item: dict[str, Any], overall_score: int) -> str | None:
    choices: list[tuple[int, str]] = []
    for level in ("challenge", "stable", "safe"):
        if item.get("tier") not in _allowed_tiers_for_level(overall_score, level):
            continue
        if not _level_allowed(item, level, overall_score):
            continue
        target = _target_difficulty_for_level(overall_score, level)
        gap = abs(int(item.get("base_difficulty", 0)) - target)
        choices.append((gap, level))
    if not choices:
        return None
    return sorted(choices, key=lambda value: value[0])[0][1]


def _ensure_preferred_school_presence(
    scored: list[dict[str, Any]],
    picked: list[dict[str, Any]],
    overall_score: int,
) -> list[dict[str, Any]]:
    if any(item.get("preferred_hit") for item in picked):
        return picked
    preferred_candidates = [
        item for item in scored
        if item.get("preferred_hit") and int(item.get("score", 0)) >= max(60, overall_score - 12)
    ]
    if not preferred_candidates:
        return picked
    preferred = sorted(
        preferred_candidates,
        key=lambda item: (-int(item.get("preferred_rank", 99)), item["score"], len(item["evidence"])),
        reverse=True,
    )[0]
    level = _best_level_for_candidate(preferred, overall_score)
    if level is None:
        return picked
    replacement = dict(preferred)
    replacement["level"] = level
    for index, current in enumerate(picked):
        if current["level"] == level and not current.get("preferred_hit"):
            updated = list(picked)
            updated[index] = replacement
            return updated
    if level not in {item["level"] for item in picked}:
        updated = list(picked)
        updated.append(replacement)
        return updated
    return picked


def _backfill_missing_levels(
    scored: list[dict[str, Any]],
    picked: list[dict[str, Any]],
    overall_score: int,
) -> list[dict[str, Any]]:
    updated = list(picked)
    picked_names = {item["school_name"] for item in updated}
    for level in ("challenge", "stable", "safe"):
        if any(item["level"] == level for item in updated):
            continue
        candidate = _pick_for_level(scored, updated, level, overall_score)
        if candidate is None:
            continue
        candidate = dict(candidate)
        candidate["level"] = level
        if candidate["school_name"] in picked_names:
            continue
        updated.append(candidate)
        picked_names.add(candidate["school_name"])
    return updated


def _allowed_tiers_for_level(overall_score: int, level: str) -> set[str]:
    if overall_score >= 92:
        mapping = {
            "challenge": {"T0", "T1"},
            "stable": {"T1", "T2"},
            "safe": {"T2", "T3"},
        }
    elif overall_score >= 86:
        mapping = {
            "challenge": {"T1"},
            "stable": {"T2"},
            "safe": {"T3"},
        }
    elif overall_score >= 80:
        mapping = {
            "challenge": {"T1"},
            "stable": {"T2"},
            "safe": {"T3"},
        }
    elif overall_score >= 74:
        mapping = {
            "challenge": {"T2"},
            "stable": {"T3"},
            "safe": {"T4"},
        }
    else:
        mapping = {
            "challenge": {"T3"},
            "stable": {"T4"},
            "safe": {"T5"},
        }
    return mapping[level]


def _target_difficulty_for_level(overall_score: int, level: str) -> int:
    tier = sorted(_allowed_tiers_for_level(overall_score, level))[0]
    return TIER_BASE_DIFFICULTY.get(tier, 75)


def _enrich_profile_analysis(profile: StudentProfile, heuristic: ProfileAnalysis) -> ProfileAnalysis:
    llm = get_llm_provider()
    prompt = (
        "请基于给定学生背景，输出 JSON，字段必须为 strengths, weaknesses, suggestions, summary。\n"
        "要求：\n"
        "1. strengths/weaknesses/suggestions 都是中文数组，每个数组 2 到 4 条。\n"
        "2. 必须结合学生真实字段，不要写空泛模板，不要编造论文、奖项、竞赛成绩、导师信息或截止时间。\n"
        "3. summary 用 2 到 3 句中文，说明当前竞争力、主要短板和最优先动作。\n"
        "4. 只输出 JSON。\n"
        f"学生姓名：{profile.name}\n"
        f"学校专业：{profile.university} / {profile.major}\n"
        f"排名：前 {profile.rank_percent}%\n"
        f"GPA：{profile.gpa}\n"
        f"英语：{profile.english_score}\n"
        f"研究兴趣：{', '.join(profile.research_interests) or '未填写'}\n"
        f"项目经历：{'; '.join(profile.projects) or '未填写'}\n"
        f"竞赛经历：{'; '.join(profile.competitions) or '未填写'}\n"
        f"论文科研：{'; '.join(profile.publications) or '未填写'}\n"
        f"目标地区：{', '.join(profile.target_regions) or '未填写'}\n"
        f"偏好院校：{', '.join(profile.preferred_schools) or '未填写'}\n"
        f"备注：{profile.notes or '无'}\n"
        f"规则层优势：{'；'.join(heuristic.strengths) or '暂无'}\n"
        f"规则层短板：{'；'.join(heuristic.weaknesses) or '暂无'}\n"
        f"规则层建议：{'；'.join(heuristic.suggestions) or '暂无'}\n"
    )
    response = llm.generate(prompt, task="profile")
    parsed = _parse_profile_payload(response)
    if not parsed:
        logger.info("Profile analysis fell back to heuristic output for profile=%s", profile.name)
        return heuristic
    parsed = _sanitize_profile_payload(parsed, profile, heuristic)
    logger.info("Profile analysis enriched with LLM for profile=%s", profile.name)
    return heuristic.model_copy(
        update={
            "strengths": parsed.get("strengths", heuristic.strengths),
            "weaknesses": parsed.get("weaknesses", heuristic.weaknesses),
            "suggestions": parsed.get("suggestions", heuristic.suggestions),
            "summary": parsed.get("summary", heuristic.summary),
        }
    )


def _parse_profile_payload(response: str) -> dict[str, Any]:
    text = response.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

    normalized: dict[str, Any] = {}
    for key in ("strengths", "weaknesses", "suggestions"):
        value = data.get(key)
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                normalized[key] = items[:4]
    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip():
        normalized["summary"] = " ".join(summary.split())
    return normalized


def _sanitize_profile_payload(
    payload: dict[str, Any],
    profile: StudentProfile,
    heuristic: ProfileAnalysis,
) -> dict[str, Any]:
    normalized = dict(payload)
    for key, fallback in (
        ("strengths", heuristic.strengths),
        ("weaknesses", heuristic.weaknesses),
        ("suggestions", heuristic.suggestions),
    ):
        values = payload.get(key, fallback)
        if not isinstance(values, list):
            values = fallback
        cleaned = [
            _repair_profile_text(text, profile)
            for text in values
            if _profile_item_consistent(str(text), profile)
        ]
        normalized[key] = cleaned[:4] or fallback
    normalized["summary"] = _repair_profile_text(str(payload.get("summary") or heuristic.summary), profile)
    return normalized


def _repair_profile_text(text: str, profile: StudentProfile) -> str:
    repaired = text.strip()
    if not repaired:
        return repaired
    interests = "、".join(profile.research_interests[:3]) or "研究兴趣"
    first_interest = profile.research_interests[0] if profile.research_interests else "目标方向"
    regions = "、".join(profile.target_regions[:2]) or "目标地区"
    repaired = re.sub(r"\?{2,}(?:,\s*\?{2,}){1,3}", interests, repaired)
    repaired = re.sub(r"\?{2,}\s*数据集", f"{first_interest}相关数据集", repaired)
    repaired = re.sub(r"\?{2,}\s*,\s*\?{2,}", regions, repaired)
    repaired = re.sub(r"\?{2,}", first_interest, repaired)
    replacements = {
        "�": "",
    }
    for old, new in replacements.items():
        repaired = repaired.replace(old, new)
    return " ".join(repaired.split())


def _profile_item_consistent(text: str, profile: StudentProfile) -> bool:
    if profile.competitions and ("竞赛经历未填写" in text or "缺少竞赛" in text):
        return False
    if profile.publications and ("无论文" in text or "科研空白" in text):
        return False
    if not profile.publications and ("已有论文" in text or "论文经历丰富" in text):
        return False
    if profile.projects and ("缺少项目" in text or "项目经历不足" in text):
        return False
    if profile.english_score and "英语未填写" in text:
        return False
    if profile.preferred_schools and "偏好院校未填写" in text:
        return False
    return True
