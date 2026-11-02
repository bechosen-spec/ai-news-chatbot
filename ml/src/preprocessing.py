"""Leakage-conscious dataset cleaning utilities."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

import pandas as pd

from ml.src.datasets import content_hash, normalize_text


def _simhash(text: str, bits: int = 64) -> int:
    tokens = re.findall(r"\b\w+\b", text.lower())
    features = [" ".join(tokens[i : i + 3]) for i in range(max(1, len(tokens) - 2))]
    vector = [0] * bits
    for feature in features:
        value = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
        for bit in range(bits):
            vector[bit] += 1 if value & (1 << bit) else -1
    return sum((1 << bit) for bit, score in enumerate(vector) if score >= 0)


def clean_dataset(
    frame: pd.DataFrame, near_duplicate_distance: int = 3
) -> tuple[pd.DataFrame, dict]:
    """Normalize, validate, and conservatively remove exact/near duplicates."""
    working = frame.copy()
    input_rows = len(working)
    missing_before = int(working["text"].isna().sum())
    working["text"] = working["text"].map(normalize_text)
    empty_mask = working["text"].eq("")
    empty_removed = int(empty_mask.sum())
    working = working.loc[~empty_mask].copy()
    working["content_hash"] = working["text"].map(content_hash)
    exact_duplicates = int(working.duplicated("content_hash", keep="first").sum())
    working = working.drop_duplicates("content_hash", keep="first").reset_index(drop=True)

    signatures: list[int] = []
    keep: list[bool] = []
    near_removed = 0
    for text in working["text"]:
        signature = _simhash(text)
        duplicate = any(
            (signature ^ prior).bit_count() <= near_duplicate_distance for prior in signatures
        )
        keep.append(not duplicate)
        if duplicate:
            near_removed += 1
        else:
            signatures.append(signature)
    working = working.loc[keep].reset_index(drop=True)
    working["article_id"] = working["content_hash"].str[:16]

    lengths = working["text"].str.split().str.len()
    summary = {
        "input_rows": input_rows,
        "usable_rows": len(working),
        "missing_text_before_normalization": missing_before,
        "empty_rows_removed": empty_removed,
        "exact_duplicates_removed": exact_duplicates,
        "near_duplicates_removed": near_removed,
        "near_duplicate_method": (
            f"64-bit trigram SimHash, Hamming distance <= {near_duplicate_distance}"
        ),
        "class_distribution": dict(sorted(Counter(working["label"]).items())),
        "article_length_words": {
            "min": int(lengths.min()),
            "median": float(lengths.median()),
            "mean": float(lengths.mean()),
            "p95": float(lengths.quantile(0.95)),
            "max": int(lengths.max()),
        },
    }
    return working, summary
