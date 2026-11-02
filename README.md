# AI Prompt-Based Online News Chatbot

The repository contains the verified Phase 1 topic-classification baseline and Phase 2A–2B of the
Nigerian news platform. Phase 2B adds deterministic indexed retrieval, configurable structured LLM
generation, citation validation, persistent owner-scoped conversations, and explicit evidence
limitations on top of the permitted Punch RSS metadata pipeline.

The classifier predicts **topic only** (`business`, `entertainment`, `politics`, `sport`, `tech`).
It does not detect misinformation, factuality, political bias, or source credibility.

## Verified baseline

The pinned [SetFit BBC News dataset](https://huggingface.co/datasets/SetFit/bbc-news) contains 2,225
English BBC articles from 2004–2005. After global cleaning, 2,090 records remained. The selected
Linear SVM achieved 98.09% accuracy and 0.9800 macro F1 on a held-out 314-article test set. These
figures are specific to this historical British benchmark and do not establish Nigerian-domain
performance.

## Repository layout

```text
backend/      FastAPI app, SQLAlchemy models, Alembic migration, tests, Dockerfile
frontend/     Phase 2 React/TypeScript/Vercel integration notes
ml/           acquisition, preprocessing, training, evaluation, artifacts, measured outputs
docs/         architecture, dataset, methodology, experiment and deployment reports
tests/        dataset and ML unit tests
shared/       dependency-light ingestion contracts shared by backend and research code
```

## Local setup

Python 3.11–3.13 is supported. Commands are run from the repository root.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn backend.app.main:app --reload
```

Copy `.env.example` to `.env`. Set a long random `ADMIN_API_KEY` before using administrative
endpoints. Set `CHAT_ACCESS_TOKENS` to a JSON token-to-subject mapping for the transitional chat
boundary. Tokens and `LLM_API_KEY` are server secrets and must never enter frontend configuration.
SQLite is the zero-service local default; set `DATABASE_URL` to a PostgreSQL Psycopg URL for Railway
or local PostgreSQL.

Run one bounded ingestion job manually—never as a permanent loop inside the web worker:

```bash
.venv/bin/python -m backend.scripts.ingest_news --source punch --limit 50
```

The same command is suitable for Railway Cron. It fetches only official RSS metadata/excerpts,
normalizes and deduplicates canonical URLs, applies the existing SVM, and persists provenance and
classification metadata. New items are indexed in the same transaction. It does not reproduce
publisher article bodies. Rebuild historical retrieval metadata with:

```bash
.venv/bin/python -m backend.scripts.index_news
.venv/bin/python -m backend.scripts.index_news --only-stale
```

Generation is disabled by default. To use the OpenAI Responses provider, set `LLM_PROVIDER=openai`
and inject `LLM_API_KEY` through the deployment secret store. The implementation uses strict JSON
Schema output, bounded timeouts/retries, output-token limits, and post-generation citation checks.
There is no fake production answer fallback and CI never calls a paid provider.

The historical Phase 1 experiment can still be reproduced separately:

```bash
.venv/bin/python -m ml.scripts.acquire_data
.venv/bin/python -m ml.scripts.prepare_data
.venv/bin/python -m ml.scripts.train_models
.venv/bin/python -m ml.scripts.evaluate_models
```

Raw and processed article text is intentionally ignored by Git. The acquisition script uses a
pinned Hugging Face revision, records file hashes and schema, and recreates the local inputs.
Training never occurs during API startup.

## API

```bash
.venv/bin/uvicorn backend.app.main:app --reload
```

OpenAPI documentation is available at `http://localhost:8000/docs`.

- `GET /health` — service version and operational status.
- `GET /api/v1/ml/model-info` — non-sensitive artifact and training metadata.
- `POST /api/v1/ml/classify` — topic prediction from a title, content, or both.
- `GET /api/v1/news` — paginated news with category/source filters and sorting.
- `GET /api/v1/news/search` — bounded title/excerpt keyword search.
- `GET /api/v1/news/categories` and `/sources` — filter metadata.
- `GET /api/v1/news/{id}` — article provenance, excerpt, and model metadata.
- `POST /api/v1/admin/news/ingest` — protected bounded ingestion trigger.
- `GET /api/v1/admin/ingestion-runs` — protected run/failure history.
- `PATCH` or `DELETE /api/v1/admin/news/{id}` — protected correction or soft deletion.
- `POST /api/v1/chat` — grounded answer, structured citations, limitations, and diversity metadata.
- `GET /api/v1/chat/conversations` and `/{id}` — the authenticated subject's chat history.
- `DELETE /api/v1/chat/conversations/{id}` — owner-scoped soft deletion.
- `GET /api/v1/chat/health` — public readiness booleans and indexed count, never secrets.

Administrative calls require `X-Admin-Key`. This is a transitional server-side Milestone 2A
control; user accounts and role-backed authentication are deliberately deferred to Milestone 2C.
Chat calls require `Authorization: Bearer …`; the server resolves the subject from its secret
mapping and never trusts a client-supplied user ID. This is suitable for the Phase 2B boundary but
is not a replacement for production OIDC, token rotation, or account lifecycle management.

Linear SVM outputs are explicitly returned as uncalibrated `decision_function` scores, not
probabilities. Requests are limited to 500 title characters and 50,000 content characters.

## Database, tests, and quality

SQLite is the zero-service local default; production uses `DATABASE_URL` for Railway PostgreSQL.

```bash
.venv/bin/alembic upgrade head
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m backend.scripts.evaluate_rag
```

The maintained suite uses deterministic RSS and model fixtures, does not call publishers, and does
not retrain full models. GitHub Actions runs the same checks. Live feed verification is a separate
documented smoke test. Never commit secrets or local databases.

## Deployment boundary

The backend Dockerfile is Railway-compatible and listens on `${PORT:-8000}`. The selected trusted
artifact is loaded once, hash-checked, and served by FastAPI. The future React/TypeScript frontend
will use `VITE_API_BASE_URL` and deploy separately to Vercel. See
[architecture](docs/architecture.md) and [deployment plan](docs/deployment_plan.md).

## Limitations and remaining Phase 2 work

- BBC News is old, British, and not representative of Nigerian reporting or current language.
- The source repository states BBC copyright but no open dataset license; raw text is not committed.
- Punch is the only integrated publisher because it provides an explicit official RSS directory.
- No Nigerian labeled evaluation set exists yet; live ingestion is not an accuracy evaluation.
- Retrieval is lexical BM25-style ranking, not semantic search. The current metadata-only corpus is
  too small to justify embedding infrastructure; pgvector remains a future scale decision.
- Only one publisher is integrated, so the API reports that cross-source corroboration is not
  possible. Source diversity metadata is a limitation signal, not a bias or credibility score.
- RAG does not fact-check publishers or make truth, misinformation, political-bias, or credibility
  determinations. Answers are limited to retrieved excerpts and publisher attribution.
- The bearer-token mapping is transitional. Full user lifecycle, OIDC, and role-backed authorization
  remain Phase 2C work.
- Near-duplicate detection is a conservative 64-bit trigram SimHash screen, not semantic deduplication.

Detailed evidence is in [dataset report](docs/dataset_report.md),
[methodology](docs/ml_methodology.md), [experiment report](docs/experiment_report.md), and
[Phase 1 summary](docs/phase_1_summary.md). Milestone 2A evidence is in
[ingestion sources](docs/ingestion_sources.md), [Phase 2 architecture](docs/phase_2_architecture.md),
and [Phase 2 evaluation](docs/phase_2_evaluation.md).
Phase 2B details are in the [RAG design](docs/rag_design.md),
[chatbot architecture](docs/chatbot_architecture.md),
[evaluation report](docs/phase_2b_evaluation.md), and
[implementation summary](docs/phase_2b_summary.md).
