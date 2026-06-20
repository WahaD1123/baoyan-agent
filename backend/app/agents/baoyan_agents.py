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
            "请使用简体中文审查成员 C 的输出，检查事实依据、完整性、相关性和格式。"
            "发现无依据事实或缺少核心部分时应判定为需要修改。只返回一个 JSON 对象，"
            "字段为 passed（布尔值）、score（0-100）、summary、issues（最多 3 项）和 "
            "suggestions（最多 3 项）；summary、issues 和 suggestions 的内容必须使用简体中文。\n"
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
                summary=f"质量检查结果无法解析：{type(exc).__name__}",
                issues=["模型没有返回符合约定格式的结构化审查结果。"],
                suggestions=["仅依据已收集的证据重新生成一次。"],
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
    sections = [
        f"**审查结论：** {'通过' if decision.passed else '需要修改'}",
        f"**评分：** {decision.score} / 100",
        "### 总结",
        decision.summary,
    ]
    if decision.issues:
        sections.extend(
            [
                "### 主要问题",
                "\n".join(
                    f"{index}. {issue}"
                    for index, issue in enumerate(decision.issues, 1)
                ),
            ]
        )
    if decision.suggestions:
        sections.extend(
            [
                "### 修改建议",
                "\n".join(
                    f"{index}. {suggestion}"
                    for index, suggestion in enumerate(decision.suggestions, 1)
                ),
            ]
        )
    return "\n\n".join(sections)
