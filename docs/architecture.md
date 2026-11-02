# Phase 1 architecture

```text
Pinned dataset files -> acquire/validate/hash -> clean/deduplicate/split
                                            -> train/validate SVM + RF
                                            -> metrics/figures + selected pipeline
                                                              |
React/Vercel (Phase 2) -> HTTPS -> FastAPI/Railway -> model service
                                      |             -> trusted joblib artifact
                                      -> PostgreSQL -> articles, chats, predictions, feedback
```

The backend uses a FastAPI application factory, versioned ML routes, Pydantic request/response
schemas, environment settings, CORS allow-listing, and a lazy thread-safe model service. The service
checks artifact existence and SHA-256 before loading the locally produced joblib pipeline. API
startup never downloads data or trains models.

SQLAlchemy models establish normalized users, sources, categories, articles, conversations,
messages, predictions, and feedback. Provenance fields include original URL, source, publication
time, collection time, and content hash. Alembic owns schema evolution. SQLite supports isolated
local tests; `DATABASE_URL` keeps the same model compatible with Railway PostgreSQL.

Phase 2 can add permitted Nigerian source adapters, scheduled ingestion, PostgreSQL full-text and
pgvector indexes, retrieval, and an LLM generation layer. Retrieved passages must carry source URLs
and timestamps. Generated answers remain generated claims—not verified facts—and fact-checking must
be a separate evidence workflow. Bias-aware retrieval, adversarial debiasing, calibration, speech,
authentication, admin tools, and the React UI are deliberately outside Phase 1.

