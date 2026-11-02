from backend.app.core.config import Settings


def test_comma_separated_allowed_origins(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example, https://b.example")
    assert Settings().allowed_origins == ["https://a.example", "https://b.example"]
