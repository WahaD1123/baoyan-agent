from fastapi.testclient import TestClient

from app.main import app
from app.models import Document
from app.services.library_router import route_documents_by_library
from app.tools.document_processing import prepare_document
from app.tools.retrieval import hybrid_retrieve


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sample_profile_contains_grounded_member_c_evidence() -> None:
    profile = client.get("/api/profile").json()
    evidence = " ".join(
        [
            *profile["projects"],
            *profile["competitions"],
            *profile["publications"],
            profile["notes"],
        ]
    )

    assert "FastAPI" in evidence
    assert "MCP" in evidence
    assert "省级二等奖" in evidence
    assert "第二作者" in evidence
    assert "实验" in evidence


def test_mock_planning_workflow() -> None:
    profile = client.get("/api/profile").json()
    response = client.post("/api/planning/generate", json={"profile": profile})
    assert response.status_code == 200
    data = response.json()
    assert data["workflow"]["workflow_type"] == "planning"
    assert data["recommendations"]
    assert data["analysis"]["overall_score"] >= 0
    assert data["timeline"]
    assert data["evidence"] is not None
    school_names = [item["school_name"] for item in data["recommendations"]]
    assert len(school_names) == len(set(school_names))


def test_profile_analysis() -> None:
    profile = client.get("/api/profile").json()
    response = client.post("/api/profile/analyze", json=profile)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] >= 0
    assert "strengths" in data


def test_member_b_text_ingest_query_and_match() -> None:
    payload = {
        "title": "Test CS Summer Camp Notice",
        "doc_type": "notice",
        "source_type": "text",
        "source": "test",
        "content": "The camp requires resume, transcript, ranking certificate, and professional interview.",
    }
    ingest = client.post("/api/knowledge/documents/text", json=payload)
    assert ingest.status_code == 200
    assert ingest.json()["document"]["chunks"]

    query = client.post("/api/knowledge/query", json={"question": "What materials are required?", "top_k": 3})
    assert query.status_code == 200
    assert query.json()["chunks"]
    assert query.json()["workflow"]["workflow_type"] == "knowledge"

    profile = client.get("/api/profile").json()
    match = client.post("/api/knowledge/advisors/match", json={"profile": profile, "top_k": 2})
    assert match.status_code == 200
    assert match.json()["matches"]


def test_member_b_full_analysis_and_advisor_extraction() -> None:
    notice = prepare_document(
        Document(
            title="Example University CS Summer Camp",
            doc_type="notice",
            source_type="text",
            content=(
                "Example University summer camp requires resume, transcript, ranking certificate, "
                "research statement, and professional interview. Deadline: 2026-06-30."
            ),
        )
    )
    assert notice.analysis["status"] == "completed"
    assert notice.analysis["mode"] == "full_document_analysis"
    assert "resume" in notice.analysis["requirements"]

    advisor = prepare_document(
        Document(
            title="Zhi-Hua Zhou's Homepage",
            doc_type="advisor",
            source_type="url",
            source="http://cs.nju.edu.cn/zhouzh/",
            content=(
                "Professor Zhi-Hua Zhou is with the Department of Computer Science and Technology, "
                "Nanjing University. His research interests include machine learning, data mining, "
                "artificial intelligence and pattern recognition."
            ),
        )
    )
    assert advisor.extracted["name"] == "Zhi-Hua Zhou"
    assert "Nanjing University" in advisor.extracted["university"]
    assert "machine learning" in advisor.extracted["research_areas"]
    assert "version" not in advisor.extracted["research_areas"]

    xmu_advisor = prepare_document(
        Document(
            title="纪荣嵘-厦门大学信息学院",
            doc_type="advisor",
            source_type="url",
            source="https://informatics.xmu.edu.cn/info/1033/177381.htm",
            content=(
                "杰出人才\n"
                "纪荣嵘\n"
                "国家杰青、国家优青、南强特聘教授；博士生导师\n"
                "厦门大学校长助理、人工智能研究院负责人\n"
                "研究方向：计算机视觉、机器学习\n"
                "主要研究方向为计算机视觉、多媒体技术和机器学习。"
            ),
        )
    )
    assert xmu_advisor.extracted["name"] == "纪荣嵘"
    assert xmu_advisor.extracted["university"] == "厦门大学"
    assert "计算机视觉" in xmu_advisor.extracted["research_areas"]


def test_member_b_direct_phd_question_prefers_experience_posts() -> None:
    experience = prepare_document(
        Document(
            title="保研经验贴",
            doc_type="experience",
            source_type="text",
            content="尽早想清楚自己要不要直博，和家人沟通好，避免拿到直博 offer 后又放弃。",
        )
    )
    advisor = prepare_document(
        Document(
            title="某教授主页",
            doc_type="advisor",
            source_type="url",
            content="教授，博士生导师，发表多篇论文，长期招收博士生和硕士生。",
        )
    )
    chunks = hybrid_retrieve([advisor, experience], "要不要直博", top_k=2)
    assert chunks
    assert chunks[0].document_title == "保研经验贴"

    selected = route_documents_by_library("要不要直博", [advisor, experience], limit=2)
    assert selected
    assert selected[0].title == "保研经验贴"


