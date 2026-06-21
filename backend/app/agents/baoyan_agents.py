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
        requirements: list[str] | None = None,
        references: list[str] | None = None,
    ) -> AgentResult:
        prompt = (
            "revision_mode=true\n"
            "Revise the application material once. Preserve supported facts, remove unsupported "
            "claims, and follow the critic suggestions. Never add a number, ranking, award level, "
            "technical stack, publication, advisor work, or contact detail that is absent from "
            "grounded_context. If the critic asks for missing evidence, keep a Chinese placeholder "
            "such as 【待补充：真实项目数据】 instead of guessing. Return only the revised material.\n"
            f"automatic_suggestions={json.dumps(decision.suggestions, ensure_ascii=False)}\n"
            f"user_inputs_to_preserve={json.dumps(decision.user_inputs, ensure_ascii=False)}\n"
            f"requirements={json.dumps(requirements or [], ensure_ascii=False)}\n"
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
        requirements: list[str] | None = None,
        references: list[str] | None = None,
    ) -> AgentResult:
        prompt = (
            "revision_mode=true\n"
            "Revise the mock interview once. Keep the requested categories, improve evidence "
            "coverage, and follow the critic suggestions. Do not introduce unsupported facts, "
            "metrics, awards, technical stacks, or advisor work. Return only the revised questions.\n"
            f"automatic_suggestions={json.dumps(decision.suggestions, ensure_ascii=False)}\n"
            f"user_inputs_to_preserve={json.dumps(decision.user_inputs, ensure_ascii=False)}\n"
            f"requirements={json.dumps(requirements or [], ensure_ascii=False)}\n"
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
        requirements: list[str] | None = None,
        references: list[str] | None = None,
    ) -> tuple[AgentResult, CriticDecision]:
        prompt = (
            "请使用简体中文审查成员 C 的输出，检查事实依据、完整性、相关性和格式。"
            "发现无依据事实或缺少核心部分时应判定为需要修改。只返回一个 JSON 对象，"
            "字段为 passed（布尔值）、score（0-100）、summary、issues（最多 3 项）和 "
            "suggestions（最多 3 项）、user_inputs（最多 5 项）。suggestions 只填写模型能依据"
            "现有 evidence 自动落实的修改；user_inputs 只填写必须由用户补充的真实信息。"
            "仅缺少用户信息时可以 passed=true，只有仍需自动重写或存在编造时才 passed=false。"
            "必须严格按照 requirements 判断完整性，不得把要求范围之外的内容判定为缺失核心部分。"
            "user_inputs 只列出正文占位符对应的信息，或当前材料可直接使用所必需但 evidence 中确实缺失的事实；"
            "不得要求用户额外提供与当前任务无关的实习、开源经历、其他项目或可选导师信息。"
            "必须核对个人贡献措辞，不得将 evidence 中的参与或负责夸大为主导、独立完成。"
            "summary、issues、suggestions 和 user_inputs 的内容必须使用简体中文。"
            "缺少真实数据时，建议必须要求用户补充，或保留【待补充：具体数据】占位符，"
            "不得建议模型自行编造数字、名次、奖项、论文、技术栈或导师成果。\n"
            f"goal={goal}\n"
            f"requirements={json.dumps(requirements or [], ensure_ascii=False)}\n"
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
    if decision.user_inputs:
        sections.extend(
            [
                "### 需要用户补充",
                "\n".join(
                    f"{index}. {item}"
                    for index, item in enumerate(decision.user_inputs, 1)
                ),
            ]
        )
    return "\n\n".join(sections)
