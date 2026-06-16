# Baoyan Agent

面向 CS 保研申请场景的多 Agent 中间件系统。项目目标是把用户画像、资料知识库、导师匹配、申请规划、材料生成和模拟面试串成一个可展示的 workflow，而不是普通问答页面。

## Tech Stack

- Backend: FastAPI, Pydantic, in-memory mock services for MVP
- Frontend: React, Vite, TypeScript
- AI layer: Mock LLM by default, with an OpenAI-compatible provider reserved
- Architecture keywords: API Gateway, Agent workflow, RAG, MCP/tool layer, model routing

## Quick Start

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend tests:

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the app at `http://localhost:5173`. The frontend can show mock data even when the backend is not running, but the best demo is with both services started.

## Main Demo Flow

1. Fill in the student profile.
2. Add admissions notices, experience posts, resume notes, or advisor information to the knowledge base.
3. Generate a school application plan with multiple Agents.
4. Match advisors from the knowledge base.
5. Generate an advisor contact email.
6. Generate mock interview questions.
7. Review workflow records to explain the middleware design.

## DashScope

The project runs with Mock LLM by default. To use Alibaba Cloud DashScope locally, create `.env` in the repo root or `backend/`:

```powershell
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your-new-local-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-vl-max
```

Do not commit `.env` or paste real keys into code, docs, issues, or chat logs.

## Member B Demo

Member B owns the heterogeneous knowledge module:

1. Add a notice by URL through `/api/knowledge/documents/url`.
2. Upload a PDF through `/api/knowledge/documents/upload`.
3. Paste an experience post through `/api/knowledge/documents/text`.
4. Ask a RAG question through `/api/knowledge/query` and show cited chunks.
5. Add an advisor homepage through `/api/knowledge/advisors/url`.
6. Match advisors through `/api/knowledge/advisors/match`.

## Team Guide

Read [docs/TEAM_GUIDE.md](docs/TEAM_GUIDE.md) before adding new modules. Read [docs/API.md](docs/API.md) before changing API contracts.
