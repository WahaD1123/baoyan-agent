from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.models import Document, ProfileAnalysis, RetrievedChunk, SchoolRecommendation, StudentProfile
from app.services.llm import get_llm_provider
from app.tools.retrieval import hybrid_retrieve


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
    titles: tuple[str, ...]
    materials: tuple[str, ...]
    exam_format: tuple[str, ...]
    deadline: str


BASE_CATALOG: tuple[SchoolCatalogItem, ...] = (
    SchoolCatalogItem("Tsinghua University", ("tsinghua", "清华", "清华大学"), "beijing", ("ai", "systems", "theory"), 95, "CS Summer Camp"),
    SchoolCatalogItem("Peking University", ("pku", "peking university", "北大", "北京大学"), "beijing", ("ai", "theory", "nlp"), 94, "Information Science Program"),
    SchoolCatalogItem("Shanghai Jiao Tong University", ("sjtu", "shanghai jiao tong university", "上交", "上海交通大学"), "shanghai", ("ai", "machine learning", "systems", "agent", "retrieval"), 91, "CS Summer Camp"),
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

    return ProfileAnalysis(
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
        prompt = (
            f"学生画像：排名前 {profile.rank_percent}%，GPA {profile.gpa}，方向 {', '.join(profile.research_interests)}。\n"
            f"学校：{item.school_name}，层级：{item.level}，匹配度：{item.match_score}。\n"
            f"规则层推荐理由：{'；'.join(item.reasons) or '暂无'}。\n"
            f"规则层风险提示：{'；'.join(item.risks) or '暂无'}。\n"
            f"规则层待办：{'；'.join(item.todo) or '暂无'}。\n"
            f"材料要求：{'；'.join(item.materials) or '暂无'}。\n"
            f"考核形式：{'；'.join(item.exam_format) or '暂无'}。\n"
            f"截止时间：{item.deadline or '暂无'}。\n"
            f"依据资料：{'；'.join(item.evidence) or '暂无'}。\n"
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
    rec_lines = [f"{item.school_name}（{_level_label(item.level)}，匹配度 {item.match_score}）" for item in recommendations]
    prompt = (
        f"学生：{profile.name}，综合分 {analysis.overall_score}。\n"
        f"推荐院校：{'；'.join(rec_lines)}。\n"
        f"时间线：{'；'.join(timeline)}。\n"
        f"参考资料：{'；'.join(evidence_titles or []) or '暂无'}。\n"
        "请用 2 到 3 句中文写一段规划摘要，语气专业、具体，不要解释系统过程。"
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
        if canonical not in items:
            items[canonical] = SchoolCatalogItem(
                school_name=canonical,
                aliases=(canonical.lower(), school.lower(), school),
                region=_guess_region_from_name(canonical, profile),
                directions=tuple(term.lower() for term in profile.research_interests[:4]) or ("computer science",),
                base_difficulty=84,
                program_name="Preferred School Program",
                source="preferred",
            )

    for school in _extract_school_candidates_from_documents(documents, evidence_chunks):
        canonical = _canonical_school_name(school)
        if canonical not in items:
            items[canonical] = SchoolCatalogItem(
                school_name=canonical,
                aliases=(canonical.lower(), school.lower(), school),
                region=_guess_region_from_name(canonical, profile),
                directions=tuple(term.lower() for term in profile.research_interests[:4]) or ("computer science",),
                base_difficulty=82,
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
    difficulty_gap = analysis.overall_score - item.base_difficulty

    score = 64 + round((analysis.overall_score - 70) * 0.65)
    reasons: list[str] = []
    risks: list[str] = []
    todo: list[str] = [
        "整理与目标方向最相关的项目，准备简历亮点描述。",
        "提前确认报名材料和截止时间。",
    ]

    alias_hit = any(_normalize_term(alias) in preferred_terms for alias in item.aliases) or _normalize_term(item.school_name) in preferred_terms
    if alias_hit:
        score += 8
        reasons.append("该院校在你的偏好名单中，申请目标更明确。")

    if _normalize_term(item.region) in region_terms:
        score += 5
        reasons.append("地域偏好匹配，后续选校范围更聚焦。")

    if any(term in direction_terms for term in interest_terms):
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

    if notice_context.titles:
        score += min(6, len(notice_context.titles) * 2)
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
        "score": max(60, min(95, score)),
        "difficulty_gap": difficulty_gap,
        "reasons": _unique_keep_order(reasons) or ["整体背景与该校方向基本匹配。"],
        "risks": _unique_keep_order(risks),
        "todo": _unique_keep_order(todo),
        "evidence": list(notice_context.titles),
        "materials": list(notice_context.materials),
        "exam_format": list(notice_context.exam_format),
        "deadline": notice_context.deadline,
    }


def _candidate_notice_context(
    item: SchoolCatalogItem,
    documents: list[Document],
    evidence_chunks: list[RetrievedChunk],
) -> NoticeContext:
    doc_ids = {chunk.document_id for chunk in evidence_chunks}
    titles: list[str] = []
    materials: list[str] = []
    exam_format: list[str] = []
    deadline = ""

    for document in documents:
        if document.doc_type != "notice":
            continue
        if doc_ids and document.id not in doc_ids:
            continue
        haystack = _normalize_term(f"{document.title} {document.content} {document.extracted}")
        if not any(_normalize_term(alias) in haystack for alias in item.aliases):
            continue
        titles.append(document.title)
        materials.extend(str(value) for value in document.extracted.get("materials", []) if str(value).strip())
        exam_format.extend(str(value) for value in document.extracted.get("exam_format", []) if str(value).strip())
        if not deadline:
            deadline = str(document.extracted.get("deadline") or "").strip()

    return NoticeContext(
        titles=tuple(_unique_keep_order(titles)),
        materials=tuple(_unique_keep_order(materials)),
        exam_format=tuple(_unique_keep_order(exam_format)),
        deadline=deadline,
    )


def _pick_for_level(scored: list[dict[str, Any]], picked: list[dict[str, Any]], level: str, overall_score: int) -> dict[str, Any] | None:
    target_ranges = {
        "challenge": (overall_score + 2, overall_score + 12),
        "stable": (overall_score - 4, overall_score + 3),
        "safe": (overall_score - 14, overall_score - 5),
    }
    low, high = target_ranges[level]
    picked_names = {item["school_name"] for item in picked}
    pool = [item for item in scored if item["school_name"] not in picked_names and low <= item["score"] <= high]
    if not pool:
        pool = [item for item in scored if item["school_name"] not in picked_names]
    if not pool:
        return None

    def rank_key(item: dict[str, Any]) -> tuple[int, int, int]:
        center = (low + high) // 2
        closeness = -abs(item["score"] - center)
        evidence_bonus = len(item["evidence"])
        return (closeness, evidence_bonus, item["score"])

    chosen = sorted(pool, key=rank_key, reverse=True)[0]
    chosen["level"] = level
    return chosen


def _to_recommendation(item: dict[str, Any]) -> SchoolRecommendation:
    return SchoolRecommendation(
        school_name=item["school_name"],
        program_name=item["program_name"],
        level=item["level"],
        match_score=item["score"],
        reasons=item["reasons"],
        risks=item["risks"],
        todo=item["todo"],
        evidence=item["evidence"],
        materials=item["materials"],
        exam_format=item["exam_format"],
        deadline=item["deadline"],
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
    return matched or name.strip()


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
    for token in ("beijing", "shanghai", "hangzhou", "nanjing", "xiamen", "guangzhou", "hefei", "harbin"):
        if token in lowered:
            return token
    if profile.target_regions:
        return _normalize_term(profile.target_regions[0])
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


def _level_label(level: str) -> str:
    return {"challenge": "冲刺", "stable": "稳妥", "safe": "保底"}.get(level, level)
