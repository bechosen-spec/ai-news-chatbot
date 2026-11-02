# Phase 2 evaluation — Milestone 2A

## Automated verification

The deterministic suite covers defensive RSS parsing, tracking-parameter removal, UTC dates, feed
outage isolation and retry limits, duplicate handling, classification persistence, source/model
category separation, news pagination, filtering, keyword search, provenance details, request
validation, admin authorization, administrator correction, soft deletion, database constraints, and
upgrade/downgrade migrations. All Phase 1 tests are preserved.

Final test counts and CI status are recorded in the PR and Milestone 2A report. Routine tests use
fixtures and make no publisher or paid-service calls.

## Live permitted-feed smoke test

On 2 November 2026, the management command ran against Punch's official RSS service and a migrated
temporary SQLite database:

| Run | Fetched | Inserted | Duplicates | Failed | Status |
|---|---:|---:|---:|---:|---|
| Initial bounded run | 8 | 8 | 0 | 0 | completed |
| Immediate repeat | 8 | 0 | 8 | 0 | completed |

Read-back verified eight stored records, zero non-empty full-content fields, five registered model
categories, one active publisher, and successful list/search/source/category API responses. Search
for `Nigeria` returned two of the eight first-run items at that moment.

A protected live API smoke test rejected a missing admin credential with HTTP 401, accepted the
configured credential with HTTP 200, recorded three duplicate items without reinsertion, and returned
three persisted ingestion runs through the history endpoint.

The eight latest-feed articles were classified as business (4), entertainment (3), and sport (1).
These observations are pipeline outputs, not accuracy results: the sample has no reviewed ground
truth, is tiny and time-dependent, and the classifier was trained on historical British news. No
Nigerian accuracy, calibration, or bias claim is made.

## Not evaluated in Milestone 2A

PostgreSQL production load, Railway Cron, Nigerian classification accuracy, temporal robustness,
semantic retrieval, LLM grounding, citation validation, user authentication, frontend behavior, and
voice functionality remain unverified and belong to later reviewed milestones.

