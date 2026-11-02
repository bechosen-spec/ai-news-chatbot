# Phase 2 architecture — Milestone 2A

## Implemented data flow

```text
Official Punch latest-news RSS feed
        |
bounded HTTP fetch + retry + defensive XML parsing
        |
validate domain -> normalize excerpt -> canonicalize URL -> in-run deduplicate
        |
database uniqueness check -> existing hash-verified Linear SVM pipeline
        |
article metadata + source category + model classification + run/failure records
        |
FastAPI news/search/provenance APIs and protected administrative APIs
```

The shared `NewsSourceAdapter` contract is dependency-light and remains import-compatible from the
Phase 1 ML module. The Punch adapter accepts only HTTP(S) publisher links on an explicit domain
allow-list, removes common tracking parameters, parses dates to UTC, bounds XML responses to 5 MB,
strips markup, and truncates excerpts according to configuration. Feed failures are isolated and
recorded without crashing the web application.

The orchestration service ensures source/category records, rejects existing canonical URL or
source/external-ID pairs, classifies title plus RSS excerpt, and persists model ID, version, score
type, margins, input hash, and timestamps. Source-provided categories remain separate from the SVM
prediction. Administrator corrections use a separate category foreign key and never overwrite the
raw prediction.

## Database and operations

Alembic revision `0002_news_ingestion` extends the Phase 1 schema with roles, user preferences,
source configuration, richer article provenance, classification review fields, ingestion runs and
failures, administrative audit logs, and future retrieval-index metadata. Canonical URLs are unique;
source/external-ID pairs have an additional uniqueness constraint. Articles are soft-deleted.

SQLite supports local demonstrations and isolated tests. Production uses Railway PostgreSQL through
the pinned Psycopg driver. The web process does not contain a permanent scheduler. Manual execution
and Railway Cron use `python -m backend.scripts.ingest_news` after migrations are applied.

## Security boundary

Public endpoints expose excerpts and publisher links, not stored full articles. Milestone 2A admin
routes require a constant-time-checked `X-Admin-Key` sourced from environment configuration, and
mutations produce audit records. Full user registration, password hashing, sessions, and role-backed
authorization belong to Milestone 2C and are not claimed here.

Milestone 2B will add retrieval and grounded chat only after this PR is reviewed and merged.
