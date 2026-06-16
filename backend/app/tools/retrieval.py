from app.models import Document


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
