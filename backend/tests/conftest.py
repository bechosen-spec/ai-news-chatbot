import hashlib
import json

import joblib
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from ml.src.modeling import build_pipeline


@pytest.fixture
def client(tmp_path):
    texts = [
        "markets company finance stocks",
        "film actor music awards",
        "parliament election minister law",
        "football team match goal",
        "computer software internet chip",
    ] * 3
    labels = ["business", "entertainment", "politics", "sport", "tech"] * 3
    model = build_pipeline("svm", {"C": 1.0}).fit(texts, labels)
    model_path = tmp_path / "selected_model.joblib"
    metadata_path = tmp_path / "metadata.json"
    joblib.dump(model, model_path)
    metadata = {
        "model_id": "test-model",
        "model_version": "test",
        "algorithm": "LinearSVC",
        "training_dataset": "test fixture",
        "supported_categories": sorted(set(labels)),
        "artifact_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "score_semantics": "decision_function",
    }
    metadata_path.write_text(json.dumps(metadata))
    app = create_app(
        Settings(model_path=model_path, model_metadata_path=metadata_path, database_url="sqlite://")
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
