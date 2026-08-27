# bus-tracker

A minimalist Raspberry Pi dashboard for live TfL bus times and weather.

Fetches live arrivals from the TfL API and current conditions from
Open-Meteo, and renders a fullscreen kiosk-style page that refreshes
itself in the background every 30 seconds.

## Configuration

Create a `.env` file in the project root:

```
BUS_STOP_ID=490000119W
STREATFIELD_STOP_ID=490019347S
WALK_TIME_MINS=5
LAT=51.5074
LON=-0.1278
```

| Variable               | Required | Description                                                        |
| ----------------------- | -------- | -------------------------------------------------------------------- |
| `BUS_STOP_ID`           | No       | Primary TfL StopPoint ID to track. Skipped if unset.                |
| `STREATFIELD_STOP_ID`   | No       | Secondary TfL StopPoint ID. Defaults to `490019347S`.                |
| `WALK_TIME_MINS`        | No       | Minutes needed to walk to the stop; used to compute "Leave In". Defaults to `5`. |
| `LAT` / `LON`           | No       | Coordinates for the Open-Meteo weather lookup.                      |

## Running with Docker (recommended)

```
docker compose up -d --build
```

The dashboard is served on `http://<host>:5000` via gunicorn. Point a
kiosk browser (e.g. Chromium in fullscreen) at it on the Pi's display.

## Running locally

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Notes

- Bus arrivals are cached for 15 seconds and weather for 10 minutes to
  avoid hammering the upstream APIs.
- `/api/data` returns the current buses/weather as JSON and is what the
  page polls in the background — useful for debugging without reloading
  the whole dashboard.
