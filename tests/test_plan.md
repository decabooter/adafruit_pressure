# Test Plan — Adafruit Pressure IOT POC

## Strategy

Tests are split into three tiers:

| Tier | Where | What |
|---|---|---|
| **Automated** | `pytest` on the developer laptop | Backend DB, API endpoints, subscriber validation logic, integration smoke test |
| **Manual — hardware** | Physical device + serial monitor | Sensor reads, WiFi recovery, MQTT publish confirmed on broker |
| **Manual — browser** | `http://localhost:8000/` | Dashboard renders, auto-refreshes, handles connection loss |

Automated tests run before any manual gate. A phase does not advance until its gate passes.

---

## Sequencing (matches project phases)

```
Phase 2 (now):  This test plan written ← YOU ARE HERE
Phase 3:        Hardware gate 1 — sensor serial output
Phase 4:        Integration gate 1 — broker + mock publisher
Phase 5:        Integration gate 2 — Feather M0 publishes to broker
Phase 6:        Automated suite — backend + subscriber (pytest)
                Integration gate 3 — full pipeline with mock data
Phase 7:        Hardware gate 2 + browser gate — physical sensor → dashboard
```

---

## Test Files

| File | Tier | Covers |
|---|---|---|
| `tests/test_backend.py` | Automated | DB insert, API endpoints, retention job, error responses |
| `tests/test_platform.py` | Automated | Subscriber payload validation logic |
| `tests/test_integration.py` | Automated | Publish mock MQTT → verify DB row inserted |
| `tests/manual_checklist.md` | Manual | Hardware gates, browser gate, WiFi recovery |

---

## Pass / Fail Criteria

**Automated suite:** `pytest tests/` exits 0 with zero failures before Phase 6 is marked complete.

**Hardware gates:** Each item in `manual_checklist.md` checked off by the developer.

**Browser gate:** Dashboard loads, updates, and degrades gracefully — verified visually.

---

## Running the Automated Suite

```bash
# from repo root
cd backend
pip install -r requirements.txt
pip install pytest httpx  # httpx needed for FastAPI test client

cd ..
pytest tests/ -v
```
