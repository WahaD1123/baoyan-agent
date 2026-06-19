from app.models import Document, RetrievedChunk
from app.tools.document_processing import extract_keywords


QUERY_EXPANSIONS = {
    "direct_phd": {
        "triggers": {
            "\u76f4\u535a",
            "\u8bfb\u535a",
            "\u535a\u58eb",
            "phd",
            "ph.d",
            "\u7855\u535a",
            "\u79d1\u7814",
            "\u5bfc\u5e08",
            "\u8981\u76f4\u535a",
        },
        "terms": {
            "\u76f4\u535a",
            "\u8bfb\u535a",
            "\u535a\u58eb",
            "\u535a\u58eb\u751f",
            "\u7855\u535a",
            "\u535a\u58eb\u7533\u8bf7",
            "\u535a\u58eb\u62db\u751f",
            "\u8bfb\u535a\u58eb",
            "\u79d1\u7814",
            "\u8bba\u6587",
            "\u5bfc\u5e08",
            "\u5b9e\u9a8c\u5ba4",
            "phd",
        },
        "preferred_types": {"experience": 3.0, "advisor": -0.9, "notice": -0.7, "other": -0.8},
    },
    "interview": {
        "triggers": {"\u9762\u8bd5", "\u673a\u8003", "\u7b14\u8bd5", "\u8003\u6838", "\u4e0a\u673a"},
        "terms": {
            "\u9762\u8bd5",
            "\u673a\u8003",
            "\u7b14\u8bd5",
            "\u8003\u6838",
            "\u4e0a\u673a",
            "\u7efc\u5408\u9762\u8bd5",
            "\u4e13\u4e1a\u9762\u8bd5",
            "\u82f1\u8bed\u9762\u8bd5",
        },
        "preferred_types": {"notice": 0.5, "experience": 0.5},
    },
    "materials": {
        "triggers": {"\u6750\u6599", "\u7b80\u5386", "\u6210\u7ee9\u5355", "\u63a8\u8350\u4fe1", "\u62a5\u540d"},
        "terms": {
            "\u6750\u6599",
            "\u7b80\u5386",
            "\u6210\u7ee9\u5355",
            "\u63a8\u8350\u4fe1",
            "\u62a5\u540d",
            "\u7533\u8bf7\u6750\u6599",
            "\u4e2a\u4eba\u9648\u8ff0",
            "\u6392\u540d\u8bc1\u660e",
        },
        "preferred_types": {"notice": 0.6, "experience": 0.25},
    },
}


def search_documents(documents: list[Document], query: str, top_k: int = 3) -> list[Document]:
    tokens = _query_terms(query)
    if not tokens:
        return documents[:top_k]

    def score(document: Document) -> int:
        haystack = " ".join(
            [
                document.title,
                document.content,
                document.doc_type,
                " ".join(document.keywords),
                str(document.extracted),
                str(document.analysis),
            ]
        ).lower()
        return sum(1 for token in tokens if token in haystack)

    ranked = sorted(documents, key=score, reverse=True)
    return [doc for doc in ranked if score(doc) > 0][:top_k]


def hybrid_retrieve(documents: list[Document], query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_terms = _query_terms(query)
    intent_weights = _intent_type_weights(query)
    candidates: list[RetrievedChunk] = []
    for document in documents:
        analysis_text = (
            f"{document.title} {document.doc_type} {' '.join(document.keywords)} "
            f"{document.analysis.get('summary', '')} "
            f"{document.analysis.get('structured_fields', document.extracted)} "
            f"{document.analysis.get('requirements', [])} "
            f"{document.analysis.get('important_dates', [])} "
            f"{document.analysis.get('exam_or_process', [])}"
        ).lower()
        analysis_hits = [term for term in query_terms if term.lower() in analysis_text]
        if analysis_hits:
            type_bonus = intent_weights.get(document.doc_type, 0)
            candidates.append(
                RetrievedChunk(
                    document_id=document.id,
                    document_title=document.title,
                    chunk_id=f"{document.id}:analysis",
                    text=_analysis_citation_text(document),
                    score=round(len(analysis_hits) + 0.8 + type_bonus, 3),
                    hit_reason="full analysis: " + ", ".join(analysis_hits[:6]),
                )
            )
        chunks = document.chunks or []
        if not chunks and document.content:
            chunks = []
        for chunk in chunks:
            text = (
                f"{document.title} {document.doc_type} {' '.join(chunk.keywords)} "
                f"{document.analysis.get('summary', '')} {document.analysis.get('structured_fields', '')} {chunk.text}"
            ).lower()
            hits = [term for term in query_terms if term.lower() in text]
            source_bonus = 0.2 if document.source_type in {"url", "pdf"} else 0
            type_bonus = 0.15 if document.doc_type in {"notice", "advisor", "experience"} else 0
            intent_bonus = intent_weights.get(document.doc_type, 0)
            exact_bonus = 0.5 if any(term.lower() in chunk.text.lower() for term in query_terms) else 0
            score = len(hits) + source_bonus + type_bonus + intent_bonus + exact_bonus
            if score > 0:
                candidates.append(
                    RetrievedChunk(
                        document_id=document.id,
                        document_title=document.title,
                        chunk_id=chunk.id,
                        text=chunk.text,
                        score=round(score, 3),
                        hit_reason=", ".join(hits[:6]) or "source/type relevance",
                    )
                )
    return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k]


def _query_terms(query: str) -> set[str]:
    lower = query.lower()
    terms = {term.lower() for term in extract_keywords(query, limit=16)}
    terms.update(token.lower() for token in query.replace(",", " ").replace("，", " ").split() if token.strip())
    for config in QUERY_EXPANSIONS.values():
        if any(trigger in lower for trigger in config["triggers"]):
            terms.update(term.lower() for term in config["terms"])
    return {term for term in terms if len(term.strip()) >= 2}


def _intent_type_weights(query: str) -> dict[str, float]:
    lower = query.lower()
    weights: dict[str, float] = {}
    for config in QUERY_EXPANSIONS.values():
        if any(trigger in lower for trigger in config["triggers"]):
            for doc_type, value in config["preferred_types"].items():
                weights[doc_type] = weights.get(doc_type, 0) + value
    if any(term in lower for term in {"\u8981\u4e0d\u8981", "\u662f\u5426", "\u5efa\u8bae", "\u600e\u4e48\u9009", "\u8981\u76f4\u535a"}):
        weights["experience"] = weights.get("experience", 0) + 1.2
        weights["notice"] = weights.get("notice", 0) - 0.4
        weights["advisor"] = weights.get("advisor", 0) - 0.4
        weights["other"] = weights.get("other", 0) - 0.4
    return weights


def _analysis_citation_text(document: Document) -> str:
    fields = document.analysis.get("structured_fields", document.extracted)
    parts = [
        f"全文分析摘要: {document.analysis.get('summary', '')}",
        f"结构化字段: {fields}",
        f"关键时间: {document.analysis.get('important_dates', [])}",
        f"材料/要求: {document.analysis.get('requirements', [])}",
        f"考核/流程: {document.analysis.get('exam_or_process', [])}",
    ]
    return "\n".join(part for part in parts if part.strip())
