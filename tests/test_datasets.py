import pandas as pd
import pytest

from ml.src.datasets import stratified_split, validate_frame
from ml.src.preprocessing import clean_dataset


def sample_frame() -> pd.DataFrame:
    rows = []
    for label in ("business", "entertainment", "politics", "sport", "tech"):
        for index in range(20):
            rows.append(
                {
                    "text": f"{label} unique article number {index} with sufficient words",
                    "label": label,
                }
            )
    return pd.DataFrame(rows)


def test_cleaning_removes_missing_and_exact_duplicates():
    frame = sample_frame()
    frame.loc[len(frame)] = frame.iloc[0]
    frame.loc[len(frame)] = {"text": None, "label": "tech"}
    cleaned, summary = clean_dataset(frame)
    assert summary["exact_duplicates_removed"] == 1
    assert summary["empty_rows_removed"] == 1
    assert cleaned["content_hash"].is_unique
    validate_frame(cleaned)


def test_invalid_category_is_rejected():
    frame = pd.DataFrame({"text": ["valid text"], "label": ["weather"]})
    with pytest.raises(ValueError, match="invalid categories"):
        validate_frame(frame)


def test_split_is_deterministic_and_disjoint():
    cleaned, _ = clean_dataset(sample_frame())
    first = stratified_split(cleaned)
    second = stratified_split(cleaned)
    for left, right in zip(first, second, strict=True):
        assert left["article_id"].tolist() == right["article_id"].tolist()
    hashes = [set(part["content_hash"]) for part in first]
    assert not hashes[0] & hashes[1]
    assert not hashes[0] & hashes[2]
    assert not hashes[1] & hashes[2]
