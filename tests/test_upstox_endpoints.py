import json
import pytest
from fastapi.testclient import TestClient

from main import app
from app.config import config


def test_request_rotation_and_webhook(monkeypatch):
    """Test /upstox/request-rotation (mocked) and /upstox/webhook endpoints."""

    # Ensure Upstox is enabled for the endpoint logic
    monkeypatch.setattr(config, "UPSTOX_ENABLED", True)

    # Monkeypatch the token manager to return a fake token without external calls
    class DummyManager:
        async def request_access_token_via_api(self):
            return {"success": True, "response": {"access_token": "fake-token-123"}}

    monkeypatch.setattr("app.upstox_token_manager.UpstoxTokenManager", lambda: DummyManager())

    client = TestClient(app)

    # Call request-rotation
    resp = client.post("/upstox/request-rotation")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("access_token") == "fake-token-123"

    # Call webhook with sample payload
    payload = {"event": "order_update", "order_id": "ORD123", "status": "FILLED"}
    resp2 = client.post("/upstox/webhook", json=payload)
    assert resp2.status_code == 200
    assert resp2.json().get("status") == "received"


def test_env_persistence(monkeypatch, tmp_path):
    """Ensure /upstox/request-rotation persists UPSTOX_ACCESS_TOKEN into .env"""

    # Enable Upstox for the endpoint logic
    monkeypatch.setattr(config, "UPSTOX_ENABLED", True)

    # Dummy manager returns a token
    class DummyManager:
        async def request_access_token_via_api(self):
            return {"success": True, "response": {"access_token": "persist-token-456"}}

    monkeypatch.setattr("app.upstox_token_manager.UpstoxTokenManager", lambda: DummyManager())

    # Create a fake project layout so main.py's env resolution writes to tmp_path/.env
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    fake_main = project_dir / "main.py"
    fake_main.write_text("# fake main")

    env_file = tmp_path / ".env"
    env_file.write_text("UPSTOX_ACCESS_TOKEN=old-token\n")

    # Monkeypatch os.path.abspath to point to our fake main.py path
    monkeypatch.setattr("os.path.abspath", lambda _: str(fake_main))

    client = TestClient(app)
    resp = client.post("/upstox/request-rotation")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("access_token") == "persist-token-456"

    # Confirm .env was updated at tmp_path/.env
    content = env_file.read_text()
    assert 'UPSTOX_ACCESS_TOKEN="persist-token-456"' in content
