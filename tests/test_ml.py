import joblib
from sklearn.metrics import accuracy_score

from ml.src.evaluation import evaluate
from ml.src.modeling import build_pipeline


def training_data():
    texts = []
    labels = []
    terms = {
        "business": "markets shares finance company",
        "entertainment": "film actor music awards",
        "politics": "parliament election minister bill",
        "sport": "football match team goal",
        "tech": "software computer internet chip",
    }
    for label, phrase in terms.items():
        for index in range(4):
            texts.append(f"{phrase} report {index}")
            labels.append(label)
    return texts, labels


def test_pipeline_prediction_persistence_and_reproducibility(tmp_path):
    texts, labels = training_data()
    pipeline = build_pipeline("svm", {"C": 1.0})
    pipeline.fit(texts, labels)
    first = pipeline.predict(texts)
    artifact = tmp_path / "model.joblib"
    joblib.dump(pipeline, artifact)
    loaded = joblib.load(artifact)
    second = loaded.predict(texts)
    assert list(first) == list(second)
    assert set(first) <= set(labels)


def test_evaluation_metrics_are_generated():
    texts, labels = training_data()
    pipeline = build_pipeline("svm", {"C": 1.0}).fit(texts, labels)
    metrics = evaluate(pipeline, texts, labels, sorted(set(labels)), 0.01)
    assert metrics["accuracy"] == accuracy_score(labels, pipeline.predict(texts))
    assert 0 <= metrics["macro_f1"] <= 1
    assert len(metrics["confusion_matrix"]) == 5
