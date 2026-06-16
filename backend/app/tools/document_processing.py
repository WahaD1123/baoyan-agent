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
    "需要",
    "材料",
    "申请",
    "导师",
    "研究",
}


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
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    joined = "\n".join(lines[:80])
    if doc_type == "notice":
        return {
            "school_or_unit": _first_match(joined, [r"([\u4e00-\u9fffA-Za-z]+大学)", r"([\u4e00-\u9fffA-Za-z]+学院)"]),
            "project_name": title,
            "deadline": _first_match(joined, [r"截止(?:时间|日期)?[:：]?\s*([^\n，。,；;]{4,30})", r"([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)"]),
            "materials": _collect_terms(joined, ["简历", "成绩单", "排名证明", "推荐信", "个人陈述", "获奖证明", "论文", "身份证"]),
            "exam_format": _collect_terms(joined, ["机考", "上机", "面试", "英语面试", "综合面试", "专业面试", "笔试"]),
            "contact": _first_match(joined, [r"[\w.-]+@[\w.-]+", r"电话[:：]?\s*([0-9\-]{7,})"]),
        }
    if doc_type == "advisor":
        return {
            "name": _first_match(title + "\n" + joined, [r"(?:Prof\.?|Professor|导师|姓名)[:： ]*([A-Za-z .]{3,40})", r"姓名[:：]\s*([\u4e00-\u9fff]{2,4})"]),
            "research_areas": extract_keywords(joined, limit=8),
            "representative_works": [line for line in lines if any(term in line.lower() for term in ["paper", "publication", "论文", "成果"])][:5],
            "suitable_background": "Matches students with related projects and clear research motivation.",
        }
    if doc_type == "experience":
        return {
            "process": [line for line in lines if any(term in line for term in ["流程", "报名", "面试", "机考"])][:6],
            "interview_questions": [line for line in lines if "?" in line or "？" in line][:8],
            "suggestions": [line for line in lines if any(term in line for term in ["建议", "注意", "避坑", "准备"])][:8],
        }
    return {"summary_keywords": extract_keywords(joined, limit=10)}


def llm_enrich_extraction(doc_type: DocumentType, title: str, text: str) -> dict[str, Any]:
    base = heuristic_extract(doc_type, text, title)
    prompt = (
        f"资料类型: {doc_type}\n标题: {title}\n"
        f"请基于以下资料提取保研申请相关关键信息，输出中文要点，不要编造。\n\n{text[:3500]}"
    )
    summary = get_llm_provider().generate(prompt, task="extract")
    base["llm_summary"] = summary
    return base


def prepare_document(document: Document) -> Document:
    document.keywords = extract_keywords(f"{document.title} {document.content}")
    document.chunks = chunk_text(document.id, document.content)
    if not document.extracted:
        document.extracted = llm_enrich_extraction(document.doc_type, document.title, document.content)
    return document


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _collect_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term.lower() in text.lower()]
