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
    assert data["schools"]


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
