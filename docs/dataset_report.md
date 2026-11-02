# Dataset report

## Selection and provenance

Phase 1 uses `SetFit/bbc-news` at revision
`9c31f7087a8c225be8b4c420d70216ef1f121eb0`. Its dataset card identifies the original BBC News
Topic Dataset: 2,225 English articles from 2004–2005 in five classes. Acquisition on 2 November
2026 verified 1,225 `train.jsonl` and 1,000 `test.jsonl` records with the expected `text`, `label`,
and `label_text` fields.

| File | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `train.jsonl` | 1,225 | 2,869,756 | `67c7468203c352fdd867cfd65a56358884b07d0bf48245e4134a6606fe43c0eb` |
| `test.jsonl` | 1,000 | 2,284,560 | `8d8c05767052607390c92a219f4c90bc571a4b005472b0aaa5bcafcd5cc08bed` |

The card does not state an open license and says BBC retains copyright in the original article
content. Therefore raw and processed text are local-only and ignored by Git. This repository stores
code, hashes, aggregated statistics, reports, and figures—not redistributed articles.

## Quality analysis

No source text or labels were missing and no empty articles were found. Conservative whitespace
normalization was applied without stemming, stop-word deletion from source text, or removal of
political terms. Global deduplication removed 101 exact content duplicates and 34 near-duplicates
detected with 64-bit word-trigram SimHash at Hamming distance ≤ 3. A total of 2,090 articles remained.

| Category | Articles |
|---|---:|
| business | 501 |
| entertainment | 366 |
| politics | 397 |
| sport | 493 |
| tech | 333 |

Document length was 90–4,492 words (median 334.5, mean 389.4, 95th percentile 741.1). Reports use
opaque article IDs rather than excerpts. The full machine-readable quality record is
`ml/results/reports/dataset_summary.json`.

## Splitting and leakage control

The SetFit source split was created by a fixed random shuffle with 1,000 test records and no
validation partition. For explicit hyperparameter isolation and stratification, Phase 1 recombines
the files only after recording their origin, removes duplicates globally, and creates a deterministic
70/15/15 split with seed 42.

| Split | Rows |
|---|---:|
| Train | 1,463 |
| Validation | 313 |
| Test | 314 |

Content hashes are asserted disjoint across all partitions. TF-IDF is fitted only within training
pipelines. Candidate hyperparameters and model choice use train/validation data; the test set is
used only for the final frozen-model report.

## Nigerian-domain relevance

BBC News is a compact engineering baseline, not Nigerian-domain evidence. It differs in geography,
time, editorial policy, vocabulary, and category balance. Candidate investigation also identified
MasakhaNEWS as a multilingual African topic dataset with English, Hausa, Igbo, Nigerian Pidgin, and
Yorùbá configurations, but its seven-label taxonomy is not directly compatible with BBC's five
labels and its licensing metadata requires separate review. It is reserved for an explicitly mapped
domain-adaptation or external-evaluation experiment.

Future Nigerian ingestion must implement `NewsSourceAdapter` only for verified, permitted APIs or
feeds, retain URL/source/publication/collection provenance, honor usage terms, deduplicate before
indexing, and never silently map incompatible taxonomies.

