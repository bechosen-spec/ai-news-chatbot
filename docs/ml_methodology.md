# Machine-learning methodology

## Problem definition

Given article text \(x\), learn a supervised function \(f(x)\) over five mutually exclusive topic
labels. This is topic classification, not misinformation, bias, stance, or factuality detection.

## Representation

Each pipeline applies Unicode accent normalization, lowercasing, English stop-word filtering, and
TF-IDF word unigrams/bigrams. Terms must occur in at least two training articles, terms occurring in
more than 95% of training articles are excluded, and sublinear term frequency is used:

\[
\operatorname{tfidf}(t,d) = (1 + \log \operatorname{tf}(t,d))
\log\left(\frac{1 + N}{1 + \operatorname{df}(t)}\right).
\]

The vectorizer is part of each scikit-learn `Pipeline`, so it is fitted only on training data and is
serialized with the classifier. Linear SVM uses at most 20,000 features; Random Forest uses at most
8,000 to constrain memory and tree cost.

## Models and bounded selection

Linear SVM minimizes a regularized hinge-loss objective. `LinearSVC` candidates use balanced class
weights and \(C \in \{0.5, 1.0, 2.0\}\). Random Forest candidates use 200 trees, balanced bootstrap
class weights, square-root feature sampling, and `max_depth` of 40 or unlimited. All stochastic
components use seed 42 and run on CPU.

Candidates fit on 70% training data and are selected by macro F1 on the 15% validation set. The
chosen configuration is refitted on train + validation. Only then are both frozen model families
evaluated once on the 15% test set. Deployment model choice is frozen from validation performance;
test metrics are final evidence, not a tuning signal.

## Metrics and reproducibility

Accuracy, macro precision/recall/F1, weighted F1, per-class precision/recall/F1/support, confusion
matrices, fit duration, batch inference duration, per-article latency, and serialized size are saved.
Macro F1 weights every category equally:

\[
F1_{macro}=\frac{1}{K}\sum_{k=1}^{K}\frac{2P_kR_k}{P_k+R_k}.
\]

The experiment manifest records timestamps, dataset content hash, split counts, candidates, selected
parameters, Python/platform/scikit-learn versions, CPU count, seed, and Git SHA. Dependency versions
are pinned. Timings are local measurements and will vary by machine.

`LinearSVC.decision_function` values are signed margins, not probabilities. The API labels them as
such and makes no calibration claim. A future calibration study must fit calibration only on training
data and evaluate reliability separately before exposing probabilities.

