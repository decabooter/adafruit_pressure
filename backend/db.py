import os
import sqlite3
import threading
import time
from pathlib import Path

_DEFAULT_DB = str(Path(__file__).parent / "readings.db")
DB_PATH = os.environ.get("DB_PATH", _DEFAULT_DB)
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db() -> None:
    with _lock:
        con = _connect()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS readings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id    TEXT    NOT NULL,
                ts           INTEGER NOT NULL,
                pressure_hpa REAL    NOT NULL,
                temp_c       REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_readings_ts     ON readings(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_readings_device ON readings(device_id, ts DESC);
        """)
        con.commit()
        con.close()


def insert_reading(device_id: str, ts: int, pressure_hpa: float, temp_c: float) -> None:
    with _lock:
        con = _connect()
        try:
            con.execute(
                "INSERT INTO readings (device_id, ts, pressure_hpa, temp_c) VALUES (?, ?, ?, ?)",
                (device_id, ts, pressure_hpa, temp_c),
            )
            con.commit()
        finally:
            con.close()


def delete_old_readings() -> None:
    cutoff_ms = (int(time.time()) - 7 * 24 * 3600) * 1000
    with _lock:
        con = _connect()
        try:
            con.execute("DELETE FROM readings WHERE ts < ?", (cutoff_ms,))
            con.commit()
        finally:
            con.close()


def get_readings_last(n: int) -> list:
    with _lock:
        con = _connect()
        try:
            rows = con.execute(
                "SELECT id, device_id, ts, pressure_hpa, temp_c "
                "FROM readings ORDER BY ts DESC LIMIT ?",
                (n,),
            ).fetchall()
        finally:
            con.close()
    return [_row_to_dict(r) for r in rows]


def get_readings_bucketed(from_ts: int, to_ts: int, bucket_ms: int) -> list:
    with _lock:
        con = _connect()
        try:
            rows = con.execute(
                "SELECT (ts / ?) * ? AS bucket_ts, "
                "AVG(pressure_hpa) AS pressure_hpa, "
                "AVG(temp_c) AS temp_c "
                "FROM readings WHERE ts >= ? AND ts <= ? "
                "GROUP BY ts / ? "
                "ORDER BY bucket_ts DESC",
                (bucket_ms, bucket_ms, from_ts, to_ts, bucket_ms),
            ).fetchall()
        finally:
            con.close()
    return [{"ts": int(r[0]), "pressure_hpa": round(r[1], 4), "temp_c": round(r[2], 2)} for r in rows]


def get_readings_range(from_ts: int, to_ts: int) -> list:
    with _lock:
        con = _connect()
        try:
            rows = con.execute(
                "SELECT id, device_id, ts, pressure_hpa, temp_c "
                "FROM readings WHERE ts >= ? AND ts <= ? ORDER BY ts DESC",
                (from_ts, to_ts),
            ).fetchall()
        finally:
            con.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    return {
        "id": row[0], "device_id": row[1], "ts": row[2],
        "pressure_hpa": row[3], "temp_c": row[4],
    }
