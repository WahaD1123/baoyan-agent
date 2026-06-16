# API Reference

Base URL: `http://127.0.0.1:8000`

## Health

- `GET /api/health`
  - Returns service status.

## Profile

- `GET /api/profile`
  - Returns the current `StudentProfile`.
- `POST /api/profile`
  - Saves a `StudentProfile`.

## Knowledge

- `GET /api/knowledge/documents`
  - Lists knowledge base documents.
- `POST /api/knowledge/documents`
  - Adds a text document. Kept for backward compatibility.
  - Body: `title`, `doc_type`, `content`, `source`.
- `POST /api/knowledge/documents/text`
  - Adds a manually pasted document and records an ingest workflow.
  - Body: `title`, `doc_type`, `source_type`, `content`, `source`.
- `POST /api/knowledge/documents/upload`
  - Uploads a PDF file and extracts text into the knowledge base.
  - Form fields: `file`, `doc_type`, `title`.
- `POST /api/knowledge/documents/url`
  - Crawls a notice, advisor, or experience URL and stores structured content.
  - Body: `url`, `doc_type`, optional `title`.
- `GET /api/knowledge/documents/{id}`
  - Returns one document with chunks and extracted fields.
- `POST /api/knowledge/query`
  - Runs hybrid retrieval plus RAG-style answering with cited chunks.
  - Body: `question`, `top_k`.
- `GET /api/knowledge/advisors`
  - Lists advisor samples.
- `POST /api/knowledge/advisors/url`
  - Crawls one advisor homepage and saves both a document and an advisor card.
  - Body: `url`, optional `title`.
- `POST /api/knowledge/advisors/search`
  - Searches the local advisor library by school, direction, and keywords.
  - Body: `university`, `direction`, `keywords`, `limit`.
- `POST /api/knowledge/advisors/match`
  - Matches advisors for a profile.
  - Body: `profile`, `top_k`.

## Planning

- `POST /api/planning/generate`
  - Runs `ProfileAgent`, `SchoolRecommendAgent`, and `PlannerAgent`.
  - Body: `profile`, optional `target`.

## Materials

- `POST /api/materials/email`
  - Generates an advisor contact email draft.
  - Body: `profile`, optional `advisor`, optional `purpose`.

## Interview

- `POST /api/interview/mock`
  - Generates mock interview questions.
  - Body: `profile`, `target_school`, `direction`.

## Workflows

- `GET /api/workflows`
  - Lists workflow records, newest first.
- `GET /api/workflows/{workflow_id}`
  - Returns a single workflow record.
