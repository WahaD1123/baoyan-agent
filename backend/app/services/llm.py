from app.core.config import get_settings


class MockLLMProvider:
    """Deterministic LLM substitute for demos and tests."""

    def generate(self, prompt: str, task: str = "general") -> str:
        prompt_hint = " ".join(prompt.split())[:180]
        templates = {
            "profile": "Profile analysis: the student has a solid CS background and should highlight ranking, research direction, and project ownership.",
            "school": "School recommendation: use a sprint/stable/safe strategy with schools from top CS programs and matching regional preferences.",
            "planner": "Planning timeline: prepare materials first, then contact advisors, then complete interview and coding practice.",
            "knowledge": "Knowledge answer: based on uploaded materials, focus on deadlines, required documents, research fit, and interview format.",
            "advisor": "Advisor match: prioritize overlap between research interests, project experience, and advisor direction.",
            "material": "Generated material: concise, polite, evidence-based, and tailored to the target advisor or program.",
            "interview": "Mock interview: combine resume questions, CS fundamentals, research details, and English self-introduction.",
            "critic": "Critic review: check completeness, specificity, evidence, and whether the output is ready for application use.",
        }
        return f"{templates.get(task, templates['profile'])}\nInput summary: {prompt_hint}"


def get_llm_provider() -> MockLLMProvider:
    settings = get_settings()
    if settings.llm_provider != "mock":
        # Keep the interface stable while the team adds real providers later.
        return MockLLMProvider()
    return MockLLMProvider()
