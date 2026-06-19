import json
import re
from typing import Any

from app.models import Document
from app.services.llm import get_llm_provider
from app.tools.retrieval import hybrid_retrieve


def route_documents_by_library(question: str, documents: list[Document], limit: int = 4) -> list[Document]:
    if not documents:
        return []

    catalog = _build_catalog(documents)
    prompt = (
        "你是保研资料库路由器。请先阅读整个资料库目录，再判断哪些资料真正适合回答用户问题。\n"
        "只输出 JSON，不要输出解释。格式：{\"selected_ids\": [\"doc_xxx\"], \"reason\": \"...\"}。\n"
        "如果资料库没有相关资料，selected_ids 输出空数组。\n"
        "判断标准：经验建议类问题优先选择经验贴；导师主页只用于导师方向/联系/匹配问题；官网通知只用于时间、材料、考核、招生政策问题。\n\n"
        f"用户问题：{question}\n\n"
        f"资料库目录：\n{catalog}"
    )
    raw = get_llm_provider().generate(prompt, task="knowledge")
    selected_ids = _parse_selected_ids(raw)
    if not selected_ids:
        return _local_route(question, documents, limit)

    by_id = {document.id: document for document in documents}
    selected = [by_id[doc_id] for doc_id in selected_ids if doc_id in by_id]
    return selected[:limit]


def route_chunks_for_documents(question: str, documents: list[Document], limit: int = 5):
    if not documents:
        return []
    return hybrid_retrieve(documents, question, limit)


def _build_catalog(documents: list[Document]) -> str:
    rows = []
    for index, document in enumerate(documents, start=1):
        analysis = document.analysis or {}
        summary = str(analysis.get("summary") or document.extracted.get("llm_summary") or document.content[:300])
        fields = analysis.get("structured_fields", document.extracted)
        rows.append(
            "\n".join(
                [
                    f"[{index}] id={document.id}",
                    f"title={document.title}",
                    f"type={document.doc_type}",
                    f"source_type={document.source_type}",
                    f"summary={_compact(summary, 520)}",
                    f"fields={_compact(str(fields), 420)}",
                ]
            )
        )
    return "\n\n".join(rows)


def _parse_selected_ids(raw: str) -> list[str]:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return []
    try:
        data: dict[str, Any] = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    ids = data.get("selected_ids", [])
    if not isinstance(ids, list):
        return []
    return [str(item) for item in ids if str(item).startswith("doc_")]


def _local_route(question: str, documents: list[Document], limit: int) -> list[Document]:
    question_lower = question.lower()
    scored: list[tuple[float, Document]] = []
    for document in documents:
        text = " ".join(
            [
                document.title,
                document.doc_type,
                str(document.extracted),
                str(document.analysis),
                document.content[:3000],
            ]
        ).lower()
        score = 0.0
        for token in _question_tokens(question):
            if token in text:
                score += 1
        if any(term in question_lower for term in ["直博", "读博", "博士", "phd", "要不要"]):
            if document.doc_type == "experience":
                score += 5
            elif document.doc_type in {"advisor", "notice", "other"}:
                score -= 1
        if any(term in question_lower for term in ["材料", "截止", "考核", "面试", "报名"]):
            if document.doc_type == "notice":
                score += 3
            elif document.doc_type == "experience":
                score += 1
        if score > 0:
            scored.append((score, document))
    return [document for _, document in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def _question_tokens(question: str) -> set[str]:
    tokens = {item for item in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9+-]{2,}", question.lower())}
    if "直博" in question:
        tokens.update({"直博", "读博", "博士", "科研", "导师", "论文"})
    return tokens


def _compact(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean[:limit]
