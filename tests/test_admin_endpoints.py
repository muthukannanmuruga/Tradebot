import os
import pytest
from httpx import AsyncClient

# Use an in-memory SQLite DB for tests to avoid external Postgres dependency
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as adb

# Create test engine/session and patch the app's DB objects
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
adb.engine = engine
adb.SessionLocal = TestSession
# Create all tables in-memory
adb.Base.metadata.create_all(bind=engine)

from main import app


@pytest.mark.asyncio
async def test_admin_view_and_toggle():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Read current view
        r = await ac.get("/admin/view-environment")
        assert r.status_code == 200
        data = r.json()
        assert "binance" in data and "upstox" in data

        # Toggle binance to 'live'
        r2 = await ac.post("/admin/toggle-view", params={"market": "binance", "view": "live"})
        assert r2.status_code == 200
        assert r2.json().get("view") == "live"

        # Verify persisted
        r3 = await ac.get("/admin/view-environment")
        assert r3.status_code == 200
        assert r3.json().get("binance") == "live"
