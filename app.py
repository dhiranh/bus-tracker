import logging
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bus-tracker")

app = Flask(__name__)
session = requests.Session()

PRIMARY_STOP_ID = os.getenv("BUS_STOP_ID")
STREATFIELD_STOP_ID = os.getenv("STREATFIELD_STOP_ID", "490019347S")
STOP_IDS = [s for s in (PRIMARY_STOP_ID, STREATFIELD_STOP_ID) if s]
STOP_MAP = {PRIMARY_STOP_ID: "R", STREATFIELD_STOP_ID: "→S"}

WALK_TIME_MINS = int(os.getenv("WALK_TIME_MINS", "5"))
LAT = os.getenv("LAT")
LON = os.getenv("LON")

BUS_CACHE_TTL = 15  # seconds
WEATHER_CACHE_TTL = 600  # seconds

WMO_MAP = {
    0: ("01d", "Clear Sky"), 1: ("01d", "Mainly Clear"), 2: ("02d", "Partly Cloudy"),
    3: ("03d", "Overcast"), 45: ("50d", "Foggy"), 48: ("50d", "Rime Fog"),
    51: ("09d", "Light Drizzle"), 53: ("09d", "Drizzle"), 55: ("09d", "Heavy Drizzle"),
    61: ("10d", "Slight Rain"), 63: ("10d", "Moderate Rain"), 65: ("10d", "Heavy Rain"),
    71: ("13d", "Slight Snow"), 73: ("13d", "Moderate Snow"), 75: ("13d", "Heavy Snow"),
    80: ("09d", "Slight Showers"), 81: ("09d", "Moderate Showers"), 82: ("09d", "Violent Showers"),
    95: ("11d", "Thunderstorm"), 96: ("11d", "Thunderstorm & Hail"),
}

_bus_cache = {"data": [], "ts": 0.0}
_weather_cache = {"data": None, "ts": 0.0}


def get_bus_data():
    now = time.monotonic()
    if now - _bus_cache["ts"] < BUS_CACHE_TTL:
        return _bus_cache["data"]

    all_arrivals = []
    for stop in STOP_IDS:
        try:
            resp = session.get(f"https://api.tfl.gov.uk/StopPoint/{stop}/Arrivals", timeout=10)
            resp.raise_for_status()
            arrivals = resp.json()
            for bus in arrivals:
                bus["originStopId"] = stop
            all_arrivals.extend(arrivals)
        except (requests.RequestException, ValueError) as e:
            log.warning("Error fetching stop %s: %s", stop, e)

    sorted_buses = sorted(all_arrivals, key=lambda x: x.get("expectedArrival", ""))[:4]

    processed = []
    for b in sorted_buses:
        try:
            arrival_dt = datetime.fromisoformat(b["expectedArrival"].replace("Z", "+00:00"))
            leave_dt = arrival_dt - timedelta(minutes=WALK_TIME_MINS)
            processed.append({
                "line": b.get("lineName", "??"),
                "dest": b.get("destinationName", "Unknown"),
                "stop_letter": STOP_MAP.get(b.get("originStopId"), ""),
                "arrival_ts": int(arrival_dt.timestamp() * 1000),
                "leave_ts": int(leave_dt.timestamp() * 1000),
            })
        except (KeyError, ValueError) as e:
            log.warning("Skipping malformed bus entry: %s", e)

    _bus_cache["data"], _bus_cache["ts"] = processed, now
    return processed


def get_weather():
    now = time.monotonic()
    if _weather_cache["data"] is not None and now - _weather_cache["ts"] < WEATHER_CACHE_TTL:
        return _weather_cache["data"]

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}&current_weather=true&timezone=Europe/London"
    )
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        curr = resp.json()["current_weather"]
        icon_code, desc = WMO_MAP.get(curr["weathercode"], ("01d", "Clear"))
        result = {
            "desc": desc,
            "temp": round(curr["temperature"]),
            "icon": f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
        }
    except (requests.RequestException, KeyError, ValueError) as e:
        log.warning("Error fetching weather: %s", e)
        result = _weather_cache["data"] or {"desc": "Error", "temp": "--", "icon": ""}

    _weather_cache["data"], _weather_cache["ts"] = result, now
    return result


@app.route("/")
def index():
    return render_template("index.html", buses=get_bus_data(), weather=get_weather())


@app.route("/api/data")
def api_data():
    return jsonify(buses=get_bus_data(), weather=get_weather())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
