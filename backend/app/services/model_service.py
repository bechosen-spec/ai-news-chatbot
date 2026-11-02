"""Trusted local artifact loading and inference."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from threading import Lock

import joblib
import numpy as np

from backend.app.core.config import Settings

LOGGER = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    pass


class ModelService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._metadata: dict = {}
        self._lock = Lock()

    @property
    def available(self) -> bool:
        return self.settings.model_path.is_file() and self.settings.model_metadata_path.is_file()

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not self.available:
                raise ModelUnavailableError("Classification model is not available")
            metadata = json.loads(self.settings.model_metadata_path.read_text())
            actual_hash = hashlib.sha256(self.settings.model_path.read_bytes()).hexdigest()
            if actual_hash != metadata.get("artifact_sha256"):
                raise ModelUnavailableError("Classification model integrity check failed")
            try:
                # Joblib artifacts are code-executing formats. Only the locally trained,
                # hash-verified artifact configured by the operator is loaded.
                self._model = joblib.load(self.settings.model_path)
            except Exception as error:
                LOGGER.exception("Unable to load model artifact")
                raise ModelUnavailableError("Classification model could not be loaded") from error
            self._metadata = metadata

    def metadata(self) -> dict:
        if not self.available:
            return {
                "algorithm": "unavailable",
                "model_id": "unavailable",
                "model_version": "unavailable",
                "training_dataset": "unavailable",
                "supported_categories": [],
                "artifact_available": False,
                "score_semantics": "unavailable",
            }
        if not self._metadata:
            self._metadata = json.loads(self.settings.model_metadata_path.read_text())
        return {**self._metadata, "artifact_available": True}

    def classify(self, text: str) -> dict:
        self._load()
        assert self._model is not None
        prediction = str(self._model.predict([text])[0])
        categories = [str(value) for value in self._model.classes_]
        if hasattr(self._model, "decision_function"):
            values = np.asarray(self._model.decision_function([text]))[0]
            score_type = "decision_function"
        elif hasattr(self._model, "predict_proba"):
            values = np.asarray(self._model.predict_proba([text]))[0]
            score_type = "probability"
        else:
            values = np.zeros(len(categories))
            score_type = "decision_function"
        metadata = self.metadata()
        return {
            "predicted_category": prediction,
            "model_id": metadata["model_id"],
            "model_version": metadata["model_version"],
            "scores": [
                {"category": category, "value": float(value)}
                for category, value in zip(categories, values, strict=True)
            ],
            "score_type": score_type,
            "calibrated_probability": score_type == "probability",
            "input_characters": len(text),
        }


def resolve_path(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path
