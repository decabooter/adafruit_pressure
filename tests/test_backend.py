"""
Backend tests — covers db.py (insert_reading) and FastAPI routes.
Run from the repo root: pytest tests/test_backend.py -v
Requires: pip install pytest httpx fastapi
"""

import sqlite3
import tempfile
import os
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """Point the backend at a fresh temp database for each test."""
    db_path = str(tmp_path / "test_readings.db")
    monkeypatch.setenv("DB_PATH", db_path)
    # Import after env var is set so the module picks up the override
    import importlib
    import backend.db as db_module
    importlib.reload(db_module)
    db_module.init_db()
    yield db_path
    # tmp_path cleanup is automatic


@pytest.fixture()
def client(tmp_db):
    """FastAPI test client wired to the temp database."""
    import importlib
    import backend.main as main_module
    importlib.reload(main_module)
    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# DB layer — insert_reading
# ---------------------------------------------------------------------------

class TestInsertReading:
    def test_inserts_row(self, tmp_db):
        from backend.db import insert_reading
        insert_reading("feather-01", 1718800000000, 1013.25, 23.4)
        con = sqlite3.connect(tmp_db)
        row = con.execute("SELECT device_id, ts, pressure_hpa, temp_c FROM readings").fetchone()
        con.close()
        assert row == ("feather-01", 1718800000000, 1013.25, 23.4)

    def test_multiple_rows_accumulate(self, tmp_db):
        from backend.db import insert_reading
        insert_reading("feather-01", 1718800000000, 1013.0, 23.0)
        insert_reading("feather-01", 1718800005000, 1013.1, 23.1)
        con = sqlite3.connect(tmp_db)
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        con.close()
        assert count == 2

    def test_schema_auto_created_on_fresh_db(self, tmp_path, monkeypatch):
        """init_db() should create the table if the file does not exist."""
        db_path = str(tmp_path / "brand_new.db")
        monkeypatch.setenv("DB_PATH", db_path)
        import importlib
        import backend.db as db_module
        importlib.reload(db_module)
        db_module.init_db()
        assert os.path.exists(db_path)
        con = sqlite3.connect(db_path)
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        con.close()
        assert ("readings",) in tables


# ---------------------------------------------------------------------------
# API — GET /readings
# ---------------------------------------------------------------------------

class TestGetReadings:
    def _seed(self, tmp_db, n=5):
        from backend.db import insert_reading
        for i in range(n):
            insert_reading("feather-01", 1718800000000 + i * 5000, 1013.0 + i * 0.1, 23.0 + i * 0.1)

    def test_returns_json_with_count(self, client, tmp_db):
        self._seed(tmp_db, 3)
        resp = client.get("/readings?last=3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 3
        assert len(body["readings"]) == 3

    def test_default_last_is_60(self, client, tmp_db):
        self._seed(tmp_db, 100)
        resp = client.get("/readings")
        assert resp.status_code == 200
        assert resp.json()["count"] == 60

    def test_last_caps_at_1000(self, client, tmp_db):
        resp = client.get("/readings?last=1001")
        assert resp.status_code == 400

    def test_last_and_from_together_is_400(self, client, tmp_db):
        resp = client.get("/readings?last=5&from=0")
        assert resp.status_code == 400

    def test_results_ordered_newest_first(self, client, tmp_db):
        self._seed(tmp_db, 3)
        readings = client.get("/readings?last=3").json()["readings"]
        timestamps = [r["ts"] for r in readings]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_from_to_range_query(self, client, tmp_db):
        self._seed(tmp_db, 5)
        # Rows 1 and 2 (index 1 and 2) have ts 1718800005000 and 1718800010000
        resp = client.get("/readings?from=1718800005000&to=1718800010000")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        for r in body["readings"]:
            assert 1718800005000 <= r["ts"] <= 1718800010000

    def test_empty_db_returns_empty_list(self, client, tmp_db):
        resp = client.get("/readings?last=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["readings"] == []

    def test_reading_fields_present(self, client, tmp_db):
        self._seed(tmp_db, 1)
        reading = client.get("/readings?last=1").json()["readings"][0]
        assert "id" in reading
        assert "device_id" in reading
        assert "ts" in reading
        assert "pressure_hpa" in reading
        assert "temp_c" in reading


# ---------------------------------------------------------------------------
# API — GET / (dashboard)
# ---------------------------------------------------------------------------

class TestDashboardRoute:
    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Data retention
# ---------------------------------------------------------------------------

class TestRetention:
    def test_old_rows_deleted(self, tmp_db):
        from backend.db import insert_reading, delete_old_readings
        # Insert one row from 8 days ago and one from 1 hour ago
        import time
        now_ms = int(time.time() * 1000)
        old_ts = now_ms - (8 * 24 * 3600 * 1000)
        recent_ts = now_ms - (3600 * 1000)
        insert_reading("feather-01", old_ts, 1010.0, 22.0)
        insert_reading("feather-01", recent_ts, 1013.0, 23.0)

        delete_old_readings()

        con = sqlite3.connect(tmp_db)
        rows = con.execute("SELECT ts FROM readings").fetchall()
        con.close()
        tss = [r[0] for r in rows]
        assert old_ts not in tss
        assert recent_ts in tss
