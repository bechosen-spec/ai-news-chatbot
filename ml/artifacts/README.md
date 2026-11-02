# Model artifacts

`selected_model.joblib` is the trusted, locally generated deployment pipeline and includes both
TF-IDF transformation and LinearSVC inference. `model_metadata.json` records its SHA-256 hash,
dataset revision, labels, selection rule, and score semantics. The API refuses to load an artifact
whose hash does not match.

Joblib files may execute Python code during loading. Never replace this model with an untrusted
download. Candidate artifacts are reproducible and ignored by Git; rerun training to regenerate
them. If the selected artifact grows materially, publish it as a versioned release asset and verify
the same recorded hash during deployment.
