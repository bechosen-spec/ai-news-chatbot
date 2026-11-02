#!/usr/bin/env python3
"""Run one bounded ingestion job outside the web process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import OperationalError

from backend.app.core.config import Settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.ingestion.rss import punch_adapter
from backend.app.services.ingestion.service import ingest
from backend.app.services.model_service import ModelService, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest permitted Nigerian news RSS metadata")
    parser.add_argument("--source", choices=["punch"], default="punch")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("--limit must be between 1 and 200")

    settings = Settings(**({"database_url": args.database_url} if args.database_url else {}))
    settings.model_path = resolve_path(settings.model_path, PROJECT_ROOT)
    settings.model_metadata_path = resolve_path(settings.model_metadata_path, PROJECT_ROOT)
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    adapter = punch_adapter(
        timeout_seconds=settings.ingestion_timeout_seconds,
        retry_limit=settings.ingestion_retry_limit,
        excerpt_max_characters=settings.news_excerpt_max_characters,
    )
    try:
        with session_factory() as session:
            run = ingest(session, adapter, ModelService(settings), limit=args.limit)
            result = {
                "run_id": run.id,
                "status": run.status,
                "fetched": run.fetched_count,
                "inserted": run.inserted_count,
                "duplicates": run.duplicate_count,
                "failed": run.failed_count,
            }
            print(json.dumps(result, indent=2))
            return 1 if run.status == "failed" else 0
    except OperationalError as error:
        parser.error(f"Database is unavailable or not migrated: {error.orig}")
    finally:
        engine.dispose()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
