"""Repeatable offline retrieval and citation-safety evaluation for Phase 2B."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.models import DataSource, NewsArticle
from backend.app.services.llm import GeneratedAnswer
from backend.app.services.rag.citations import validate_citations
from backend.app.services.retrieval import Evidence, Retriever
from backend.app.services.retrieval.index import index_article

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "ml/data/evaluation/phase2b_punch_metadata.json"
OUTPUT = ROOT / "ml/results/rag"


def _seed(session: Session, fixture: dict) -> None:
    source = DataSource(
        id="source-punch",
        name=fixture["provenance"]["publisher"],
        slug=fixture["provenance"]["source_slug"],
        base_url="https://punchng.com",
        feed_url=fixture["provenance"]["feed"],
        terms_url="https://rss.punchng.com/",
        ingestion_method="rss",
        is_active=True,
    )
    session.add(source)
    for item in fixture["articles"]:
        article = NewsArticle(
            id=item["id"],
            source=source,
            title=item["title"],
            content="",
            excerpt=None,
            original_url=item["url"],
            content_hash=hashlib.sha256(item["title"].encode()).hexdigest(),
        )
        session.add(article)
        session.flush()
        index_article(session, article)
    session.commit()


def _evaluate_retriever(session: Session, fixture: dict, *, baseline: bool) -> tuple[dict, list]:
    rows = []
    for case in fixture["queries"]:
        started = perf_counter()
        result = Retriever(session).search(case["query"], limit=3, baseline=baseline)
        elapsed_ms = (perf_counter() - started) * 1_000
        retrieved = [item.article_id for item in result.evidence]
        relevant = set(case["relevant_ids"])
        hits = relevant.intersection(retrieved)
        ranks = [position for position, item in enumerate(retrieved, start=1) if item in relevant]
        rows.append(
            {
                "query": case["query"],
                "relevant_ids": "|".join(case["relevant_ids"]),
                "retrieved_ids": "|".join(retrieved),
                "precision_at_3": len(hits) / 3,
                "recall_at_3": len(hits) / len(relevant),
                "reciprocal_rank": 1 / min(ranks) if ranks else 0.0,
                "latency_ms": elapsed_ms,
            }
        )
    metrics = {
        "precision_at_3": mean(row["precision_at_3"] for row in rows),
        "recall_at_3": mean(row["recall_at_3"] for row in rows),
        "mrr": mean(row["reciprocal_rank"] for row in rows),
        "mean_latency_ms": mean(row["latency_ms"] for row in rows),
        "query_count": len(rows),
    }
    return metrics, rows


def _citation_safety() -> dict:
    evidence = [
        Evidence(
            "S1",
            "article",
            "Title",
            "Publisher",
            "source",
            "https://example.test",
            None,
            "",
            None,
            1.0,
        )
    ]
    cases = [
        (GeneratedAnswer(answer="Grounded", citation_ids=["S1"]), True),
        (GeneratedAnswer(answer="Fabricated", citation_ids=["S999"]), False),
        (GeneratedAnswer(answer="Missing", citation_ids=[]), False),
    ]
    observed = [validate_citations(answer, evidence)[0] for answer, _ in cases]
    expected = [expected_value for _, expected_value in cases]
    return {
        "case_count": len(cases),
        "correct": sum(
            actual == expected_value
            for actual, expected_value in zip(observed, expected, strict=True)
        ),
        "accuracy": mean(
            actual == expected_value
            for actual, expected_value in zip(observed, expected, strict=True)
        ),
        "fabricated_citation_rejected": observed[1] is False,
        "missing_citation_rejected": observed[2] is False,
    }


def main() -> None:
    fixture = json.loads(FIXTURE.read_text())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session, fixture)
        keyword_metrics, keyword_rows = _evaluate_retriever(session, fixture, baseline=True)
        bm25_metrics, bm25_rows = _evaluate_retriever(session, fixture, baseline=False)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {
        "fixture": str(FIXTURE.relative_to(ROOT)),
        "provenance": fixture["provenance"],
        "corpus_size": len(fixture["articles"]),
        "keyword_baseline": keyword_metrics,
        "bm25_v1": bm25_metrics,
        "citation_validation": _citation_safety(),
        "live_llm_evaluation": {
            "performed": False,
            "reason": (
                "OPENAI_API_KEY was not configured; no paid or network-dependent "
                "evaluation was run."
            ),
        },
        "limitations": [
            "The lawful fixture contains publisher-provided titles and URLs, not article bodies.",
            "All items are from one publisher, so cross-source diversity cannot be evaluated.",
            "Eight relevance judgments are manually reviewed but small and domain-specific.",
        ],
    }
    (OUTPUT / "retrieval_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    with (OUTPUT / "retrieval_queries.csv").open("w", newline="") as handle:
        fields = ["method", *keyword_rows[0].keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for method, rows in (("keyword", keyword_rows), ("bm25_v1", bm25_rows)):
            for row in rows:
                writer.writerow({"method": method, **row})

    labels = ["Precision@3", "Recall@3", "MRR"]
    keys = ["precision_at_3", "recall_at_3", "mrr"]
    image = Image.new("RGB", (800, 480), "white")
    draw = ImageDraw.Draw(image)
    draw.text((240, 20), "Phase 2B offline retrieval evaluation", fill="black")
    draw.line((80, 400, 750, 400), fill="black", width=2)
    draw.line((80, 70, 80, 400), fill="black", width=2)
    for position, (label, key) in enumerate(zip(labels, keys, strict=True)):
        start_x = 140 + position * 210
        keyword_height = int(keyword_metrics[key] * 300)
        bm25_height = int(bm25_metrics[key] * 300)
        draw.rectangle((start_x, 400 - keyword_height, start_x + 55, 400), fill="#94a3b8")
        draw.rectangle((start_x + 65, 400 - bm25_height, start_x + 120, 400), fill="#2563eb")
        draw.text((start_x, 415), label, fill="black")
    draw.rectangle((570, 55, 590, 70), fill="#94a3b8")
    draw.text((596, 55), "Keyword", fill="black")
    draw.rectangle((670, 55, 690, 70), fill="#2563eb")
    draw.text((696, 55), "BM25 v1", fill="black")
    image.save(OUTPUT / "retrieval_comparison.png")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
