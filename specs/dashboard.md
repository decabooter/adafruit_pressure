# Dashboard Spec — Localhost Web Interface

## Purpose
A single-page web interface served at `http://localhost:8000/` that displays live air pressure
and temperature readings pulled from the local API. No build step, no framework, no server
restart needed to update — just a static HTML file with vanilla JS.

---

## Delivery

- File: `backend/static/index.html`
- Served by FastAPI via `StaticFiles` mount at `/`
- The root route `GET /` returns this file

---

## Layout

```
┌────────────────────────────────────────────────────────────┐
│  Air Pressure Monitor    Last update: 12:34:05  [Export CSV] │
├───────────────────┬────────────────────────────────────────┤
│   1013.2 hPa      │                                        │
│   Pressure        │   [line chart — last 12 hours]         │
│                   │                                        │
│   23.4 °C         │                                        │
│   Temperature     │                                        │
└───────────────────┴────────────────────────────────────────┘
```

- Left column: two large readout cards — current pressure and current temperature
- Right column: Chart.js line chart showing all readings from the last 12 hours
- Header bar: title + timestamp of the most recent reading + Export CSV button
- No navigation, no settings, no login — read-only view

---

## Data Refresh

- On page load: fetch `GET /readings?from=<12h_ago_ms>&to=<now_ms>` immediately
- Every 5 seconds: repeat the same fetch (sliding 12-hour window) and update display in-place
- Use `setInterval` with `fetch` — no WebSocket needed for this POC
- If the fetch fails: display a subtle "Connection lost — retrying…" status in the header; keep the last known values visible

---

## Chart

- Library: Chart.js loaded from CDN (`https://cdn.jsdelivr.net/npm/chart.js`)
- Chart type: line, no fill
- X-axis: timestamp labels formatted as `HH:MM` (local time); max 8 tick labels shown
- Y-axis: pressure in hPa, auto-scaled to the data range with 5 hPa padding above/below
- Data: all readings in the last 12 hours (oldest on left, newest on right)
- No animation on update (set `animation: false`) to avoid visual jitter during live refresh

---

## Export CSV

- **Trigger**: "Export CSV" button in the header, always visible
- **Behavior**: clicking the button opens a modal overlay with two datetime pickers:
  - **From**: defaults to 24 hours before the most recent reading in the database
  - **To**: defaults to the timestamp of the most recent reading
  - Both inputs use `<input type="datetime-local">` (browser-native, no library needed)
  - The selectable range spans all data available in the database (up to 7-day retention)
- **Download**: clicking "Download" inside the modal:
  1. Fetches `GET /readings?from=<from_ms>&to=<to_ms>` for the selected window
  2. Builds a CSV with header row and one data row per reading
  3. Triggers a browser file download; filename: `pressure_<YYYY-MM-DD>.csv`
  4. Closes the modal
- **CSV columns** (in order): `timestamp`, `pressure_hpa`, `temp_c`, `device_id`
  - `timestamp` formatted as ISO 8601 local time (`YYYY-MM-DDTHH:MM:SS`)
- **Cancel**: closes the modal without downloading
- **Empty result**: if no readings exist in the selected window, show an inline error message inside the modal ("No data in this range") and do not trigger a download

---

## Styling

- Self-contained — all CSS inline in `<style>` tags, no external stylesheet
- Dark background (#1a1a2e), light text (#eaeaea)
- Readout cards use a large font (3rem) for the value, smaller (0.9rem) for the label
- Responsive to window width — cards stack vertically on narrow screens (CSS flex-wrap)
- Export modal: centered overlay with dark backdrop, same dark-card styling as the rest of the page
- No third-party CSS framework

---

## Dependencies

| Resource | Source |
|---|---|
| Chart.js | CDN (`cdn.jsdelivr.net`) — loaded at page open |

No npm, no bundler, no build step. The file must work by opening it in a browser while the
FastAPI server is running.

---

## Error States

| Condition | Display behavior |
|---|---|
| API unreachable | Header shows "Connection lost — retrying…"; last values stay visible |
| Empty database (no readings yet) | Chart is empty; readout cards show "—" instead of a value |
| Single reading (not enough for a chart) | Chart shows one point; readout cards show that reading |
| Export with no data in range | Modal shows "No data in this range"; no download triggered |

---

## Acceptance Criteria

1. Opening `http://localhost:8000/` in a browser shows the dashboard without errors in the JS console
2. Readout cards update to the latest sensor values within 6 seconds of a new reading arriving in the database
3. The chart plots all readings from the last 12 hours with timestamps on the X-axis
4. With the API stopped, the dashboard shows "Connection lost — retrying…" and does not crash
5. The page renders correctly at both 1920×1080 and 1280×800 viewport sizes
6. Clicking "Export CSV" opens the modal with From defaulting to 24h before the latest reading and To defaulting to the latest reading
7. Selecting a valid time range and clicking "Download" produces a `.csv` file with correct columns and one row per reading in that window
8. Selecting a range with no data shows "No data in this range" and does not trigger a download

---

## File Layout

```
backend/
  static/
    index.html     ← entire dashboard: HTML + inline CSS + inline JS (single file)
```
