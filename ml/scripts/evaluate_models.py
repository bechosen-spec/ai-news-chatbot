#!/usr/bin/env python3
"""Verify that preserved experiment outputs and the selected artifact agree."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[2]


def main() -> dict[str, float]:
    artifact = ROOT / "ml/artifacts/selected_model.joblib"
    metadata = json.loads((ROOT / "ml/artifacts/model_metadata.json").read_text())
    actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if actual_hash != metadata["artifact_sha256"]:
        raise RuntimeError("Selected model hash does not match its metadata")
    test = pd.read_csv(ROOT / "ml/data/processed/test.csv")
    model = joblib.load(artifact)  # trusted artifact produced by this repository
    predictions = model.predict(test["text"])
    result = {
        "accuracy": float(accuracy_score(test["label"], predictions)),
        "macro_f1": float(f1_score(test["label"], predictions, average="macro")),
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
