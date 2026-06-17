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
            return "系统已生成一版语气稳妥、证据明确的申请材料草稿，可继续人工润色。"
        if task == "interview":
            return "系统已围绕简历项目、专业基础和英文表达生成一组模拟面试题。"
        if task == "critic":
            return "系统检查通过：输出包含核心依据，但仍建议人工确认关键事实和材料细节。"
        if task == "extract":
            return "系统已提取资料中的学校、材料要求、考核形式和其他关键字段。"
        return f"系统已完成 {task} 任务。"

    def _profile_reply(self, prompt: str) -> str:
        pieces = []
        if "rank top" in prompt.lower() or "排名" in prompt:
            pieces.append("画像分析显示该学生具备较好的学业基础。")
        if "gpa" in prompt.lower():
            pieces.append("绩点信息已经纳入竞争力评估。")
        if "interests" in prompt.lower() or "方向" in prompt:
            pieces.append("研究兴趣将作为后续选校和导师匹配的重要依据。")
        return " ".join(pieces) or "画像分析已完成，系统将围绕学业、科研和项目背景生成竞争力判断。"

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
            "school": "你是保研院校规划助手。请基于学生画像和检索证据，给出简短而明确的院校建议。",
            "planner": "你是保研规划助手。请基于推荐院校和准备节奏，给出下一步行动建议。",
            "profile": "你是学生画像分析助手。请概括学业、科研、项目和语言优势，并指出短板。",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompts.get(task, "你是一个严谨的 CS 保研申请助手。")},
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
                content = data["choices"][0]["message"]["content"]
                logger.info("DashScope success for task=%s, chars=%s", task, len(content))
                return content
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            fallback = self.fallback.generate(prompt, task)
            logger.warning("DashScope fallback for task=%s due to %s", task, exc.__class__.__name__)
            return f"{fallback}\n\n[DashScope fallback: {exc.__class__.__name__}]"


def get_llm_provider() -> MockLLMProvider | DashScopeProvider:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return MockLLMProvider()
    settings = get_settings()
    if settings.llm_provider.lower() == "dashscope":
        return DashScopeProvider()
    return MockLLMProvider()
