from app.models import Document, RetrievedChunk
from app.tools.document_processing import extract_keywords


def search_documents(documents: list[Document], query: str, top_k: int = 3) -> list[Document]:
    tokens = {token.lower() for token in query.replace(",", " ").split() if token.strip()}
    if not tokens:
        return documents[:top_k]

    def score(document: Document) -> int:
        haystack = " ".join(
            [document.title, document.content, document.doc_type, " ".join(document.keywords)]
        ).lower()
        return sum(1 for token in tokens if token in haystack)

    ranked = sorted(documents, key=score, reverse=True)
    return [doc for doc in ranked if score(doc) > 0][:top_k] or documents[:top_k]


def hybrid_retrieve(documents: list[Document], query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_terms = set(extract_keywords(query, limit=16))
    if not query_terms:
        query_terms = {token.lower() for token in query.split() if token.strip()}
    candidates: list[RetrievedChunk] = []
    for document in documents:
        chunks = document.chunks or []
        if not chunks and document.content:
            chunks = []
        for chunk in chunks:
            text = f"{document.title} {document.doc_type} {' '.join(chunk.keywords)} {chunk.text}".lower()
            hits = [term for term in query_terms if term.lower() in text]
            source_bonus = 0.2 if document.source_type in {"url", "pdf"} else 0
            type_bonus = 0.15 if document.doc_type in {"notice", "advisor", "experience"} else 0
            score = len(hits) + source_bonus + type_bonus
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
    if not candidates:
        for document in documents[:top_k]:
            text = document.chunks[0].text if document.chunks else document.content[:650]
            candidates.append(
                RetrievedChunk(
                    document_id=document.id,
                    document_title=document.title,
                    chunk_id=document.chunks[0].id if document.chunks else document.id,
                    text=text,
                    score=0.1,
                    hit_reason="fallback",
                )
            )
    return sorted(candidates, key=lambda item: item.score, reverse=True)[:top_k]
