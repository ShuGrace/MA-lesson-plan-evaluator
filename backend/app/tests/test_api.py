import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Lesson Plan Evaluator API"

def test_create_evaluation():
    payload = {
        "lesson_plan_text": "Sample lesson plan",
        "lesson_plan_title": "Math Lesson",
        "grade_level": "Grade 5",
        "subject_area": "Mathematics"
    }
    response = client.post("/api/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "evaluation_id" in data

def test_get_all_evaluations():
    response = client.get("/api/evaluations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_evaluate_lesson_mock():
    payload = {"text": "This is a test lesson plan"}
    response = client.post("/api/evaluate/lesson", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "agent_responses" in data
    assert any(agent["agent"] == "DeepSeek" for agent in data["agent_responses"])
