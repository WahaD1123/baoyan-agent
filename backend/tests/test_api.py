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
