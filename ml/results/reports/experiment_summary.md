# Experiment summary

On the 314-article held-out test split, TF-IDF + LinearSVC achieved 0.9809 accuracy and 0.9800 macro
F1; TF-IDF + Random Forest achieved 0.9618 accuracy and 0.9608 macro F1. LinearSVC `C=0.5` was frozen
from validation macro F1 and selected for deployment. See `docs/experiment_report.md` and the JSON/CSV
files under `ml/results/metrics` for complete measured results.

