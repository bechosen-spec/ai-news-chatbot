# Phase 2B chatbot architecture

## Request flow

```text
Bearer token
  -> constant-time server-side token/subject resolution
  -> owner-scoped conversation lookup or creation
  -> bounded query normalization and optional filters
  -> indexed retrieval + URL/hash deduplication + source-diversity rerank
  -> untrusted evidence envelope + bounded conversation history
  -> configurable structured generation provider
  -> citation allow-list validation
  -> persistent assistant message + citations + retrieval metadata
```

The client never supplies an owner/user ID. `POST /api/v1/chat` accepts only the question, optional
conversation ID, and retrieval filters. Conversation lookup always includes both the authenticated
server-side subject and `deleted_at IS NULL`, so another valid subject receives the same 404 as a
missing conversation. Listing, reading, continuation, and soft deletion share this predicate.

Alembic revision `0003_rag_chat` adds `owner_subject`, update/delete timestamps, message citations,
message status/metadata, and lexical index fields. Existing nullable ownership is preserved during
migration; legacy unowned conversations are inaccessible through the Phase 2B endpoints rather than
being assigned to an arbitrary caller.

## API behavior

- `POST /api/v1/chat` returns answer status, structured citations, limitations, candidate count,
  unique-source count, and diversity ratio.
- `GET /api/v1/chat/conversations` lists only active conversations owned by the caller.
- `GET /api/v1/chat/conversations/{id}` returns ordered persisted messages for that owner.
- `DELETE /api/v1/chat/conversations/{id}` soft-deletes only an owned conversation.
- `GET /api/v1/chat/health` is public and exposes only provider name/configuration state,
  authentication configuration state, and indexed count—never keys or token subjects.

Missing authentication configuration returns 503; missing/invalid bearer credentials return 401;
provider unavailability returns 503, timeout 504, and malformed/rejected provider output 502.
Question length, result count, history, evidence context, provider output tokens, network timeout,
and retries are all bounded.

## Security and operational boundary

`CHAT_ACCESS_TOKENS` is a transitional JSON mapping stored only in server secrets. It provides real
owner isolation without trusting request identity, but production account lifecycle, token rotation,
OIDC validation, and revocation belong to the next authentication milestone. Administrative access
continues to use its separate `X-Admin-Key`; chat credentials never grant administrative rights.

The web process does not train models, run permanent schedulers, scrape article pages, or reproduce
publisher bodies. Ingestion and reindexing are explicit bounded jobs. CI uses deterministic fixtures
and fake providers, makes no publisher/provider network calls, and spends no LLM credits.