def _assert_member_c_workflow(payload: dict, workflow_type: str, content_label: str) -> None:
    assert content_label in payload["content"]
    assert "质量检查" in payload["content"]
    workflow = payload["workflow"]
    assert workflow["workflow_type"] == workflow_type
    assert len(workflow["steps"]) >= 2
    assert any("Critic" in step["name"] or "审查" in step["name"] for step in workflow["steps"])


def test_member_c_generates_advisor_email_with_critic_workflow() -> None:
    profile = client.get("/api/profile").json()
    advisor = client.get("/api/knowledge/advisors").json()[0]

    response = client.post(
        "/api/materials/email",
        json={"profile": profile, "advisor": advisor, "purpose": "summer camp application"},
    )

    assert response.status_code == 200
    _assert_member_c_workflow(response.json(), "material_email", "导师联系邮件")


def test_member_c_generates_resume_highlights_with_critic_workflow() -> None:
    profile = client.get("/api/profile").json()

    response = client.post(
        "/api/materials/resume-highlights",
        json={"profile": profile, "target_direction": "AI systems"},
    )

    assert response.status_code == 200
    _assert_member_c_workflow(response.json(), "resume_highlights", "简历亮点")


def test_member_c_generates_statement_with_critic_workflow() -> None:
    profile = client.get("/api/profile").json()

    response = client.post(
        "/api/materials/statement",
        json={
            "profile": profile,
            "target_school": "Shanghai Jiao Tong University",
            "direction": "AI systems",
            "tone": "concise",
        },
    )

    assert response.status_code == 200
    _assert_member_c_workflow(response.json(), "personal_statement", "个人陈述")


def test_member_c_generates_categorized_interview_with_critic_workflow() -> None:
    profile = client.get("/api/profile").json()

    response = client.post(
        "/api/interview/mock",
        json={"profile": profile, "target_school": "SJTU", "direction": "AI"},
    )

    assert response.status_code == 200
    _assert_member_c_workflow(response.json(), "interview", "模拟面试题")
    assert "项目追问" in response.json()["content"]


def _legacy_member_c_prompts_bound_generated_output() -> None:
    profile = client.get("/api/profile").json()
    advisor = client.get("/api/knowledge/advisors").json()[0]
    cases = [
        (
            "/api/materials/email",
            {"profile": profile, "advisor": advisor, "purpose": "summer camp application"},
            "正文控制在 600 字以内",
        ),
        (
            "/api/materials/resume-highlights",
            {"profile": profile, "target_direction": "AI systems"},
            "每条不超过 100 字",
        ),
        (
            "/api/materials/statement",
            {"profile": profile, "target_school": "SJTU", "direction": "AI", "tone": "concise"},
            "正文控制在 700 字以内",
        ),
        (
            "/api/interview/mock",
            {"profile": profile, "target_school": "SJTU", "direction": "AI"},
            "总题量控制在 15 题以内",
        ),
    ]

    for path, payload, generation_rule in cases:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        steps = response.json()["workflow"]["steps"]
        assert generation_rule in steps[0]["agent_result"]["input_summary"]
        assert "不要使用 Markdown 表格" in steps[1]["agent_result"]["input_summary"]
        assert "400 字以内" in steps[1]["agent_result"]["input_summary"]


def test_member_c_dynamic_steps_keep_generation_bounds() -> None:
    profile = client.get("/api/profile").json()
    advisor = client.get("/api/knowledge/advisors").json()[0]
    cases = [
        (
            "/api/materials/email",
            {"profile": profile, "advisor": advisor, "purpose": "summer camp application"},
            "within 600 Chinese characters",
        ),
        (
            "/api/materials/resume-highlights",
            {"profile": profile, "target_direction": "AI systems"},
            "at most 100 Chinese characters",
        ),
        (
            "/api/materials/statement",
            {"profile": profile, "target_school": "SJTU", "direction": "AI", "tone": "concise"},
            "within 700 Chinese characters",
        ),
        (
            "/api/interview/mock",
            {"profile": profile, "target_school": "SJTU", "direction": "AI"},
            "at most 15 questions",
        ),
    ]

    for path, payload, generation_rule in cases:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        workflow = response.json()["workflow"]
        generation = next(
            step for step in workflow["steps"]
            if step["capability"].endswith(".generate")
        )
        critic = next(
            step for step in workflow["steps"]
            if step["capability"] == "critic.review"
        )
        assert generation_rule in generation["agent_result"]["input_summary"]
        critic_prompt = critic["agent_result"]["input_summary"]
        assert "JSON" in critic_prompt
        assert "passed" in critic_prompt
        assert "简体中文" in critic_prompt
        assert workflow["plan_source"] in {"planner", "fallback"}
        assert generation["model_name"]
        assert critic["model_name"]
