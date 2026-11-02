#!/usr/bin/env python3
"""Select, refit, evaluate, compare, and serialize Phase 1 classifiers."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from ml.src.datasets import RANDOM_SEED
from ml.src.evaluation import (
    evaluate,
    plot_class_distribution,
    plot_comparisons,
    plot_confusion,
    write_json,
)
from ml.src.modeling import build_pipeline, select_on_validation

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "ml/data/processed"
RESULTS = ROOT / "ml/results"
ARTIFACTS = ROOT / "ml/artifacts"


def _git_sha() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> dict:
    frames = {name: pd.read_csv(DATA / f"{name}.csv") for name in ("train", "validation", "test")}
    labels = sorted(frames["train"]["label"].unique())
    combined_train = pd.concat([frames["train"], frames["validation"]], ignore_index=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    metrics: dict[str, dict] = {}
    searches: dict[str, dict] = {}

    for name in ("svm", "random_forest"):
        search = select_on_validation(
            name,
            frames["train"]["text"],
            frames["train"]["label"],
            frames["validation"]["text"],
            frames["validation"]["label"],
        )
        searches[name] = {
            "selected_parameters": search.parameters,
            "validation_macro_f1": search.validation_macro_f1,
            "candidates": search.candidate_results,
        }
        final_pipeline = build_pipeline(name, search.parameters)
        started = time.perf_counter()
        final_pipeline.fit(combined_train["text"], combined_train["label"])
        training_seconds = time.perf_counter() - started
        artifact = ARTIFACTS / f"{name}_pipeline.joblib"
        joblib.dump(final_pipeline, artifact, compress=3)
        model_metrics = evaluate(
            final_pipeline,
            frames["test"]["text"],
            frames["test"]["label"],
            labels,
            training_seconds,
        )
        model_metrics.update(
            {
                "algorithm": "LinearSVC" if name == "svm" else "RandomForestClassifier",
                "parameters": search.parameters,
                "validation_macro_f1": search.validation_macro_f1,
                "artifact_bytes": artifact.stat().st_size,
                "artifact_megabytes": artifact.stat().st_size / (1024 * 1024),
            }
        )
        metrics[name] = model_metrics
        write_json(RESULTS / "metrics" / f"{name}_metrics.json", model_metrics)
        pd.DataFrame(model_metrics["classification_report"]).transpose().to_csv(
            RESULTS / "metrics/classification_reports" / f"{name}_classification_report.csv"
        )
        plot_confusion(
            model_metrics["confusion_matrix"],
            labels,
            ("Linear SVM" if name == "svm" else "Random Forest") + " Confusion Matrix",
            RESULTS
            / "figures"
            / ("svm_confusion_matrix.png" if name == "svm" else "rf_confusion_matrix.png"),
        )

    # Freeze the deployment choice using validation data only; the test set is
    # evaluated afterwards for final reporting, never for hyperparameter/model selection.
    selected = max(searches, key=lambda name: searches[name]["validation_macro_f1"])
    selected_path = ARTIFACTS / "selected_model.joblib"
    shutil.copyfile(ARTIFACTS / f"{selected}_pipeline.joblib", selected_path)
    selected_metrics = metrics[selected]
    metadata = {
        "model_id": f"bbc-tfidf-{selected}-v1",
        "model_version": "1.0.0",
        "algorithm": selected_metrics["algorithm"],
        "training_dataset": "SetFit/bbc-news@9c31f7087a8c225be8b4c420d70216ef1f121eb0",
        "supported_categories": labels,
        "random_seed": RANDOM_SEED,
        "trained_at_utc": datetime.now(UTC).isoformat(),
        "selected_by": "highest validation macro F1; test metrics used only for final reporting",
        "test_metrics": {
            key: selected_metrics[key] for key in ("accuracy", "macro_f1", "weighted_f1")
        },
        "artifact_sha256": __import__("hashlib").sha256(selected_path.read_bytes()).hexdigest(),
        "artifact_bytes": selected_path.stat().st_size,
        "score_semantics": "decision_function" if selected == "svm" else "probability",
    }
    write_json(ARTIFACTS / "model_metadata.json", metadata)

    dataset_summary = json.loads((RESULTS / "reports/dataset_summary.json").read_text())
    plot_class_distribution(
        dataset_summary["class_distribution"], RESULTS / "figures/class_distribution.png"
    )
    plot_comparisons(metrics, RESULTS / "figures")
    comparison_rows = []
    for name, values in metrics.items():
        comparison_rows.append(
            {
                "model": name,
                **{
                    key: values[key]
                    for key in (
                        "accuracy",
                        "macro_precision",
                        "macro_recall",
                        "macro_f1",
                        "weighted_f1",
                        "training_seconds",
                        "inference_milliseconds_per_article",
                        "artifact_bytes",
                    )
                },
                "selected": name == selected,
            }
        )
    pd.DataFrame(comparison_rows).to_csv(RESULTS / "metrics/model_comparison.csv", index=False)
    experiment = {
        "experiment_id": datetime.now(UTC).strftime("phase1-%Y%m%dT%H%M%SZ"),
        "run_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "dataset_content_hash": dataset_summary["content_hash"],
        "split_counts": dataset_summary["split_counts"],
        "random_seed": RANDOM_SEED,
        "searches": searches,
        "selected_model": selected,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "scikit_learn": sklearn.__version__,
        },
    }
    write_json(RESULTS / "reports/experiment_manifest.json", experiment)
    print(
        json.dumps({"selected_model": selected, "metrics": metrics, "metadata": metadata}, indent=2)
    )
    return {"selected_model": selected, "metrics": metrics, "metadata": metadata}


if __name__ == "__main__":
    main()
