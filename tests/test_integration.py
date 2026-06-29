"""
Integration tests — verifies the full path from MQTT message to database row.
Uses a mock MQTT callback (no real broker required) to simulate a message
arriving at the subscriber, then confirms the row appears in SQLite.

Run from the repo root: pytest tests/test_integration.py -v
"""

import json
import sqlite3
import time
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "integration_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import importlib
    import backend.db as db_module
    importlib.reload(db_module)
    db_module.init_db()
    yield db_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simulate_mqtt_message(topic: str, payload_dict: dict):
    """
    Call the subscriber's on_message handler directly, bypassing the broker.
    Imports the handler from platform.subscriber and calls it with a mock
    message object carrying the given topic and JSON payload.
    """
    from ingestion.subscriber import on_message

    class FakeMsg:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload.encode("utf-8")

    on_message(client=None, userdata=None, msg=FakeMsg(topic, json.dumps(payload_dict)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMqttToDatabase:
    VALID_PAYLOAD = {
        "device_id": "feather-01",
        "ts": 1718800000000,
        "pressure_hpa": 1013.25,
        "temp_c": 23.4,
    }

    def test_valid_message_inserts_row(self, tmp_db):
        _simulate_mqtt_message("pressure/feather-01/reading", self.VALID_PAYLOAD)
        con = sqlite3.connect(tmp_db)
        rows = con.execute("SELECT device_id, ts, pressure_hpa, temp_c FROM readings").fetchall()
        con.close()
        assert len(rows) == 1
        assert rows[0] == ("feather-01", 1718800000000, 1013.25, 23.4)

    def test_multiple_messages_insert_multiple_rows(self, tmp_db):
        for i in range(3):
            payload = {**self.VALID_PAYLOAD, "ts": 1718800000000 + i * 5000}
            _simulate_mqtt_message("pressure/feather-01/reading", payload)
        con = sqlite3.connect(tmp_db)
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        con.close()
        assert count == 3

    def test_invalid_payload_does_not_insert(self, tmp_db):
        bad_payload = {"device_id": "feather-01"}  # missing required fields
        _simulate_mqtt_message("pressure/feather-01/reading", bad_payload)
        con = sqlite3.connect(tmp_db)
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        con.close()
        assert count == 0

    def test_malformed_json_does_not_crash(self, tmp_db):
        """Subscriber must handle non-JSON bytes without raising."""
        from ingestion.subscriber import on_message

        class FakeBadMsg:
            topic = "pressure/feather-01/reading"
            payload = b"not valid json {{{"

        on_message(client=None, userdata=None, msg=FakeBadMsg())
        # If we reach here, the subscriber did not crash
        con = sqlite3.connect(tmp_db)
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        con.close()
        assert count == 0

    def test_out_of_range_pressure_does_not_insert(self, tmp_db):
        payload = {**self.VALID_PAYLOAD, "pressure_hpa": 5000.0}
        _simulate_mqtt_message("pressure/feather-01/reading", payload)
        con = sqlite3.connect(tmp_db)
        count = con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        con.close()
        assert count == 0

    def test_payload_ts_preserved_exactly(self, tmp_db):
        _simulate_mqtt_message("pressure/feather-01/reading", self.VALID_PAYLOAD)
        con = sqlite3.connect(tmp_db)
        ts = con.execute("SELECT ts FROM readings").fetchone()[0]
        con.close()
        assert ts == self.VALID_PAYLOAD["ts"]
