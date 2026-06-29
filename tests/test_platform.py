"""
Platform tests — covers the subscriber's payload validation logic in isolation.
No MQTT broker required; tests import and call the validation function directly.
Run from the repo root: pytest tests/test_platform.py -v
"""

import json
import pytest


# Import the validation function from the subscriber module.
# It must be a pure function: validate_payload(dict) -> bool
from ingestion.subscriber import validate_payload


# ---------------------------------------------------------------------------
# Valid payloads
# ---------------------------------------------------------------------------

class TestValidPayloads:
    def test_nominal_reading(self):
        payload = {
            "device_id": "feather-01",
            "ts": 1718800000000,
            "pressure_hpa": 1013.25,
            "temp_c": 23.4,
        }
        assert validate_payload(payload) is True

    def test_pressure_at_lower_bound(self):
        payload = {"device_id": "feather-01", "ts": 1, "pressure_hpa": 800.0, "temp_c": 0.0}
        assert validate_payload(payload) is True

    def test_pressure_at_upper_bound(self):
        payload = {"device_id": "feather-01", "ts": 1, "pressure_hpa": 1200.0, "temp_c": 0.0}
        assert validate_payload(payload) is True

    def test_temp_at_lower_bound(self):
        payload = {"device_id": "feather-01", "ts": 1, "pressure_hpa": 1013.0, "temp_c": -40.0}
        assert validate_payload(payload) is True

    def test_temp_at_upper_bound(self):
        payload = {"device_id": "feather-01", "ts": 1, "pressure_hpa": 1013.0, "temp_c": 85.0}
        assert validate_payload(payload) is True


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------

class TestMissingFields:
    BASE = {"device_id": "feather-01", "ts": 1718800000000, "pressure_hpa": 1013.0, "temp_c": 23.0}

    @pytest.mark.parametrize("field", ["device_id", "ts", "pressure_hpa", "temp_c"])
    def test_missing_required_field(self, field):
        payload = {k: v for k, v in self.BASE.items() if k != field}
        assert validate_payload(payload) is False


# ---------------------------------------------------------------------------
# Invalid types / values
# ---------------------------------------------------------------------------

class TestInvalidValues:
    def test_empty_device_id(self):
        assert validate_payload({"device_id": "", "ts": 1, "pressure_hpa": 1013.0, "temp_c": 23.0}) is False

    def test_non_string_device_id(self):
        assert validate_payload({"device_id": 42, "ts": 1, "pressure_hpa": 1013.0, "temp_c": 23.0}) is False

    def test_zero_ts(self):
        assert validate_payload({"device_id": "feather-01", "ts": 0, "pressure_hpa": 1013.0, "temp_c": 23.0}) is False

    def test_negative_ts(self):
        assert validate_payload({"device_id": "feather-01", "ts": -1, "pressure_hpa": 1013.0, "temp_c": 23.0}) is False

    def test_pressure_too_low(self):
        assert validate_payload({"device_id": "feather-01", "ts": 1, "pressure_hpa": 799.9, "temp_c": 23.0}) is False

    def test_pressure_too_high(self):
        assert validate_payload({"device_id": "feather-01", "ts": 1, "pressure_hpa": 1200.1, "temp_c": 23.0}) is False

    def test_temp_too_low(self):
        assert validate_payload({"device_id": "feather-01", "ts": 1, "pressure_hpa": 1013.0, "temp_c": -40.1}) is False

    def test_temp_too_high(self):
        assert validate_payload({"device_id": "feather-01", "ts": 1, "pressure_hpa": 1013.0, "temp_c": 85.1}) is False

    def test_pressure_is_string(self):
        assert validate_payload({"device_id": "feather-01", "ts": 1, "pressure_hpa": "1013.0", "temp_c": 23.0}) is False

    def test_not_a_dict(self):
        assert validate_payload("not a dict") is False

    def test_none(self):
        assert validate_payload(None) is False
