# Manual Test Checklist

Check off each item as it passes. Date and initial each line when done.

---

## Hardware Gate 1 — Sensor Serial Output (Phase 3)

Prereqs: BMP581 wired to Feather M0 via I2C, sketch uploaded via PlatformIO (VS Code), PlatformIO Serial Monitor open at 115200 baud (`PlatformIO: Serial Monitor` from the VS Code command palette or the plug icon in the PlatformIO toolbar).

- [x] Serial monitor shows "Ready" within 10 seconds of power-on
- [x] A JSON payload prints to serial every ~1 second (1 Hz sample rate)
- [x] `pressure_hpa` value is between 900 and 1100 (plausible for your altitude) — observed ~981 hPa
- [x] `temp_c` value is between 15 and 35 (plausible indoor temperature) — observed ~25.4 °C
- [ ] Unplugging the BMP581 (or holding SDA/SCL low) causes a halt message, not a crash/reboot loop

---

## Integration Gate 1 — Broker + Mock Publisher (Phase 4)

Prereqs: Mosquitto running (`mosquitto -c platform/mosquitto.conf`), subscriber running.

- [x] `mosquitto_sub -h localhost -u iot_user -P <pass> -t 'pressure/#'` connects successfully
- [x] Publishing a valid mock payload manually appears in the subscriber terminal:
  ```
  mosquitto_pub -h localhost -u iot_user -P <pass> \
    -t 'pressure/feather-01/reading' \
    -m '{"device_id":"feather-01","ts":1718800000000,"pressure_hpa":1013.25,"temp_c":23.4}'
  ```
- [x] Anonymous connection attempt is rejected (code 5 — Not Authorized)
- [x] Subscriber logs the received valid payload at DEBUG level
- [x] Database row count grows as messages arrive

---

## Integration Gate 2 — Feather M0 Publishes to Broker (Phase 5)

Prereqs: Gate 1 passed, Feather M0 on the same WiFi network, broker IP set in `config.h`.

- [x] Live JSON payloads from the Feather M0 flow through to the subscriber
- [x] Payload `device_id` matches the value in `config.h` ("feather-01")
- [x] Timestamp (`ts`) is within 5 seconds of current wall-clock time (NTP synced)
- [ ] Router WiFi is toggled off for 30 seconds then back on — Feather M0 reconnects and resumes publishing without a manual reset

---

## Browser Gate — Dashboard (Phase 7)

Prereqs: Full pipeline running (Feather M0 + broker + subscriber + FastAPI).

- [x] `http://localhost:8000/` loads in browser with no JS console errors
- [x] Pressure readout card shows a plausible value (~981 hPa)
- [x] Temperature readout card shows a plausible indoor temperature (~25.4 °C)
- [x] Chart populates with 5-second averaged data points over a 12-hour window
- [x] "Last update" timestamp in the header advances every ~5 seconds
- [ ] FastAPI process is stopped — dashboard shows "Connection lost — retrying…" and does not go blank or crash
- [ ] FastAPI process is restarted — dashboard recovers and resumes displaying live data within 10 seconds

---

## Sign-off

| Gate | Date | Initials | Notes |
|---|---|---|---|
| Hardware Gate 1 | 2026-06-29 | | Sensor at 0x47, 1 Hz, ~981 hPa / ~25.4 °C |
| Integration Gate 1 | 2026-06-29 | | System Mosquitto service conflict resolved |
| Integration Gate 2 | 2026-06-29 | | Board at 192.168.1.31, NTP synced |
| Browser Gate | 2026-06-29 | | Dashboard live, export CSV functional |
