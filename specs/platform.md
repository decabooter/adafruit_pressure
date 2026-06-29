# Platform Spec — MQTT Broker & Subscriber

## Purpose
Receive sensor readings published by the Feather M0, validate them against the payload schema,
and write them to the SQLite database owned by the Backend layer.

---

## Components

| Component | Technology | Runs on |
|---|---|---|
| MQTT broker | Mosquitto 2.x | Developer laptop (localhost) |
| MQTT subscriber | Python 3.11+ with `paho-mqtt` | Developer laptop (same machine) |

---

## Mosquitto Broker

### Configuration (`ingestion/mosquitto.conf`)

```
listener 1883
allow_anonymous false
password_file /path/to/ingestion/mosquitto.passwd
```

- Binds to all interfaces on port 1883
- Anonymous connections rejected — credentials required
- TLS not required for localhost POC; add if broker becomes network-accessible

### Credentials

- One user: `iot_user` with a strong password
- Generated with `mosquitto_passwd -c ingestion/mosquitto.passwd iot_user`
- Password file must be listed in `.gitignore` and never committed
- The same credentials are placed in `firmware/secrets.h` for the Feather M0

### Topic design

| Topic pattern | Publisher | Subscriber |
|---|---|---|
| `pressure/{device_id}/reading` | Feather M0 | Python subscriber |

Wildcard subscription: `pressure/+/reading` (catches all device IDs).

---

## Python Subscriber (`ingestion/subscriber.py`)

### Dependencies (`ingestion/requirements.txt`)

```
paho-mqtt==2.*
```

### Behavior

1. Connect to Mosquitto at `localhost:1883` with credentials from environment variables:
   - `MQTT_USER`, `MQTT_PASS`
2. Subscribe to `pressure/+/reading` with QoS 1
3. On each message received:
   a. Parse JSON payload
   b. Validate schema (see Validation section)
   c. On valid payload: call `backend.db.insert_reading(payload)` (imported from backend layer)
   d. On invalid payload: log error with raw message content; do not insert
4. On disconnect: log and attempt reconnect with 5-second backoff, up to indefinite retries
5. Log every received message at DEBUG level; log errors at ERROR level

### Validation

A payload is valid if and only if:
- It is parseable JSON
- `device_id` is a non-empty string
- `ts` is an integer > 0
- `pressure_hpa` is a float between 800 and 1200
- `temp_c` is a float between −40 and 85

Invalid payloads are logged and discarded; they do not crash the subscriber.

---

## Interface Contracts

**Input (from Firmware Agent):**
```json
{ "device_id": "feather-01", "ts": 1718800000000, "pressure_hpa": 1013.25, "temp_c": 23.4 }
```

**Output (to Backend Agent):**
Calls `insert_reading(device_id, ts, pressure_hpa, temp_c)` — function defined in `backend/db.py`.

---

## Error Handling

| Condition | Response |
|---|---|
| Broker not reachable at startup | Log error, retry every 5 seconds |
| Malformed JSON message | Log and discard; do not crash |
| Schema validation failure | Log with raw payload; do not insert |
| Database write failure | Log error with payload; do not crash subscriber |

---

## Acceptance Criteria

1. `mosquitto_sub -h localhost -u iot_user -P <pass> -t 'pressure/#'` receives messages published by the Feather M0
2. Anonymous connection attempt (`mosquitto_pub` without credentials) is rejected with CONNACK code 5
3. Subscriber inserts a row into SQLite for every valid message received (verify with `SELECT COUNT(*) FROM readings`)
4. Subscriber logs and discards a malformed JSON message without exiting
5. Subscriber reconnects automatically within 10 seconds of a broker restart

---

## File Layout

```
ingestion/
  mosquitto.conf         ← broker config
  mosquitto.passwd       ← generated credential file (gitignored)
  subscriber.py          ← MQTT subscriber process
  requirements.txt       ← paho-mqtt
  start.sh               ← convenience script: starts mosquitto + subscriber together
```
