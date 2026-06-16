# Architecture

## Overview

Baoyan Agent uses a simple single-repo architecture:

```text
React UI
  |
  v
FastAPI API Gateway
  |
  v
Workflow Engine
  |
  +-- Agents
  |    +-- ProfileAgent
  |    +-- SchoolRecommendAgent
  |    +-- KnowledgeAgent
  |    +-- AdvisorMatchAgent
  |    +-- MaterialAgent
  |    +-- InterviewAgent
  |    +-- CriticAgent
  |
  +-- Tool Layer
       +-- Document retrieval
       +-- Advisor matching
       +-- LLM provider
       +-- Future MCP adapters
```

## Middleware Points

- API Gateway: FastAPI routers expose consistent module APIs.
- Workflow Engine: each user task is converted into ordered Agent steps.
- Tool Layer: retrieval and future MCP tools are isolated from API handlers.
- Model Routing: `LLM_PROVIDER=mock` works by default and can later be replaced.
- Workflow Records: every generated result keeps its Agent steps for demonstration.

## Current MVP Storage

The MVP uses an in-memory store in `backend/app/services/store.py`. This keeps the project easy to run. Later, it can be replaced by:

- SQLite or PostgreSQL for profiles, documents, advisors, and workflow records.
- A vector database for document retrieval.
- Redis for cache and session state.
- A queue for asynchronous document parsing.
