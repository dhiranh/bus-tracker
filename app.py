import os
import requests
from flask import Flask, render_template
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

WMO_MAP = {
    0: ("01d", "Clear Sky"), 1: ("01d", "Mainly Clear"), 2: ("02d", "Partly Cloudy"),
    3: ("03d", "Overcast"), 45: ("50d", "Foggy"), 48: ("50d", "Rime Fog"),
    51: ("09d", "Light Drizzle"), 53: ("09d", "Drizzle"), 55: ("09d", "Heavy Drizzle"),
    61: ("10d", "Slight Rain"), 63: ("10d", "Moderate Rain"), 65: ("10d", "Heavy Rain"),
    71: ("13d", "Slight Snow"), 73: ("13d", "Moderate Snow"), 75: ("13d", "Heavy Snow"),
    80: ("09d", "Slight Showers"), 81: ("09d", "Moderate Showers"), 82: ("09d", "Violent Showers"),
    95: ("11d", "Thunderstorm"), 96: ("11d", "Thunderstorm & Hail")
}

def get_bus_data():

    primary_stop = os.getenv('BUS_STOP_ID')
    STOP_MAP = {
        primary_stop: "R",  
        "490013329Q": "->S"  
    }
    
    stop_ids = [primary_stop, "490013329Q"]
    walk_time = int(os.getenv('WALK_TIME_MINS', 5))
    all_arrivals = []
    
    for stop in stop_ids:
        if not stop or stop == "None": continue
        try:
            url = f"https://api.tfl.gov.uk/StopPoint/{stop}/Arrivals"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for bus in data:
                    bus['originStopId'] = stop
                all_arrivals.extend(data)
        except Exception as e:
            print(f"Error: {e}")

    sorted_buses = sorted(all_arrivals, key=lambda x: x['expectedArrival'])[:4]
    
    processed_buses = []
    for b in sorted_buses:
        arrival_dt = datetime.fromisoformat(b['expectedArrival'].replace('Z', '+00:00'))
        leave_dt = arrival_dt - timedelta(minutes=walk_time)
        
        stop_id = b.get('originStopId')
        letter = STOP_MAP.get(stop_id, "")

        processed_buses.append({
            'line': b.get('lineName', '??'),
            'dest': b.get('destinationName', 'Unknown'),
            'stop_letter': letter,
            'arrival_ts': int(arrival_dt.timestamp() * 1000),
            'leave_ts': int(leave_dt.timestamp() * 1000)
        })
    return processed_buses

def get_weather():
    lat, lon = os.getenv('LAT'), os.getenv('LON')
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=Europe/London"
    try:
        data = requests.get(url, timeout=10).json()
        curr = data['current_weather']
        icon_code, desc = WMO_MAP.get(curr['weathercode'], ("01d", "Clear"))
        return {"desc": desc, "temp": round(curr['temperature']), "icon": f"https://openweathermap.org/img/wn/{icon_code}@2x.png"}
    except Exception: return {"desc": "Error", "temp": "--", "icon": ""}

@app.route('/')
def index():
    return render_template('index.html', buses=get_bus_data(), weather=get_weather())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)