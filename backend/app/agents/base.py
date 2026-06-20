from typing import Protocol

from app.models import AgentResult
from app.services.llm import get_llm_provider


class AgentLLM(Protocol):
    def generate(self, prompt: str, task: str = "general") -> str: ...


class BaseAgent:
    name = "BaseAgent"
    task = "general"

    def __init__(self, llm: AgentLLM | None = None) -> None:
        self.llm = llm or get_llm_provider()

    def run(self, input_summary: str, references: list[str] | None = None) -> AgentResult:
        return self._run_task(input_summary, self.task, references)

    def _run_task(
        self,
        input_summary: str,
        task: str,
        references: list[str] | None = None,
    ) -> AgentResult:
        output = self.llm.generate(input_summary, task=task)
        return AgentResult(
            agent_name=self.name,
            input_summary=input_summary,
            output=output,
            references=references or [],
        )
