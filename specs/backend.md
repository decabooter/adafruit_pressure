# Backend Spec — SQLite Database & FastAPI

## Purpose
Persist sensor readings to a local SQLite database, expose them via a REST API, and serve
the dashboard HTML. Acts as the single source of truth for all stored data.

---

## Components

| Component | Technology |
|---|---|
| Database | SQLite 3 (file-based, no server) |
| API + static server | Python 3.11+ with FastAPI + Uvicorn |

---

## Database (`backend/readings.db`)

### Schema

```sql
CREATE TABLE readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT    NOT NULL,
    ts          INTEGER NOT NULL,
    pressure_hpa REAL   NOT NULL,
    temp_c      REAL    NOT NULL
);

CREATE INDEX idx_readings_ts ON readings(ts DESC);
CREATE INDEX idx_readings_device ON readings(device_id, ts DESC);
```

- `ts` stores Unix milliseconds (matches firmware payload)
- No `created_at` column — `ts` from the device is the authoritative timestamp
- Database file lives at `backend/readings.db` (gitignored)

### Data retention
A background task (APScheduler or FastAPI lifespan) runs once per hour and deletes rows
older than 7 days:
```sql
DELETE FROM readings WHERE ts < (strftime('%s','now') - 604800) * 1000;
```

---

## Public API (FastAPI, `backend/main.py`)

Base URL: `http://localhost:8000`

### `GET /readings`

Returns recent readings as JSON.

**Query parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `last` | integer | no | Return the N most recent readings (default 60, max 1000) |
| `from` | integer | no | Start of time range, Unix ms |
| `to` | integer | no | End of time range, Unix ms |

`last` and `from`/`to` are mutually exclusive; if both are provided, return HTTP 400.

**Response (200):**
```json
{
  "count": 2,
  "readings": [
    { "id": 42, "device_id": "feather-01", "ts": 1718800005000, "pressure_hpa": 1013.30, "temp_c": 23.5 },
    { "id": 41, "device_id": "feather-01", "ts": 1718800000000, "pressure_hpa": 1013.25, "temp_c": 23.4 }
  ]
}
```

Results are ordered by `ts` descending (newest first).

**Error responses:**

| Status | Condition |
|---|---|
| 400 | Both `last` and `from`/`to` provided |
| 400 | `last` > 1000 |
| 500 | Database error |

### `GET /`

Returns the dashboard HTML page (see Dashboard Spec). Served as a static HTML file from
`backend/static/index.html`.

---

## Internal API (used by Platform subscriber, not HTTP)

`backend/db.py` exposes:

```python
def insert_reading(device_id: str, ts: int, pressure_hpa: float, temp_c: float) -> None
```

- Opens a connection, inserts the row, commits, closes
- Thread-safe (uses `check_same_thread=False` with a lock, or WAL mode)
- Raises `sqlite3.Error` on failure (caller logs and handles)

---

## Dependencies (`backend/requirements.txt`)

```
fastapi==0.111.*
uvicorn[standard]==0.30.*
apscheduler==3.*
```

---

## Error Handling

| Condition | Response |
|---|---|
| Database file missing at startup | Create it and run schema migrations automatically |
| Invalid query parameters | HTTP 400 with descriptive message |
| Database read error on API request | HTTP 500 with generic message; log full error server-side |
| Retention job failure | Log error; do not crash the API process |

---

## Acceptance Criteria

1. `INSERT` via `insert_reading()` followed by `SELECT * FROM readings ORDER BY ts DESC LIMIT 1` returns the inserted row
2. `GET /readings?last=5` returns JSON with up to 5 readings, newest first
3. `GET /readings?last=1001` returns HTTP 400
4. `GET /readings?last=5&from=0` returns HTTP 400
5. Rows older than 7 days are absent after the retention job runs
6. API starts cleanly on a machine with no existing `readings.db` (auto-creates schema)

---

## File Layout

```
backend/
  main.py                ← FastAPI app, API routes, lifespan (retention job)
  db.py                  ← SQLite connection, schema init, insert_reading()
  static/
    index.html           ← dashboard (see Dashboard Spec)
  requirements.txt
  readings.db            ← runtime database (gitignored)
```
