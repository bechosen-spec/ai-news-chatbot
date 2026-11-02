# Railway and Vercel deployment plan

Railway builds `backend/Dockerfile`, injects `PORT`, `DATABASE_URL`, allowed frontend origins, and
non-secret artifact configuration, then checks `/health`. Database migrations run as an explicit
release step (`alembic upgrade head`), never implicitly in each web worker. The container includes
the small selected model; a future larger model should be a versioned release asset downloaded at
build/release time and verified against metadata, never retrained on startup.

Production uses the pinned Psycopg driver with Railway PostgreSQL. Backups, connection pooling, TLS,
log retention, and least-privilege database roles must be configured before launch. pgvector is
deferred until RAG requirements and embedding lifecycle are specified.

Milestone 2A ingestion runs as a bounded Railway Cron command:

```text
python -m backend.scripts.ingest_news --source punch --limit 100
```

The cron process shares PostgreSQL and environment configuration with the web service but does not
run inside it. `ADMIN_API_KEY` protects manual HTTP-triggered ingestion and must be stored as a
Railway secret. Source failures are persisted for later administrator review.

Vercel hosts the Phase 2 React/TypeScript build. `VITE_API_BASE_URL` points to Railway, while
`ALLOWED_ORIGINS` contains only exact deployed frontend origins. Authentication secrets remain in
platform secret stores. Neither repository nor browser bundles may contain database credentials,
provider secrets, or private API keys.

