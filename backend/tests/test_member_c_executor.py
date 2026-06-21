import json
from types import SimpleNamespace

from app.agents import CriticAgent, InterviewAgent, MaterialAgent
from app.models import Advisor, StudentProfile
from app.services.member_c_mcp import MemberCMCPClient
from app.tools.member_c_tools import dispatch_local_tool
from app.workflows.capabilities import build_member_c_registry
from app.workflows import member_c_executor as member_c_workflow
from app.workflows.member_c_executor import MemberCTask, MemberCWorkflowExecutor
from app.workflows.planner import TaskPlanner


class ScriptedLLM:
    def __init__(
        self,
        critic_passed: bool,
        *,
        suggestions_when_passed: bool = False,
    ) -> None:
        self.critic_passed = critic_passed
        self.suggestions_when_passed = suggestions_when_passed
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, task: str = "general") -> str:
        self.calls.append((task, prompt))
        if task == "workflow_planner":
            return json.dumps(
                {
                    "goal": "generate_advisor_email",
                    "steps": [
                        {"kind": "tool", "capability": "profile.build_context"},
                        {"kind": "tool", "capability": "advisor.get_context"},
                        {"kind": "tool", "capability": "knowledge.search"},
                        {"kind": "agent", "capability": "material.generate"},
                        {"kind": "agent", "capability": "critic.review"},
                        {
                            "kind": "agent",
                            "capability": "material.revise",
                            "condition": "critic_failed",
                        },
                    ],
                }
            )
        if task == "critic_structured":
            critic_call_count = sum(
                called_task == "critic_structured"
                for called_task, _called_prompt in self.calls
            )
            passed = self.critic_passed if critic_call_count == 1 else True
            return json.dumps(
                {
                    "passed": passed,
                    "score": 88 if passed else 62,
                    "summary": "final grounded" if critic_call_count > 1 else ("grounded" if passed else "revision required"),
                    "issues": [] if passed else ["one unsupported phrase"],
                    "suggestions": (
                        ["polish an optional sentence"]
                        if passed and self.suggestions_when_passed
                        else ([] if passed else ["remove the phrase"])
                    ),
                    "user_inputs": [] if passed else ["请补充真实项目指标"],
                }
            )
        if "revision_mode=true" in prompt:
            return "revised grounded email"
        return "first draft email"


class RevisionFallbackLLM(ScriptedLLM):
    def __init__(self) -> None:
        super().__init__(critic_passed=False)
        self.last_call = None

    def generate(self, prompt: str, task: str = "general") -> str:
        output = super().generate(prompt, task)
        if "revision_mode=true" in prompt:
            self.last_call = SimpleNamespace(
                source="fallback",
                model_name="qwen3.6-flash",
                fallback_reason="APITimeoutError",
            )
            return "generic mock replacement"
        self.last_call = None
        return output


def _task() -> MemberCTask:
    return MemberCTask(
        goal="generate_advisor_email",
        workflow_type="material_email",
        title="Advisor Contact Email",
        profile=StudentProfile(
            name="Alice",
            research_interests=["agent systems"],
            projects=["Built a multi-agent application assistant"],
        ),
        advisor=Advisor(
            name="Prof. Wang",
            university="Target University",
            research_areas=["agent systems"],
        ),
        request_details={"purpose": "summer camp application"},
        generation_rules=["Write in Chinese", "Use only supplied evidence"],
    )


def _executor(llm: ScriptedLLM) -> MemberCWorkflowExecutor:
    return MemberCWorkflowExecutor(
        planner=TaskPlanner(build_member_c_registry(), llm),
        mcp_client=MemberCMCPClient(remote_caller=dispatch_local_tool),
        material_agent=MaterialAgent(llm=llm),
        interview_agent=InterviewAgent(llm=llm),
        critic_agent=CriticAgent(llm=llm),
    )


def test_executor_runs_mcp_generate_critic_and_one_revision() -> None:
    llm = ScriptedLLM(critic_passed=False)

    workflow = _executor(llm).execute(_task())

    assert workflow.plan_source == "planner"
    assert workflow.status == "completed"
    assert workflow.final_result.startswith("## Advisor Contact Email\nrevised grounded email")
    capabilities = [step.capability for step in workflow.steps]
    assert capabilities == [
        "workflow.plan",
        "profile.build_context",
        "advisor.get_context",
        "knowledge.search",
        "material.generate",
        "critic.review",
        "material.revise",
    ]
    assert workflow.steps[1].tool_call is not None
    assert workflow.steps[1].tool_call.transport == "mcp"
    assert sum(task == "material" for task, _prompt in llm.calls) == 2
    assert sum(task == "critic_structured" for task, _prompt in llm.calls) == 1
    assert "请补充真实项目指标" in workflow.final_result
    assert "## 建议" in workflow.final_result
    assert "自动优化" not in workflow.final_result
    assert "remove the phrase" not in workflow.final_result
    assert "revision required" not in workflow.final_result


def test_executor_skips_conditional_revision_when_critic_passes() -> None:
    llm = ScriptedLLM(critic_passed=True)

    workflow = _executor(llm).execute(_task())

    revision = next(step for step in workflow.steps if step.capability == "material.revise")
    assert revision.status == "skipped"
    assert "Critic passed" in revision.decision_reason
    assert "first draft email" in workflow.final_result
    assert sum(task == "material" for task, _prompt in llm.calls) == 1
    assert sum(task == "critic_structured" for task, _prompt in llm.calls) == 1


