"""Evaluation metrics and publication-ready baseline figures."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-news-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)


def evaluate(
    pipeline, test_x, test_y, labels: list[str], training_seconds: float
) -> dict[str, Any]:
    started = time.perf_counter()
    predictions = pipeline.predict(test_x)
    prediction_seconds = time.perf_counter() - started
    macro = precision_recall_fscore_support(test_y, predictions, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(
        test_y, predictions, average="weighted", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(test_y, predictions)),
        "macro_precision": float(macro[0]),
        "macro_recall": float(macro[1]),
        "macro_f1": float(macro[2]),
        "weighted_f1": float(weighted[2]),
        "training_seconds": training_seconds,
        "inference_seconds_total": prediction_seconds,
        "inference_milliseconds_per_article": prediction_seconds / len(test_x) * 1000,
        "test_articles": len(test_x),
        "classification_report": classification_report(
            test_y, predictions, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(test_y, predictions, labels=labels).tolist(),
    }


def _save(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_class_distribution(counts: dict[str, int], output: Path) -> None:
    plt.figure(figsize=(8, 4.8))
    plt.bar(list(counts), list(counts.values()), color="#386cb0")
    plt.title("BBC News Class Distribution After Deduplication")
    plt.xlabel("Category")
    plt.ylabel("Articles")
    _save(output)


def plot_confusion(matrix: list[list[int]], labels: list[str], title: str, output: Path) -> None:
    array = np.asarray(matrix)
    plt.figure(figsize=(7, 6))
    plt.imshow(array, cmap="Blues")
    plt.colorbar(label="Articles")
    plt.xticks(range(len(labels)), labels, rotation=35, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Predicted category")
    plt.ylabel("True category")
    plt.title(title)
    for row in range(len(labels)):
        for column in range(len(labels)):
            plt.text(column, row, str(array[row, column]), ha="center", va="center")
    _save(output)


def plot_comparisons(metrics: dict[str, dict[str, Any]], figure_dir: Path) -> None:
    names = list(metrics)
    display = ["Linear SVM" if name == "svm" else "Random Forest" for name in names]
    specs = [
        ("accuracy", "Accuracy", "accuracy_comparison.png", "Score"),
        ("macro_f1", "Macro F1-score", "f1_comparison.png", "Score"),
        ("training_seconds", "Training Time", "training_time_comparison.png", "Seconds"),
        (
            "inference_milliseconds_per_article",
            "Inference Time per Article",
            "inference_time_comparison.png",
            "Milliseconds",
        ),
    ]
    for key, title, filename, ylabel in specs:
        plt.figure(figsize=(6.5, 4.5))
        values = [metrics[name][key] for name in names]
        bars = plt.bar(display, values, color=["#1b9e77", "#d95f02"])
        plt.title(f"{title}: Held-out Test Set")
        plt.ylabel(ylabel)
        for bar, value in zip(bars, values, strict=True):
            plt.text(
                bar.get_x() + bar.get_width() / 2, value, f"{value:.4f}", ha="center", va="bottom"
            )
        _save(figure_dir / filename)

    labels = [
        key
        for key in metrics[names[0]]["classification_report"]
        if key in {"business", "entertainment", "politics", "sport", "tech"}
    ]
    positions = np.arange(len(labels))
    width = 0.36
    plt.figure(figsize=(9, 5))
    for index, name in enumerate(names):
        values = [metrics[name]["classification_report"][label]["f1-score"] for label in labels]
        plt.bar(positions + (index - 0.5) * width, values, width, label=display[index])
    plt.xticks(positions, labels)
    plt.ylim(0, 1.05)
    plt.ylabel("F1-score")
    plt.title("Per-class F1-score on Held-out Test Set")
    plt.legend()
    _save(figure_dir / "per_class_performance.png")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")
