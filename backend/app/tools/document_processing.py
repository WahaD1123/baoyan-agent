import re
from io import BytesIO
from typing import Any

from app.models import Document, DocumentChunk, DocumentType
from app.services.llm import get_llm_provider


STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "homepage",
    "home",
    "page",
    "version",
    "isbn",
    "copyright",
    "university",
    "professor",
    "publication",
    "publications",
    "需要",
    "材料",
    "申请",
    "导师",
    "研究",
    "通知",
    "大学",
    "学院",
}

RESEARCH_AREA_WHITELIST = [
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data mining",
    "information retrieval",
    "natural language processing",
    "large language model",
    "llm agents",
    "knowledge graph",
    "computer vision",
    "software engineering",
    "database",
    "distributed systems",
    "operating systems",
    "computer networks",
    "cyber security",
    "trustworthy ai",
    "ai systems",
]

MATERIAL_TERMS = [
    "resume",
    "cv",
    "transcript",
    "ranking certificate",
    "recommendation letter",
    "research statement",
    "personal statement",
    "publication",
    "certificate",
    "简历",
    "成绩单",
    "成绩排名",
    "排名证明",
    "推荐信",
    "个人陈述",
    "研究计划",
    "获奖证明",
    "论文",
    "身份证",
]

EXAM_TERMS = [
    "coding test",
    "written test",
    "interview",
    "professional interview",
    "english interview",
    "机考",
    "上机",
    "笔试",
    "面试",
    "英语面试",
    "综合面试",
    "专业面试",
]


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9+-]{2,}", text)
    counts: dict[str, int] = {}
    for word in words:
        key = word.lower()
        if key in STOP_WORDS:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def chunk_text(document_id: str, text: str, chunk_size: int = 650, overlap: int = 80) -> list[DocumentChunk]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(clean):
        piece = clean[start : start + chunk_size].strip()
        if piece:
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    index=index,
                    text=piece,
                    keywords=extract_keywords(piece, limit=8),
                )
            )
            index += 1
        if start + chunk_size >= len(clean):
            break
        start += chunk_size - overlap
    return chunks


def extract_text_from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is not installed. Run pip install -r requirements.txt") from exc
    reader = PdfReader(BytesIO(data))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page)


def heuristic_extract(doc_type: DocumentType, text: str, title: str = "") -> dict[str, Any]:
    lines = _non_empty_lines(text)
    joined = "\n".join(lines)
    preview = "\n".join(lines[:120])
    if doc_type == "notice":
        return {
            "school_or_unit": _first_match(
                f"{title}\n{preview}",
                [
                    r"([\u4e00-\u9fffA-Za-z]+大学)",
                    r"([\u4e00-\u9fffA-Za-z]+学院)",
                    r"([A-Z][A-Za-z .&-]+ University)",
                ],
            ),
            "project_name": title,
            "deadline": _extract_deadline(joined),
            "materials": _collect_terms(joined, MATERIAL_TERMS),
            "exam_format": _collect_terms(joined, EXAM_TERMS),
            "contact": _first_match(joined, [r"([\w.-]+@[\w.-]+)", r"电话[:：]?\s*([0-9\-]{7,})"]),
            "important_dates": _extract_dates(joined),
        }
    if doc_type == "advisor":
        full_text = f"{title}\n{joined}"
        return {
            "name": _extract_advisor_name(title, full_text),
            "university": _extract_university(full_text),
            "department": _extract_department(full_text),
            "research_areas": _extract_research_areas(full_text),
            "representative_works": _extract_representative_works(lines),
            "suitable_background": "适合有相关科研、项目经历，并能清楚说明研究兴趣的学生。",
        }
    if doc_type == "experience":
        return {
            "process": _lines_with_terms(lines, ["流程", "报名", "面试", "机考", "笔试", "camp", "interview"])[:8],
            "interview_questions": [line for line in lines if "?" in line or "？" in line][:10],
            "suggestions": _lines_with_terms(lines, ["建议", "注意", "避坑", "准备", "recommend", "suggest"])[:10],
        }
    return {"summary_keywords": extract_keywords(joined, limit=10)}


def llm_enrich_extraction(doc_type: DocumentType, title: str, text: str) -> dict[str, Any]:
    base = heuristic_extract(doc_type, text, title)
    prompt = (
        f"资料类型: {doc_type}\n标题: {title}\n"
        "请基于下面资料进行全文理解，提取和保研申请相关的关键字段。"
        "要求：中文、具体、不要编造；如果字段不存在就说明未提及。\n\n"
        f"{_analysis_prompt_text(text)}"
    )
    summary = get_llm_provider().generate(prompt, task="extract")
    base["llm_summary"] = summary
    return base