def test_executor_does_not_rewrite_passed_draft_for_optional_suggestions() -> None:
    llm = ScriptedLLM(critic_passed=True, suggestions_when_passed=True)

    workflow = _executor(llm).execute(_task())

    revision = next(step for step in workflow.steps if step.capability == "material.revise")
    assert revision.status == "skipped"
    assert "first draft email" in workflow.final_result
    assert "## 质量检查" not in workflow.final_result
    assert "## 建议" not in workflow.final_result
    assert sum(task == "material" for task, _prompt in llm.calls) == 1


def test_executor_keeps_real_draft_when_revision_falls_back() -> None:
    llm = RevisionFallbackLLM()

    workflow = _executor(llm).execute(_task())

    assert "first draft email" in workflow.final_result
    assert "generic mock replacement" not in workflow.final_result
    revision = next(step for step in workflow.steps if step.capability == "material.revise")
    assert "kept the original draft" in revision.decision_reason


def test_critic_requests_chinese_and_formats_readable_markdown() -> None:
    llm = ScriptedLLM(critic_passed=False)

    result, decision = CriticAgent(llm=llm).review_member_c(
        content="draft",
        goal="generate_advisor_email",
        evidence_summary="grounded evidence",
        requirements=["只生成邮件正文，不要求提供附件内容"],
    )

    critic_prompt = next(prompt for task, prompt in llm.calls if task == "critic_structured")
    assert "简体中文" in critic_prompt
    assert "不得建议模型自行编造" in critic_prompt
    assert "只生成邮件正文，不要求提供附件内容" in critic_prompt
    assert decision.passed is False
    assert result.output == (
        "**审查结论：** 需要修改\n\n"
        "**评分：** 62 / 100\n\n"
        "### 总结\n\nrevision required\n\n"
        "### 主要问题\n\n1. one unsupported phrase\n\n"
        "### 修改建议\n\n1. remove the phrase"
        "\n\n### 需要用户补充\n\n1. 请补充真实项目指标"
    )


def test_resume_output_is_normalized_to_markdown_bullets() -> None:
    raw = (
        "主导开发多智能体保研助手，完成工作流编排。 "
        "搭建课程推荐系统，完成离线评估。 "
        "获蓝桥杯省级二等奖。 "
        "以第二作者发表会议论文。"
    )

    formatted = member_c_workflow._normalize_generated_content(
        raw,
        "generate_resume_highlights",
    )

    assert formatted.splitlines() == [
        "- 主导开发多智能体保研助手，完成工作流编排。",
        "- 搭建课程推荐系统，完成离线评估。",
        "- 获蓝桥杯省级二等奖。",
        "- 以第二作者发表会议论文。",
    ]


def test_interview_output_is_normalized_to_headings_and_numbered_questions() -> None:
    raw = (
        "项目经历\n"
        "考察重点：项目架构与个人贡献。\n\n"
        "请介绍多智能体保研助手的整体架构？\n"
        "你如何验证系统效果？\n"
        "CS基础\n"
        "考察重点：数据结构与操作系统。 3. 请解释哈希表冲突？ 4. 如何保证共享数据一致性？"
    )

    formatted = member_c_workflow._normalize_generated_content(
        raw,
        "generate_interview",
    )

    assert "### 项目经历" in formatted
    assert "> 考察重点：项目架构与个人贡献。" in formatted
    assert "1. 请介绍多智能体保研助手的整体架构？" in formatted
    assert "2. 你如何验证系统效果？" in formatted
    assert "### CS基础" in formatted
    assert "3. 请解释哈希表冲突？" in formatted
    assert "4. 如何保证共享数据一致性？" in formatted


def test_interview_normalization_preserves_decimal_values() -> None:
    raw = (
        "科研\n考察重点：实验分析。\n"
        "论文方法较基线提升 8.6 个百分点，你如何验证结果？\n"
        "复盘\n考察重点：个人基础。\n"
        "你的专业排名前 8.0%，GPA 为 3.82，你如何评价自己的优势？"
    )

    formatted = member_c_workflow._normalize_generated_content(raw, "generate_interview")

    assert "### 科研" in formatted
    assert "### 复盘" in formatted
    assert "8.6 个百分点" in formatted
    assert "前 8.0%" in formatted
    assert "GPA 为 3.82" in formatted


def test_email_normalization_separates_salutation_greeting_and_signature() -> None:
    raw = (
        "尊敬的王老师您好： 我是厦门大学的张三。 "
        "在科研实践中，我负责智能体模块开发。 "
        "随信附上个人简历与成绩单，期待能有机会加入您的团队。 "
        "此致 敬礼！ 张三 zhangsan@example.com 138-0000-0000 2024年X月X日"
    )

    formatted = member_c_workflow._normalize_generated_content(raw, "generate_advisor_email")

    assert formatted.startswith("尊敬的王老师：\n\n您好！\n\n我是厦门大学的张三。")
    assert "\n\n在科研实践中，我负责智能体模块开发。" in formatted
    assert "\n\n随信附上个人简历与成绩单" in formatted
    assert "此致\n\n敬礼！" in formatted
    assert "学生：张三\n\n邮箱：zhangsan@example.com" in formatted
    assert "电话：138-0000-0000\n\n日期：2024年X月X日" in formatted
