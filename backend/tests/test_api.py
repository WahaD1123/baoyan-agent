from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
