import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_update_evaluation_not_found():
    # 尝试更新一个不存在的 evaluation
    response = client.put("/api/evaluations/9999", json={"status": "completed"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found"


def test_delete_evaluation_not_found():
    # 尝试删除一个不存在的 evaluation
    response = client.delete("/api/evaluations/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found"


def test_get_statistics():
    # 获取统计信息
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # 可以根据你的 Database.get_statistics 返回值进一步断言
    # 例如 assert "total_evaluations" in data
