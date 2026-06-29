# Firmware Spec — Adafruit Feather M0 WiFi + BMP581

## Purpose
Read barometric pressure and temperature from the BMP581 sensor every 5 seconds and publish
the readings as JSON to a local MQTT broker over WiFi.

---

## Hardware

| Component | Details |
|---|---|
| MCU board | Adafruit Feather M0 WiFi (ATSAMD21G18 @ 48 MHz, 32 KB RAM, 256 KB flash) |
| WiFi module | ATWINC1500 (onboard), SPI-connected to the M0 |
| Sensor | Adafruit BMP581, connected via I2C (SDA = pin 20, SCL = pin 21) |
| BMP581 I2C address | 0x47 (default) |

---

## Build Tool

**PlatformIO** (VS Code extension) — no Arduino IDE required. The firmware directory includes
a `platformio.ini` that declares the board, framework, and all library dependencies. PlatformIO
downloads libraries automatically on first build.

## Dependencies (declared in `platformio.ini`, installed automatically)

| Library | Purpose |
|---|---|
| `Adafruit_BMP581` | BMP581 driver |
| `Adafruit_Sensor` | Unified sensor abstraction (BMP581 dependency) |
| `WiFi101` | ATWINC1500 WiFi driver for Feather M0 |
| `ArduinoMqttClient` | MQTT client (lightweight, no dependencies) |
| `ArduinoJson` | JSON serialization of payloads |

---

## Configuration (compile-time constants in `config.h`)

| Constant | Default | Description |
|---|---|---|
| `WIFI_SSID` | — | WiFi network name (do not hardcode in source; load from `secrets.h`) |
| `WIFI_PASS` | — | WiFi password (do not hardcode in source; load from `secrets.h`) |
| `MQTT_BROKER` | `"192.168.1.x"` | IP of the laptop running Mosquitto |
| `MQTT_PORT` | `1883` | Mosquitto default port |
| `MQTT_USER` | — | Broker username (load from `secrets.h`) |
| `MQTT_PASS` | — | Broker password (load from `secrets.h`) |
| `DEVICE_ID` | `"feather-01"` | Unique identifier for this device |
| `READ_INTERVAL_MS` | `5000` | Milliseconds between sensor reads |

`secrets.h` must be listed in `.gitignore` and never committed.

---

## Behavior

### Startup sequence
1. Initialize serial at 115200 baud
2. Initialize BMP581 over I2C — if not found, print error to serial and halt (`while(1)`)
3. Configure BMP581 oversampling: pressure OSR x16, temperature OSR x2, IIR filter coeff 3
4. Connect to WiFi — print status to serial; block until connected (with 10-second retry loop)
5. Connect to MQTT broker — if connection fails, retry every 5 seconds indefinitely
6. Print "Ready" to serial

### Main loop (every `READ_INTERVAL_MS`)
1. Read pressure and temperature from BMP581
2. Validate readings: pressure must be 800–1200 hPa, temp must be −40–85 °C; if out of range, log to serial and skip publish
3. Build JSON payload (see Payload section)
4. Check MQTT connection; reconnect if dropped
5. Publish payload to topic `pressure/{DEVICE_ID}/reading`
6. Print published payload to serial for debugging

---

## Payload Schema

```json
{
  "device_id": "feather-01",
  "ts": 1718800000000,
  "pressure_hpa": 1013.25,
  "temp_c": 23.4
}
```

| Field | Type | Description |
|---|---|---|
| `device_id` | string | Value of `DEVICE_ID` constant |
| `ts` | integer | Milliseconds since Unix epoch (from `WiFi.getTime()` via NTP) |
| `pressure_hpa` | float (2 dp) | Pressure in hectopascals |
| `temp_c` | float (1 dp) | Temperature in degrees Celsius |

---

## Error Handling

| Condition | Response |
|---|---|
| BMP581 not detected at startup | Serial error + `while(1)` halt |
| Reading out of valid range | Log to serial, skip publish, continue loop |
| WiFi drops during operation | Attempt reconnect before next publish; log each attempt |
| MQTT broker unreachable | Retry connection every 5 seconds; do not drop readings silently |
| NTP time unavailable | Use `millis()` offset from a fixed epoch as fallback; log warning |

---

## Acceptance Criteria

1. Serial monitor shows a valid JSON payload every 5 seconds with plausible hPa values (900–1100 for typical indoor altitude)
2. Payload appears on the broker: `mosquitto_sub -t 'pressure/#'` shows the message within 1 second of the serial print
3. Device recovers WiFi connection automatically after router restart without requiring a manual reset
4. Sketch compiles with zero errors and zero warnings via PlatformIO in VS Code with the Feather M0 environment configured

---

## File Layout

```
firmware/
  platformio.ini              ← board, framework, library declarations
  src/
    feather_pressure.ino      ← main sketch
    config.h                  ← all constants except secrets
    secrets.h                 ← WiFi + MQTT credentials (gitignored)
```
