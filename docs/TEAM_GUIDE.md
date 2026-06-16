# Team Guide

## Project Goal

本项目是一个面向 CS 保研申请场景的多 Agent 中间件系统。我们要展示的不只是一个问答网页，而是一个能调度用户画像、资料知识库、导师匹配、申请规划、材料生成和模拟面试的 workflow 平台。

## Team Split

成员 A：用户画像与申请规划。

- 页面：用户画像、院校规划。
- API：`/api/profile/*`、`/api/planning/*`。
- Agent：`ProfileAgent`、`SchoolRecommendAgent`、`PlannerAgent`。
- 演示结果：冲稳保推荐、申请时间线、规划理由。

成员 B：知识库与导师匹配。

- 页面：资料知识库、导师匹配。
- API：`/api/knowledge/*`。
- Agent：`KnowledgeAgent`、`AdvisorMatchAgent`。
- 演示结果：资料检索问答、导师方向总结、导师匹配依据。

成员 C：申请材料生成与模拟面试。

- 页面：材料生成、模拟面试。
- API：`/api/materials/*`、`/api/interview/*`。
- Agent：`MaterialAgent`、`InterviewAgent`、`CriticAgent`。
- 演示结果：导师联系邮件、简历亮点、个人陈述片段、模拟面试题。

## Everyone Must Deliver

- At least one page.
- At least one API group.
- At least one Agent or tool.
- At least one sample input and sample output.
- A short demo script for their module.

## Collaboration Rules

- 公共数据模型统一放在 `backend/app/models/schemas.py` 和 `frontend/src/types/domain.ts`。
- 新接口先更新 `docs/API.md`，再写代码。
- Agent 输出必须写入 `WorkflowRun`，方便答辩展示中间件调度过程。
- 业务逻辑尽量走 `workflows/` 和 `agents/`，不要直接塞进 API handler。
- Mock LLM 是默认方案，不能让项目因为没有 API key 跑不起来。
- 提交前至少确认后端 `/api/health` 和前端首页可打开。

## Demo Storyline

1. 填写学生画像。
2. 上传或选择样例院校通知和导师资料。
3. 运行 RAG 问答，解释材料要求。
4. 生成冲稳保院校规划。
5. 匹配导师并展示匹配理由。
6. 生成导师联系邮件。
7. 生成模拟面试题。
8. 打开 Workflow 页面，说明 Agent、工具和中间件如何协同。
