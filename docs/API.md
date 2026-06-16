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
  - Adds a document.
  - Body: `title`, `doc_type`, `content`, `source`.
- `POST /api/knowledge/query`
  - Runs RAG-style mock question answering.
  - Body: `question`, `top_k`.
- `GET /api/knowledge/advisors`
  - Lists advisor samples.
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
