# Phase 2B RAG design

## Retrieval choice

Phase 2B uses a deterministic BM25-style lexical index. Each article stores normalized term counts,
title term counts, document length, source text hash, index version, and index time in
`retrieval_metadata`. Ranking combines BM25 term saturation and inverse document frequency, a title
boost, and a small freshness tie-breaker. A document receives no freshness score unless it first has
a lexical match.

The current corpus contains short publisher-provided RSS metadata from one source. Embeddings and
pgvector would add model, storage, migration, and operational cost without a representative corpus
on which to validate semantic gains. The retrieval interface is isolated so a later hybrid semantic
backend can be evaluated against the committed lexical baseline before adoption.

Queries are case-normalized, token-bounded, and stripped of a small deterministic stop-word list.
The retriever supports effective category, source, and publication-date filters. It excludes inactive
sources and soft-deleted articles, deduplicates canonical URLs and content hashes, then reranks
repeated publishers with a penalty. The response reports candidate count, unique sources, diversity
ratio, and limitations. With today's one-source corpus it explicitly says cross-source corroboration
is unavailable; it never converts diversity into a bias, quality, or credibility judgment.

Ingestion indexes every inserted article after its database ID is assigned. Historical or changed
records can be rebuilt with `python -m backend.scripts.index_news`; `--only-stale` compares both text
hash and index version. Indexing is local and deterministic, with no network or paid dependency.

## Grounding and citation integrity

Retrieved items receive request-local IDs (`S1`, `S2`, …). The prompt supplies title, publisher,
publication time, canonical URL, and the bounded stored excerpt. It labels all evidence as untrusted
data and instructs the model to ignore commands, role changes, secret requests, and other prompt
injection inside article text. The system prompt also requires attribution for allegations and
prohibits outside knowledge, publisher-intent inference, truth scores, and political-bias claims.

The provider must return a strict structure: `answer`, `citation_ids`, and `limitations`. The server
validates that every cited ID belongs to the retrieved evidence and requires a citation whenever
evidence exists. Unknown or missing citations produce a safe `citation_validation_failed` response;
the generated prose and fabricated citations are not returned. No matching evidence produces a
deterministic `insufficient_evidence` response without calling an LLM.

Conversation history is bounded to six messages, each truncated for prompt construction, and the
overall evidence prompt has a configurable character cap. Short follow-up questions reuse the
previous user question only for retrieval. Stored history is never accepted as an identity claim.

## Provider boundary

`LLMProvider` is a small asynchronous protocol. Phase 2B implements the OpenAI Responses API with
server-side secrets, configurable model/base URL, request timeout, bounded retry/backoff, output-token
limit, and Pydantic validation. It follows the official
[Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
by sending a strict JSON Schema under `text.format`. Refusals, malformed JSON, schema failures,
timeouts, and HTTP errors become explicit service errors. `disabled` is the safe default.
