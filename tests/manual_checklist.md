# Manual Test Checklist

Check off each item as it passes. Date and initial each line when done.

---

## Hardware Gate 1 — Sensor Serial Output (Phase 3)

Prereqs: BMP581 wired to Feather M0 via I2C, sketch uploaded via PlatformIO (VS Code), PlatformIO Serial Monitor open at 115200 baud (`PlatformIO: Serial Monitor` from the VS Code command palette or the plug icon in the PlatformIO toolbar).

- [ ] Serial monitor shows "Ready" within 10 seconds of power-on
- [ ] A JSON payload prints to serial every ~5 seconds
- [ ] `pressure_hpa` value is between 900 and 1100 (plausible for your altitude)
- [ ] `temp_c` value is between 15 and 35 (plausible indoor temperature)
- [ ] Unplugging the BMP581 (or holding SDA/SCL low) causes a halt message, not a crash/reboot loop

---

## Integration Gate 1 — Broker + Mock Publisher (Phase 4)

Prereqs: Mosquitto running (`mosquitto -c platform/mosquitto.conf`), subscriber running.

- [ ] `mosquitto_sub -h localhost -u iot_user -P <pass> -t 'pressure/#'` connects successfully
- [ ] Publishing a valid mock payload manually appears in the subscriber terminal:
  ```
  mosquitto_pub -h localhost -u iot_user -P <pass> \
    -t 'pressure/feather-01/reading' \
    -m '{"device_id":"feather-01","ts":1718800000000,"pressure_hpa":1013.25,"temp_c":23.4}'
  ```
- [ ] Anonymous connection attempt is rejected:
  ```
  mosquitto_pub -h localhost -t 'pressure/test/reading' -m 'test'
  # Expected: Connection Refused error
  ```
- [ ] Subscriber logs the received valid payload at DEBUG level
- [ ] `SELECT COUNT(*) FROM backend/readings.db` (via `sqlite3`) shows 1 row after the mock publish

---

## Integration Gate 2 — Feather M0 Publishes to Broker (Phase 5)

Prereqs: Gate 1 passed, Feather M0 on the same WiFi network, broker IP set in `config.h`.

- [ ] `mosquitto_sub -t 'pressure/#'` shows live JSON payloads from the Feather M0
- [ ] Payload `device_id` matches the value in `config.h`
- [ ] Timestamp (`ts`) is within 5 seconds of current wall-clock time
- [ ] Router WiFi is toggled off for 30 seconds then back on — Feather M0 reconnects and resumes publishing without a manual reset

---

## Browser Gate — Dashboard (Phase 7)

Prereqs: Full pipeline running (Feather M0 + broker + subscriber + FastAPI).

- [ ] `http://localhost:8000/` loads in browser with no JS console errors
- [ ] Pressure readout card shows a value within 2 hPa of a reference barometer (phone weather app is acceptable)
- [ ] Temperature readout card shows a plausible indoor temperature
- [ ] Sparkline chart populates with data points within 10 seconds of page load
- [ ] "Last update" timestamp in the header advances every ~5 seconds
- [ ] FastAPI process is stopped — dashboard shows "Connection lost — retrying…" and does not go blank or crash
- [ ] FastAPI process is restarted — dashboard recovers and resumes displaying live data within 10 seconds

---

## Sign-off

| Gate | Date | Initials | Notes |
|---|---|---|---|
| Hardware Gate 1 | | | |
| Integration Gate 1 | | | |
| Integration Gate 2 | | | |
| Browser Gate | | | |