def build_full_document_analysis(document: Document) -> dict[str, Any]:
    extracted = document.extracted or heuristic_extract(document.doc_type, document.content, document.title)
    summary = str(extracted.get("llm_summary") or "")
    if not summary:
        prompt = (
            f"资料类型: {document.doc_type}\n标题: {document.title}\n"
            "请完整阅读资料后输出中文摘要，重点说明申请价值、关键信息、缺失信息和后续可提问点。\n\n"
            f"{_analysis_prompt_text(document.content)}"
        )
        summary = get_llm_provider().generate(prompt, task="extract")

    important_lines = _important_lines(document.content)
    return {
        "status": "completed",
        "mode": "full_document_analysis",
        "scope": "网页/PDF/文本正文已完整解析并保存，入库时生成结构化理解结果。",
        "summary": summary,
        "structured_fields": extracted,
        "important_dates": extracted.get("important_dates") or _extract_dates(document.content),
        "requirements": extracted.get("materials") or _lines_with_terms(_non_empty_lines(document.content), MATERIAL_TERMS)[:8],
        "exam_or_process": extracted.get("exam_format") or _lines_with_terms(_non_empty_lines(document.content), EXAM_TERMS)[:8],
        "risks": _analysis_risks(document),
        "qa_notes": _qa_notes(document),
        "citation_chunk_ids": [chunk.id for chunk in document.chunks[:5]],
        "source_coverage": {
            "content_chars": len(document.content),
            "chunk_count": len(document.chunks),
            "source_type": document.source_type,
            "source": document.source,
        },
        "important_lines": important_lines[:12],
    }


def prepare_document(document: Document) -> Document:
    document.keywords = extract_keywords(f"{document.title} {document.content}")
    document.chunks = chunk_text(document.id, document.content)
    if not document.extracted:
        document.extracted = llm_enrich_extraction(document.doc_type, document.title, document.content)
    if not document.analysis:
        document.analysis = build_full_document_analysis(document)
    return document


def _analysis_prompt_text(text: str, limit: int = 12000) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    head = clean[: int(limit * 0.45)]
    middle_start = max(0, len(clean) // 2 - int(limit * 0.15))
    middle = clean[middle_start : middle_start + int(limit * 0.3)]
    tail = clean[-int(limit * 0.25) :]
    return f"{head}\n\n[中部内容节选]\n{middle}\n\n[尾部内容节选]\n{tail}"


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" ：:-\t\r\n")
    return ""


def _collect_terms(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _lines_with_terms(lines: list[str], terms: list[str]) -> list[str]:
    lowered_terms = [term.lower() for term in terms]
    return [line for line in lines if any(term in line.lower() for term in lowered_terms)]


def _extract_dates(text: str) -> list[str]:
    patterns = [
        r"20[0-9]{2}[年/-][0-9]{1,2}[月/-][0-9]{1,2}日?",
        r"[0-9]{1,2}月[0-9]{1,2}日",
        r"20[0-9]{2}\.[0-9]{1,2}\.[0-9]{1,2}",
    ]
    dates: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            if match not in dates:
                dates.append(match)
    return dates[:10]


def _extract_deadline(text: str) -> str:
    deadline = _first_match(
        text,
        [
            r"(?:截止|截止时间|截止日期|报名截止|申请截止)[:：]?\s*([^\n，。；;]{4,40})",
            r"(?:deadline|due date)[:：]?\s*([^\n,.;]{4,40})",
        ],
    )
    return deadline or (_extract_dates(text)[0] if _extract_dates(text) else "")


def _extract_advisor_name(title: str, text: str) -> str:
    candidates = [
        _first_match(title, [r"^([\u4e00-\u9fff]{2,4})\s*[-_—|｜]\s*[\u4e00-\u9fffA-Za-z]+(?:大学|学院)"]),
        _first_match(title, [r"^([A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,3})\s*[-_—|｜]\s*"]),
        _first_match(text, [r"(?m)^#{1,4}\s*([\u4e00-\u9fff]{2,4})\s*$"]),
        _first_match(text, [r"(?:教师姓名|姓名|导师|负责人)[:：\s]*([\u4e00-\u9fff]{2,4})"]),
        _first_chinese_name_line(text),
        _first_match(title, [r"([A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,3})'s Homepage"]),
        _first_match(text, [r"\bProfessor\s+([A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,3})\b"]),
        _first_match(text, [r"\bProf\.?\s+([A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){1,3})\b"]),
    ]
    for candidate in candidates:
        if candidate and candidate.lower() not in STOP_WORDS and not candidate.endswith(("大学", "学院")):
            return candidate
    return ""


def _extract_university(text: str) -> str:
    chinese_university = _first_match(
        text,
        [
            r"[-_—|｜]\s*([\u4e00-\u9fff]{2,20}大学)",
            r"([\u4e00-\u9fff]{2,20}大学)",
        ],
    )
    if chinese_university:
        return chinese_university
    candidates = re.findall(r"([A-Z][A-Za-z .&-]{2,60}\sUniversity)", text)
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate).strip(" ,.;")
        if 5 <= len(normalized) <= 80:
            return normalized
    return ""


