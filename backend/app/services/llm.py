import json
import os
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("baoyan-agent.llm")

class MockLLMProvider:
    """Deterministic LLM substitute for demos and tests."""

    def generate(self, prompt: str, task: str = "general") -> str:
        compact = " ".join(prompt.split())
        if task == "workflow_planner":
            return self._workflow_plan_reply(prompt)
        if task == "critic_structured":
            return json.dumps(
                {
                    "passed": False,
                    "score": 72,
                    "summary": "演示模式的质量检查建议进行一次有依据的修改。",
                    "issues": ["部分表述需要进一步核对证据来源。"],
                    "suggestions": ["仅保留工具上下文中能够验证的事实。"],
                }
            )
        if task == "profile":
            return self._profile_reply(compact)
        if task == "school":
            return self._school_reply(compact)
        if task == "planner":
            return self._planner_reply(compact)
        if task == "knowledge":
            return "系统已结合命中的资料片段生成回答，重点关注截止时间、材料要求、研究方向和考核形式。"
        if task == "advisor":
            return "系统已根据研究兴趣、项目背景和导师方向生成匹配建议，并提示联系重点。"
        if task == "material":
            if "material_kind=advisor_email" in prompt:
                return (
                    "尊敬的老师您好：\n"
                    "我是示例同学，来自厦门大学计算机科学与技术专业，专业排名 Top 8%，目前关注机器学习与智能系统方向。\n"
                    "我在多智能体保研助手和课程推荐系统项目中承担需求拆解、系统实现和效果验证工作，希望进一步了解您团队在相关方向的研究。\n"
                    "随信附上简历与项目摘要，若您方便，期待获得进一步交流机会。\n"
                    "祝好！"
                )
            if "material_kind=resume_highlights" in prompt:
                return (
                    "1. 围绕多智能体保研助手完成任务拆解、后端 workflow 与前端展示联调，体现 AI 应用系统落地能力。\n"
                    "2. 在课程推荐系统中整理用户画像与推荐逻辑，积累数据建模、接口设计和结果解释经验。\n"
                    "3. 结合蓝桥杯训练经历强化算法与编码基础，可支撑夏令营机考和项目追问。\n"
                    "4. 研究兴趣集中在机器学习与智能系统，和 AI systems / RAG 方向具备延展空间。"
                )
            if "material_kind=personal_statement" in prompt:
                return (
                    "我对人工智能系统方向的兴趣来自课程项目和多智能体应用实践。"
                    "在多智能体保研助手项目中，我尝试把用户画像、资料检索、规划生成和材料审查连接成可解释的 workflow，"
                    "这让我意识到模型能力只有和可靠的软件架构结合，才能稳定服务真实任务。"
                    "未来我希望继续围绕智能系统、检索增强生成和 Agent 协同开展学习与研究。"
                )
            return "申请材料初稿：请结合学生画像补充具体项目、数据、结果和申请方向。"
        if task == "interview":
            return (
                "项目追问：\n"
                "1. 请介绍多智能体保研助手的整体架构，以及你负责的模块。\n"
                "2. 如果导师质疑系统只是套壳问答，你会如何说明 workflow 和中间件价值？\n\n"
                "专业基础：\n"
                "1. 请解释进程和线程的区别。\n"
                "2. 请说明哈希表冲突处理方式，以及查询复杂度的条件。\n\n"
                "科研方向：\n"
                "1. 你如何理解 RAG 中检索质量对生成质量的影响？\n"
                "2. 多 Agent 系统如何避免互相传递错误信息？\n\n"
                "英文面试：\n"
                "1. Please introduce one project you are proud of.\n"
                "2. Why are you interested in AI systems?\n\n"
                "复盘建议：回答时先讲问题背景，再讲个人贡献，最后讲可验证结果和改进空间。"
            )
        if task == "critic":
            return (
                "优势：结构完整，能对应学生画像和目标方向。\n"
                "缺少证据：建议补充项目规模、技术栈、实验结果或排名证明。\n"
                "风险点：避免使用“非常优秀”“极大提升”等无法证明的表达。\n"
                "改写建议：每段至少保留一个可核验事实，并把经历和申请方向明确连接。"
            )
        if task == "extract":
            return "系统已提取资料中的学校、材料要求、考核形式和其他关键字段。"
        return f"系统已完成 {task} 任务。"

    def _workflow_plan_reply(self, prompt: str) -> str:
        goal = "generate_advisor_email"
        for candidate in (
            "generate_advisor_email",
            "generate_resume_highlights",
            "generate_statement",
            "generate_interview",
        ):
            if f"goal={candidate}" in prompt:
                goal = candidate
                break

        steps: list[dict[str, str]] = [
            {"kind": "tool", "capability": "profile.build_context"}
        ]
        lowered = prompt.lower()
        if goal == "generate_advisor_email" and '"has_advisor": true' in lowered:
            steps.append({"kind": "tool", "capability": "advisor.get_context"})
        if goal == "generate_interview":
            if '"has_knowledge": true' in lowered:
                steps.append({"kind": "tool", "capability": "interview.retrieve_evidence"})
            generate_capability = "interview.generate"
            revise_capability = "interview.revise"
        else:
            if '"has_knowledge": true' in lowered:
                steps.append({"kind": "tool", "capability": "knowledge.search"})
            generate_capability = "material.generate"
            revise_capability = "material.revise"
        steps.extend(
            [
                {"kind": "agent", "capability": generate_capability},
                {"kind": "agent", "capability": "critic.review"},
                {
                    "kind": "agent",
                    "capability": revise_capability,
                    "condition": "critic_failed",
                },
            ]
        )
        return json.dumps({"goal": goal, "steps": steps})

    def _profile_reply(self, prompt: str) -> str:
        payload = {
            "strengths": [
                "专业排名和 GPA 具备继续冲击强校的基础。",
                "项目经历可以支撑简历主线和面试表达。",
            ],
            "weaknesses": [
                "科研证明如果不够具体，强校场景下说服力会下降。"
            ],
            "suggestions": [
                "把最相关项目整理成可量化的技术亮点。",
                "尽快形成统一材料包，并按目标院校补细节。",
            ],
            "summary": "当前更适合走冲刺、稳妥、保底并行的申请节奏，先补齐可验证材料，再推进选校和联系。",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _school_reply(self, prompt: str) -> str:
        reasons = []
        risks = []
        todo = []
        if "材料要求" in prompt and "暂无" not in prompt:
            reasons.append("该校已有通知资料支撑，推荐依据更具体。")
            todo.append("优先根据通知中的材料要求整理申请文件。")
        if "机考" in prompt or "coding test" in prompt.lower():
            risks.append("该校可能包含机考或编码测试，需要提前练习。")
            todo.append("尽快安排上机练习和项目追问训练。")
        if "论文" in prompt or "publication" in prompt.lower():
            reasons.append("已有科研或投稿经历，可以作为申请亮点。")
        if "冲刺" in prompt or "challenge" in prompt.lower():
            risks.append("作为冲刺项，需要补强科研深度和表达细节。")
        if not reasons:
            reasons.append("这所学校与当前画像存在基础匹配。")
        if not risks:
            risks.append("当前最大的风险在于材料细节和科研深度仍可继续加强。")
        if not todo:
            todo.append("优先准备简历、项目摘要和个人陈述。")
        payload = {
            "reasons": reasons[:3],
            "risks": risks[:3],
            "todo": todo[:3],
            "insight": "建议先确认该校通知要求，再围绕最相关的项目和科研经历进行针对性准备。",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _planner_reply(self, prompt: str) -> str:
        lines = []
        if "材料包" in prompt:
            lines.append("优先完成统一材料包，后续所有申请动作都会更顺畅。")
        if "导师" in prompt:
            lines.append("在材料准备到位后再联系导师，能显著提高沟通质量。")
        if "机考" in prompt or "面试" in prompt:
            lines.append("最后一阶段应集中做机考、项目追问和英文自我介绍训练。")
        return " ".join(lines[:2]) or "系统已根据推荐结果生成分周准备节奏。"


class DashScopeProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = (settings.llm_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        self.model = settings.llm_model or "qwen-plus"
        self.critic_model = settings.llm_critic_model
        self.critic_max_tokens = settings.llm_critic_max_tokens
        self.planner_model = settings.llm_planner_model
        self.planner_max_tokens = settings.llm_planner_max_tokens
        self.member_c_fallback_model = settings.llm_member_c_fallback_model
        self.member_c_max_tokens = settings.llm_member_c_max_tokens
        self.fallback = MockLLMProvider()

    def generate(self, prompt: str, task: str = "general") -> str:
        if not self.api_key:
            logger.info("DashScope disabled for task=%s: missing API key, using mock provider", task)
            return self.fallback.generate(prompt, task)
        system_prompts = {
            "knowledge": "你是 CS 保研资料知识库助手。只基于给定资料回答，并明确指出引用来源。",
            "advisor": "你是 CS 保研导师匹配助手。输出研究方向、匹配理由、风险点和联系建议。",
            "extract": "你是信息抽取助手。请用清晰中文总结，并尽量保留关键字段。",
            "critic": "你是审查助手。检查输出是否具体、是否有依据、是否有编造风险。",
            "critic_structured": (
                "你是严格的保研申请材料质量检查员。只返回包含 passed、score、summary、"
                "issues 和 suggestions 字段的 JSON；除字段名外，所有文字内容必须使用简体中文。"
            ),
            "workflow_planner": "你是受约束的工作流规划智能体。只能输出符合给定 schema 的 JSON，并且只能选择能力清单中的名称。",
            "school": "你是保研院校规划助手。请基于学生画像和检索证据，给出简短而明确的院校建议。",
            "planner": "你是保研规划助手。请基于推荐院校和准备节奏，给出下一步行动建议。",
            "profile": "你是学生画像分析助手。请概括学业、科研、项目和语言优势，并指出短板。",
            "material": "你是CS保研申请材料助手。请生成具体、克制、有证据的中文申请材料，避免空泛夸大。",
            "interview": "你是CS保研模拟面试官。请按项目、专业基础、科研方向和英文面试分类出题。",
        }
        if task in {"critic", "critic_structured"}:
            primary_model, max_tokens = self.critic_model, self.critic_max_tokens
        elif task == "workflow_planner":
            primary_model, max_tokens = self.planner_model, self.planner_max_tokens
        else:
            primary_model, max_tokens = self.model, None
        if task in {"material", "interview"}:
            max_tokens = self.member_c_max_tokens
        try:
            return self._request(prompt, task, system_prompts, primary_model, max_tokens)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            can_fallback_to_flash = (
                task in {"material", "interview"}
                and self.member_c_fallback_model != primary_model
                and isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout))
            )
            if can_fallback_to_flash:
                logger.warning(
                    "DashScope retry for task=%s: model=%s timed out, falling back to model=%s",
                    task,
                    primary_model,
                    self.member_c_fallback_model,
                )
                try:
                    return self._request(
                        prompt,
                        task,
                        system_prompts,
                        self.member_c_fallback_model,
                        max_tokens,
                    )
                except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as fallback_exc:
                    exc = fallback_exc
            fallback = self.fallback.generate(prompt, task)
            logger.warning("DashScope mock fallback for task=%s due to %s", task, exc.__class__.__name__)
            return f"{fallback}\n\n[DashScope fallback: {exc.__class__.__name__}]"

    def _request(
        self,
        prompt: str,
        task: str,
        system_prompts: dict[str, str],
        model: str,
        max_tokens: int | None,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompts.get(task, "你是一个严谨的 CS 保研申请助手。")},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
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
            content = data["choices"][0]["message"]["content"]
            logger.info("DashScope success for task=%s model=%s chars=%s", task, model, len(content))
            return content


def model_name_for_task(task: str) -> str:
    settings = get_settings()
    if settings.llm_provider.lower() != "dashscope":
        return "mock"
    if task in {"critic", "critic_structured"}:
        return settings.llm_critic_model
    if task == "workflow_planner":
        return settings.llm_planner_model
    return settings.llm_model or "qwen-plus"


def get_llm_provider() -> MockLLMProvider | DashScopeProvider:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return MockLLMProvider()
    settings = get_settings()
    if settings.llm_provider.lower() == "dashscope":
        return DashScopeProvider()
    return MockLLMProvider()
