# Member C Materials And Interview Design

## Purpose

Member C owns the application output layer for the CS baoyan assistant. The module turns the profile and advisor context produced by members A and B into application materials and interview practice outputs that can be shown in class.

The implementation must support a stable course demo first. It should run with the local mock provider by default and use DashScope only when local environment variables are configured. Real API keys must stay in a local `.env` file and must never be committed.

## Scope

Member C will implement and demonstrate:

- Advisor contact email.
- Resume highlights.
- Personal statement segment.
- Categorized mock interview questions.
- Critic review for each generated output.

The module will not implement profile editing, school planning, document ingestion, advisor crawling, or advisor matching. Those remain owned by members A and B.

## Recommended Approach

Use a stable demo plus optional real LLM enhancement.

- Mock mode remains the default and returns structured Chinese outputs suitable for screenshots and offline class demos.
- DashScope mode uses the existing OpenAI-compatible provider when `LLM_PROVIDER=dashscope` and `LLM_API_KEY` are configured.
- If DashScope is missing or fails, the provider falls back to mock output so the demo still works.
- All generated outputs are recorded as `WorkflowRun` objects so the team can explain Agent orchestration during the presentation.

## Backend Design

### Data Models

Add request and response models that keep the API explicit:

- `ResumeHighlightRequest`: profile plus optional target direction.
- `StatementRequest`: profile plus optional target school, direction, and tone.
- `InterviewRequest`: keep the existing fields and add optional difficulty or categories only if needed.
- `MaterialResponse`: can remain the shared response shape with `content` and `workflow`.

The first implementation can return formatted text instead of complex nested JSON. This keeps the frontend and demo simple while still preserving workflow details.

### API Endpoints

Member C should expose:

- `POST /api/materials/email`
- `POST /api/materials/resume-highlights`
- `POST /api/materials/statement`
- `POST /api/interview/mock`

Each endpoint should keep the API handler thin:

1. Accept and validate request data.
2. Call the workflow function.
3. Store the workflow in `store`.
4. Return generated content plus workflow.

### Workflow Functions

Add focused workflow functions:

- `run_material_email_workflow(profile, advisor, purpose)`
- `run_resume_highlights_workflow(profile, target_direction)`
- `run_statement_workflow(profile, target_school, direction, tone)`
- `run_interview_workflow(profile, target_school, direction)`

Each workflow should use at least two steps:

1. `MaterialAgent` or `InterviewAgent` generates the draft.
2. `CriticAgent` reviews completeness, specificity, evidence, and application readiness.

The final result should include both the generated material and a visible quality check section.

### Agent Prompts

`MaterialAgent` should produce concrete application text, not generic praise. It should reference:

- Student name, school, major, and ranking.
- Research interests.
- Projects, competitions, and publications.
- Advisor or target direction when available.

`InterviewAgent` should output grouped questions:

- Resume and project questions.
- CS fundamentals.
- Research direction questions.
- English interview questions.
- Follow-up questions based on the student's project.

`CriticAgent` should output:

- Strengths.
- Missing evidence.
- Risk of vague wording or exaggeration.
- Concrete revision suggestions.

## Frontend Design

Keep one Member C page named "材料面试" with two areas.

### Materials Area

Show three actions:

- Generate advisor email.
- Generate resume highlights.
- Generate personal statement.

Each action updates a dedicated output panel. Panels should show generated content and the quality check text returned by the workflow.

### Interview Area

Show one action for mock interview generation. The output should make the categories easy to scan:

- 项目追问
- 专业基础
- 科研方向
- 英文面试
- 复盘建议

The page should use existing app styling and should not introduce a new visual system.

## Data Flow

1. Member A creates or loads `StudentProfile`.
2. Member B provides advisor candidates through the advisor list.
3. Member C reads the current profile and selected first advisor from app state.
4. The frontend calls the Member C endpoint.
5. The backend workflow runs the generating Agent and `CriticAgent`.
6. The workflow is stored in `store.workflows`.
7. The frontend shows generated output and pushes the workflow into the execution record list.

## Error Handling

- Missing advisor for email generation should still produce a general target-advisor email.
- Empty projects or publications should not fail; the output should ask the student to add more evidence.
- DashScope errors should fall back to mock generation through the existing provider.
- API handlers should avoid storing secrets or printing API keys.

## Testing

Backend tests should cover:

- `POST /api/materials/email` returns a material workflow.
- `POST /api/materials/resume-highlights` returns a material workflow.
- `POST /api/materials/statement` returns a material workflow.
- `POST /api/interview/mock` returns an interview workflow.
- Each returned workflow has a generation step and a critic step.

Frontend verification should cover:

- The production build succeeds.
- The materials page exposes all four demo actions.
- Generated outputs update the correct panels.

## Demo Script

1. Open the materials page.
2. Generate an advisor email using the current profile and first matched advisor.
3. Generate resume highlights and explain how the output uses projects and awards.
4. Generate a personal statement segment for AI systems or RAG.
5. Generate mock interview questions.
6. Open the workflow page and show the generation step plus critic review step.
7. Explain that mock mode guarantees a stable demo and DashScope can improve generation quality when configured locally.

## Acceptance Criteria

- Member C owns at least one page, two API groups, three Agents, and four visible demo outputs.
- All Member C outputs are recorded in `WorkflowRun`.
- The module works without a real API key.
- The module can use DashScope when local environment variables are configured.
- No real API key is committed.
- The implementation stays within Member C scope and does not duplicate members A or B work.
