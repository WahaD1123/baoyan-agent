import json
import os

import httpx

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


class DashScopeProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = (settings.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        self.model = settings.llm_model or "qwen-plus"
        self.fallback = MockLLMProvider()

    def generate(self, prompt: str, task: str = "general") -> str:
        if not self.api_key:
            return self.fallback.generate(prompt, task)
        system_prompts = {
            "knowledge": "你是CS保研资料知识库助手。只基于给定资料回答，并尽量列出来源。",
            "advisor": "你是CS保研导师匹配助手。输出研究方向、匹配理由、风险点和联系建议。",
            "extract": "你是信息抽取助手。请用清晰中文总结，并尽量保留关键字段。",
            "critic": "你是审稿助手。检查输出是否具体、是否有依据、是否有编造风险。",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompts.get(task, "你是一个严谨的CS保研申请助手。")},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            fallback = self.fallback.generate(prompt, task)
            return f"{fallback}\n\n[DashScope fallback: {exc.__class__.__name__}]"


def get_llm_provider() -> MockLLMProvider | DashScopeProvider:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return MockLLMProvider()
    settings = get_settings()
    if settings.llm_provider.lower() == "dashscope":
        return DashScopeProvider()
    return MockLLMProvider()
