#!/usr/bin/env python3
"""Acquire the pinned BBC News JSONL files and record their provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REVISION = "9c31f7087a8c225be8b4c420d70216ef1f121eb0"
BASE_URL = f"https://huggingface.co/datasets/SetFit/bbc-news/resolve/{REVISION}"
FILES = ("train.jsonl", "test.jsonl")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_jsonl(path: Path) -> tuple[int, list[str]]:
    count = 0
    columns: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            if not isinstance(record, dict) or not {"text", "label", "label_text"} <= record.keys():
                raise ValueError(f"Malformed schema in {path}:{line_number}")
            count += 1
            columns.update(record)
    return count, sorted(columns)


def acquire(destination: Path, force: bool = False) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for filename in FILES:
        target = destination / filename
        if force or not target.exists():
            request = urllib.request.Request(
                f"{BASE_URL}/{filename}", headers={"User-Agent": "ai-news-chatbot-research/0.1"}
            )
            with (
                urllib.request.urlopen(request, timeout=60) as response,
                target.open("wb") as output,
            ):
                output.write(response.read())
        rows, columns = inspect_jsonl(target)
        records.append(
            {
                "file": filename,
                "url": f"{BASE_URL}/{filename}",
                "rows": rows,
                "columns": columns,
                "sha256": sha256(target),
                "bytes": target.stat().st_size,
            }
        )
    provenance = {
        "dataset": "SetFit/bbc-news",
        "original_dataset": "BBC News Topic Dataset",
        "source_url": "https://huggingface.co/datasets/SetFit/bbc-news",
        "revision": REVISION,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "language": "English",
        "license": "No open license stated; BBC retains copyright in article content.",
        "usage_note": "Raw text is excluded from Git and used only as a local research baseline.",
        "files": records,
        "total_rows": sum(record["rows"] for record in records),
    }
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("ml/data/raw"))
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(acquire(arguments.destination, arguments.force), indent=2))
