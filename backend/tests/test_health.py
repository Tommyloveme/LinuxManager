from pathlib import Path

from fastapi.testclient import TestClient


def test_health(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CEDAR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CEDAR_SECRET_KEY", "test-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["ok"] is True
