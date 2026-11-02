# Phase 2B evaluation

## Method

The committed offline fixture contains 12 real Punch titles and canonical URLs observed through the
publisher's latest-news RSS feed on 2026-11-02. It contains no article bodies. Eight manually reviewed
queries each have one relevant article ID. `python -m backend.scripts.evaluate_rag` creates an
in-memory database, builds the same production index, and compares simple token-overlap keyword
ranking with `bm25-v1` at three results. It also runs deterministic citation-validator cases and
writes JSON, per-query CSV, and a PNG chart under `ml/results/rag/`.

## Measured result

| Method | Precision@3 | Recall@3 | MRR | Mean latency |
| --- | ---: | ---: | ---: | ---: |
| Keyword overlap | 0.3333 | 1.0000 | 1.0000 | 6.03 ms |
| BM25 v1 | 0.3333 | 1.0000 | 1.0000 | 4.16 ms |

Both methods ranked the relevant item first for all eight easy, title-oriented queries. This small
fixture therefore demonstrates no ranking-quality improvement from BM25; it establishes a repeatable
baseline and verifies that the richer method does not regress these cases. Latency is an indicative
single-process local measurement, not a production benchmark. The apparent difference should not be
generalized.

Citation validation passed all three deterministic cases: one allowed citation was accepted, while
one fabricated ID and one missing-citation answer were rejected. Unit tests separately cover prompt
injection text remaining inside the untrusted evidence envelope, cross-owner conversation denial,
safe no-evidence behavior, strict provider output parsing, and retry behavior.

No live LLM evaluation was performed because no provider key was configured. The project does not
invent answer-quality, hallucination, token-cost, or provider-latency numbers, and CI does not make
paid calls.

## Limitations

- Twelve articles and eight judgments are too small for broad retrieval conclusions.
- Titles and URLs are lawful metadata but do not test answer completeness over article bodies.
- Every item is from Punch, so source-diversity reranking and corroboration cannot be evaluated.
- Manually reviewed relevance labels can contain assessor bias and have no inter-rater agreement.
- Retrieval relevance and citation validity do not establish factual truth, source credibility,
  political balance, or misinformation detection.

The machine-readable evidence is
`ml/results/rag/retrieval_metrics.json`; query-level outputs are
`ml/results/rag/retrieval_queries.csv`.
