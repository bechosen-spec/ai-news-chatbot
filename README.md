# AI Prompt-Based Online News Chatbot

Phase 1 provides a reproducible news-topic classification baseline and a deployment-ready FastAPI
foundation for a future Nigerian online-news chatbot. It trains and compares TF-IDF + Linear SVM
and TF-IDF + Random Forest on real news data, preserves measured results, exposes the selected
pipeline through a validated API, and defines the initial relational schema.

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
```

## Local setup

Python 3.11–3.13 is supported. Commands are run from the repository root.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
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

Linear SVM outputs are explicitly returned as uncalibrated `decision_function` scores, not
probabilities. Requests are limited to 500 title characters and 50,000 content characters.

## Database, tests, and quality

SQLite is the zero-service local default; production uses `DATABASE_URL` for Railway PostgreSQL.

```bash
.venv/bin/alembic upgrade head
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

The maintained suite does not download the dataset or retrain full models. GitHub Actions runs the
same deterministic checks. Copy `.env.example` to `.env` for local overrides; never commit secrets.

## Deployment boundary

The backend Dockerfile is Railway-compatible and listens on `${PORT:-8000}`. The selected trusted
artifact is loaded once, hash-checked, and served by FastAPI. The future React/TypeScript frontend
will use `VITE_API_BASE_URL` and deploy separately to Vercel. See
[architecture](docs/architecture.md) and [deployment plan](docs/deployment_plan.md).

## Limitations and Phase 2

- BBC News is old, British, and not representative of Nigerian reporting or current language.
- The source repository states BBC copyright but no open dataset license; raw text is not committed.
- No probability calibration, Nigerian external evaluation, RAG, LLM, bias mitigation, fact-checking,
  authentication, pgvector, voice features, or production UI is claimed in Phase 1.
- Near-duplicate detection is a conservative 64-bit trigram SimHash screen, not semantic deduplication.

Detailed evidence is in [dataset report](docs/dataset_report.md),
[methodology](docs/ml_methodology.md), [experiment report](docs/experiment_report.md), and
[Phase 1 summary](docs/phase_1_summary.md).