def _extract_department(text: str) -> str:
    return _first_match(
        text,
        [
            r"(?:Department|School|College) of ([A-Za-z &-]{3,80})",
            r"([\u4e00-\u9fff]{2,20}(?:信息学院|人工智能学院|计算机学院|软件学院))",
            r"([\u4e00-\u9fff]{2,20}(?:学院|系|实验室))",
        ],
    ) or "Computer Science"


def _extract_research_areas(text: str) -> list[str]:
    lower = text.lower()
    areas = [area for area in RESEARCH_AREA_WHITELIST if area in lower]
    interest_text = _first_match(
        text,
        [
            r"research interests? (?:include|are|:)\s*([^.。;；\n]{8,240})",
            r"(?:研究方向|研究兴趣)[:：\s]*([^\n。；;]{4,200})",
        ],
    )
    if interest_text:
        pieces = re.split(r",|;|；|、|/|\band\b", interest_text)
        for piece in pieces:
            area = re.sub(r"[^A-Za-z\u4e00-\u9fff +#-]", " ", piece).strip().lower()
            area = re.sub(r"\s+", " ", area)
            if 3 <= len(area) <= 50 and area not in STOP_WORDS and area not in areas:
                areas.append(area)
    return areas[:8] or extract_keywords(text, limit=5)


def _first_chinese_name_line(text: str) -> str:
    lines = _non_empty_lines(text)
    context_terms = ("教授", "副教授", "博士", "博士生导师", "硕士生导师", "研究方向", "学术研究", "个人简介", "国家杰青")
    stop_lines = {"首页", "学院概况", "师资队伍", "杰出人才", "科学研究", "招生信息", "联系我们"}
    for index, line in enumerate(lines[:160]):
        clean = re.sub(r"^#{1,4}\s*", "", line).strip()
        if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", clean):
            continue
        if clean in stop_lines or clean.endswith(("大学", "学院")):
            continue
        nearby = "\n".join(lines[index + 1 : index + 5])
        if any(term in nearby for term in context_terms):
            return clean
    return ""


def _extract_representative_works(lines: list[str]) -> list[str]:
    works = []
    for line in lines:
        lower = line.lower()
        if any(term in lower for term in ["paper", "publication", "journal", "conference", "论文", "成果", "代表作"]):
            works.append(line[:180])
    return works[:5]


def _important_lines(text: str) -> list[str]:
    terms = MATERIAL_TERMS + EXAM_TERMS + ["deadline", "截止", "报名", "联系", "email", "研究方向", "research interests"]
    return _lines_with_terms(_non_empty_lines(text), terms)


def _analysis_risks(document: Document) -> list[str]:
    risks = []
    fields = document.extracted or {}
    if document.doc_type == "notice":
        if not fields.get("deadline"):
            risks.append("未稳定识别截止时间，演示时建议人工核对原文。")
        if not fields.get("materials"):
            risks.append("未稳定识别材料清单，建议补充文本或换用可复制网页。")
    if document.doc_type == "advisor":
        if not fields.get("name"):
            risks.append("未稳定识别导师姓名，建议检查主页标题或手动修正。")
        if not fields.get("research_areas"):
            risks.append("研究方向信息不足，导师匹配分数可能偏保守。")
    if not risks:
        risks.append("暂无明显结构化缺口，仍建议展示时保留原文引用。")
    return risks


def _qa_notes(document: Document) -> list[str]:
    if document.doc_type == "notice":
        return ["这项申请需要哪些材料？", "报名截止时间是什么时候？", "考核形式包括哪些？"]
    if document.doc_type == "advisor":
        return ["这位导师的主要研究方向是什么？", "我的项目经历和导师方向是否匹配？", "联系邮件应该突出什么？"]
    if document.doc_type == "experience":
        return ["这篇经验贴提到了哪些面试问题？", "申请流程有哪些关键节点？", "有哪些避坑建议？"]
    return ["这份资料的核心信息是什么？", "有哪些可以用于申请规划的内容？"]
