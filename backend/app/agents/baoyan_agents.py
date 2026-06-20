import json
import re

from app.agents.base import BaseAgent
from app.models import AgentResult, CriticDecision


class ProfileAgent(BaseAgent):
    name = "ProfileAgent"
    task = "profile"


class SchoolRecommendAgent(BaseAgent):
    name = "SchoolRecommendAgent"
    task = "school"


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    task = "planner"


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"
    task = "knowledge"


class AdvisorMatchAgent(BaseAgent):
    name = "AdvisorMatchAgent"
    task = "advisor"


class MaterialAgent(BaseAgent):
    name = "MaterialAgent"
    task = "material"

    def generate(self, prompt: str, references: list[str] | None = None) -> AgentResult:
        return self._run_task(prompt, "material", references)

    def revise(
        self,
        draft: str,
        decision: CriticDecision,
        grounded_context: str,
        references: list[str] | None = None,
    ) -> AgentResult:
        prompt = (
            "revision_mode=true\n"
            "Revise the application material once. Preserve supported facts, remove unsupported "
            "claims, and follow the critic suggestions. Return only the revised material.\n"
            f"critic={decision.model_dump_json()}\n"
            f"grounded_context={grounded_context}\n"
            f"draft={draft}"
        )
        return self._run_task(prompt, "material", references)


class InterviewAgent(BaseAgent):
    name = "InterviewAgent"
    task = "interview"

    def generate(self, prompt: str, references: list[str] | None = None) -> AgentResult:
        return self._run_task(prompt, "interview", references)

    def revise(
        self,
        draft: str,
        decision: CriticDecision,
        grounded_context: str,
        references: list[str] | None = None,
    ) -> AgentResult:
        prompt = (
            "revision_mode=true\n"
            "Revise the mock interview once. Keep the requested categories, improve evidence "
            "coverage, and follow the critic suggestions. Return only the revised questions.\n"
            f"critic={decision.model_dump_json()}\n"
            f"grounded_context={grounded_context}\n"
            f"draft={draft}"
        )
        return self._run_task(prompt, "interview", references)


class CriticAgent(BaseAgent):
    name = "CriticAgent"
    task = "critic"

    def review_member_c(
        self,
        content: str,
        goal: str,
        evidence_summary: str,
        references: list[str] | None = None,
    ) -> tuple[AgentResult, CriticDecision]:
        prompt = (
            "Review this Member C output for groundedness, completeness, relevance, and format. "
            "Reject unsupported facts or missing core sections. Return one JSON object only with "
            "passed (boolean), score (0-100), summary, issues (max 3), and suggestions (max 3).\n"
            f"goal={goal}\n"
            f"evidence={evidence_summary}\n"
            f"content={content}"
        )
        result = self._run_task(prompt, "critic_structured", references)
        try:
            decision = CriticDecision.model_validate(_extract_json_object(result.output))
        except Exception as exc:
            decision = CriticDecision(
                passed=False,
                score=50,
                summary=f"Critic response could not be validated: {type(exc).__name__}",
                issues=["The structured critic response was invalid."],
                suggestions=["Rewrite once using only the collected evidence."],
            )
        result.output = _format_critic_decision(decision)
        return result, decision


def _extract_json_object(raw: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("Critic did not return JSON")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise TypeError("Critic JSON must be an object")
    return parsed


def _format_critic_decision(decision: CriticDecision) -> str:
    lines = [
        f"Decision: {'PASS' if decision.passed else 'REVISE'}",
        f"Score: {decision.score}",
        f"Summary: {decision.summary}",
    ]
    if decision.issues:
        lines.append("Issues: " + "; ".join(decision.issues))
    if decision.suggestions:
        lines.append("Suggestions: " + "; ".join(decision.suggestions))
    return "\n".join(lines)
