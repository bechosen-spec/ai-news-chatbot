"""Build or refresh deterministic retrieval metadata for stored articles."""

import argparse

from backend.app.core.config import get_settings
from backend.app.db.session import create_database_engine, create_session_factory
from backend.app.services.retrieval.index import reindex_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-stale", action="store_true")
    arguments = parser.parse_args()
    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as session:
        count = reindex_all(session, only_stale=arguments.only_stale)
    engine.dispose()
    print(f"Indexed {count} article(s).")


if __name__ == "__main__":
    main()
