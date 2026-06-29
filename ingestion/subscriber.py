import json
import logging
import os
import sys

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)

BROKER = "localhost"
PORT   = 1883
TOPIC  = "pressure/+/reading"


def validate_payload(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    try:
        device_id    = payload.get("device_id")
        ts           = payload.get("ts")
        pressure_hpa = payload.get("pressure_hpa")
        temp_c       = payload.get("temp_c")

        if not isinstance(device_id, str) or not device_id:
            return False
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or ts <= 0:
            return False
        if isinstance(pressure_hpa, bool) or not isinstance(pressure_hpa, (int, float)):
            return False
        if isinstance(temp_c, bool) or not isinstance(temp_c, (int, float)):
            return False
        if not (800.0 <= float(pressure_hpa) <= 1200.0):
            return False
        if not (-40.0 <= float(temp_c) <= 85.0):
            return False
        return True
    except Exception:
        return False


def on_message(client, userdata, msg):
    # Lazy import so this module is importable before backend/ exists (e.g. during testing)
    import backend.db as _db

    try:
        payload = json.loads(msg.payload)
    except (json.JSONDecodeError, ValueError) as exc:
        log.error("Malformed JSON on %s: %s | raw: %s", msg.topic, exc, msg.payload)
        return

    log.debug("Received: %s", payload)

    if not validate_payload(payload):
        log.error("Payload failed validation: %s", payload)
        return

    try:
        _db.insert_reading(
            payload["device_id"],
            int(payload["ts"]),
            float(payload["pressure_hpa"]),
            float(payload["temp_c"]),
        )
    except Exception as exc:
        log.error("DB write failed: %s | payload: %s", exc, payload)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("Connected. Subscribing to %s", TOPIC)
        client.subscribe(TOPIC, qos=1)
    else:
        log.error("Connection refused (code %d)", rc)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        log.warning("Unexpected disconnect (code %d)", rc)


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

    user     = os.environ.get("MQTT_USER")
    password = os.environ.get("MQTT_PASS")
    if not user or not password:
        log.error("Set MQTT_USER and MQTT_PASS environment variables before starting.")
        sys.exit(1)

    client = mqtt.Client()
    client.username_pw_set(user, password)
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=5, max_delay=30)

    log.info("Connecting to %s:%d", BROKER, PORT)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
