#!/usr/bin/env python3
"""Prepare deterministic, leakage-checked train/validation/test files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ml.src.datasets import BBC_CATEGORIES, RANDOM_SEED, stratified_split, validate_frame
from ml.src.preprocessing import clean_dataset


def read_source(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for source_split in ("train", "test"):
        path = raw_dir / f"{source_split}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run acquire_data.py first")
        frame = pd.read_json(path, lines=True)
        frame["source_split"] = source_split
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    return combined.rename(columns={"label": "source_label_id", "label_text": "label"})


def prepare(raw_dir: Path, output_dir: Path) -> dict:
    source = read_source(raw_dir)
    provenance_path = raw_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else None
    source_missing = source.isna().sum().astype(int).to_dict()
    cleaned, quality = clean_dataset(source)
    validate_frame(cleaned, BBC_CATEGORIES)
    train, validation, test = stratified_split(cleaned, RANDOM_SEED)
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = ["article_id", "text", "label", "content_hash", "source_split"]
    parts = {"train": train, "validation": validation, "test": test}
    for name, part in parts.items():
        part[columns].to_csv(output_dir / f"{name}.csv", index=False)

    summary = {
        "dataset": "SetFit/bbc-news",
        "source_provenance": provenance,
        "random_seed": RANDOM_SEED,
        "split_strategy": (
            "stratified 70/15/15 after global exact and conservative near-deduplication"
        ),
        "source_missing_values": source_missing,
        **quality,
        "split_counts": {name: len(part) for name, part in parts.items()},
        "split_class_distribution": {
            name: part["label"].value_counts().sort_index().astype(int).to_dict()
            for name, part in parts.items()
        },
        "representative_examples": [
            {
                "article_id": str(cleaned.loc[cleaned["label"].eq(label), "article_id"].iloc[0]),
                "label": label,
            }
            for label in sorted(cleaned["label"].unique())
        ],
        "content_hash": __import__("hashlib")
        .sha256("".join(sorted(cleaned["content_hash"])).encode())
        .hexdigest(),
    }
    report_path = Path("ml/results/reports/dataset_summary.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("ml/data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/data/processed"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.raw_dir, args.output_dir), indent=2))
