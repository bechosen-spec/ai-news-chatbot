"""CPU-friendly model pipelines and bounded validation search."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ml.src.datasets import RANDOM_SEED


@dataclass
class SearchResult:
    name: str
    pipeline: Pipeline
    parameters: dict[str, Any]
    validation_macro_f1: float
    candidate_results: list[dict[str, Any]]


def _vectorizer(max_features: int) -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        max_features=max_features,
        sublinear_tf=True,
    )


def _candidate_pipeline(name: str, params: dict[str, Any]) -> Pipeline:
    if name == "svm":
        classifier = LinearSVC(C=params["C"], class_weight="balanced", random_state=RANDOM_SEED)
        features = 20_000
    elif name == "random_forest":
        classifier = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            max_features="sqrt",
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        features = 8_000
    else:
        raise ValueError(f"Unknown model: {name}")
    return Pipeline([("tfidf", _vectorizer(features)), ("classifier", classifier)])


def select_on_validation(name: str, train_x, train_y, validation_x, validation_y) -> SearchResult:
    candidates = (
        [{"C": value} for value in (0.5, 1.0, 2.0)]
        if name == "svm"
        else [
            {"n_estimators": 200, "max_depth": 40},
            {"n_estimators": 200, "max_depth": None},
        ]
    )
    results: list[dict[str, Any]] = []
    best: tuple[float, Pipeline, dict[str, Any]] | None = None
    for parameters in candidates:
        pipeline = _candidate_pipeline(name, parameters)
        started = time.perf_counter()
        pipeline.fit(train_x, train_y)
        duration = time.perf_counter() - started
        score = float(f1_score(validation_y, pipeline.predict(validation_x), average="macro"))
        results.append(
            {"parameters": parameters, "validation_macro_f1": score, "fit_seconds": duration}
        )
        if best is None or score > best[0]:
            best = (score, pipeline, parameters)
    assert best is not None
    return SearchResult(name, best[1], best[2], best[0], results)


def build_pipeline(name: str, parameters: dict[str, Any]) -> Pipeline:
    return _candidate_pipeline(name, parameters)
