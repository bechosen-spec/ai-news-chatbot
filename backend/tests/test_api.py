from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_model_info(client):
    response = client.get("/api/v1/ml/model-info")
    assert response.status_code == 200
    assert response.json()["artifact_available"] is True
    assert response.json()["algorithm"] == "LinearSVC"


def test_classification_uses_non_probability_scores(client):
    response = client.post(
        "/api/v1/ml/classify",
        json={"title": "Parliament debates bill", "content": "The minister addressed lawmakers."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["predicted_category"] in {"business", "entertainment", "politics", "sport", "tech"}
    assert body["score_type"] == "decision_function"
    assert body["calibrated_probability"] is False


def test_invalid_and_extra_inputs_are_rejected(client):
    assert client.post("/api/v1/ml/classify", json={"title": "", "content": ""}).status_code == 422
    assert client.post("/api/v1/ml/classify", json={"content": 123}).status_code == 422
    assert (
        client.post("/api/v1/ml/classify", json={"content": "text", "unknown": 1}).status_code
        == 422
    )
    assert client.post("/api/v1/ml/classify", json={"content": "x" * 50_001}).status_code == 422


def test_model_unavailable_returns_503_without_traceback(tmp_path):
    app = create_app(
        Settings(
            model_path=tmp_path / "missing.joblib",
            model_metadata_path=tmp_path / "missing.json",
        )
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/ml/classify", json={"content": "A valid article"})
    assert response.status_code == 503
    assert "Traceback" not in response.text
