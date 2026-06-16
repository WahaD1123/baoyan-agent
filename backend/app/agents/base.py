from app.models import AgentResult
from app.services.llm import get_llm_provider


class BaseAgent:
    name = "BaseAgent"
    task = "general"

    def run(self, input_summary: str, references: list[str] | None = None) -> AgentResult:
        llm = get_llm_provider()
        output = llm.generate(input_summary, task=self.task)
        return AgentResult(
            agent_name=self.name,
            input_summary=input_summary,
            output=output,
            references=references or [],
        )
