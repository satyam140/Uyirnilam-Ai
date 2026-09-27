import json
import os
import ssl
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
weather_cache = {}


def demo_weather(location="Pune", crop="Tomato"):
    weather = {
        "location": location,
        "temperature": 28,
        "humidity": 74,
        "rain_probability": 30,
        "wind_kmh": 12,
        "recent_rainfall_mm": 4,
        "forecast": [
            {"day": "Today", "temperature": 28, "rain_probability": 30, "summary": "Warm with light cloud cover"},
            {"day": "Tomorrow", "temperature": 27, "rain_probability": 65, "summary": "Rain likely in the afternoon"},
            {"day": "Thursday", "temperature": 29, "rain_probability": 20, "summary": "Warmer and mostly clear"},
        ],
    }
    weather["irrigation"] = irrigation_advice(weather, crop)
    return weather


def get_weather(location="Pune", crop="Tomato", live=True):
    if not live:
        return demo_weather(location, crop)
    try:
        latitude, longitude, resolved_location = geocode_location(location)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "relative_humidity_2m", "rain", "wind_speed_10m"],
            "daily": ["temperature_2m_max", "precipitation_probability_max", "precipitation_sum", "weather_code"],
            "forecast_days": 3,
            "past_days": 1,
            "timezone": "auto",
        }
        response = open_meteo_json(OPEN_METEO_URL, params)
        current = response["current"]
        daily = response["daily"]
        temperatures = daily["temperature_2m_max"]
        rain_probabilities = daily["precipitation_probability_max"]
        precipitation = daily["precipitation_sum"]
        weather_codes = daily["weather_code"]
        forecast = []
        for index in range(len(daily["time"])):
            day_name = "Today" if index == 1 else ("Tomorrow" if index == 2 else datetime.fromisoformat(daily["time"][index]).strftime("%A"))
            forecast.append({
                "day": day_name,
                "temperature": round(float(temperatures[index])),
                "rain_probability": round(float(rain_probabilities[index])),
                "summary": weather_summary(int(weather_codes[index])),
            })
        weather = {
            "location": resolved_location,
            "temperature": round(float(current["temperature_2m"])),
            "humidity": round(float(current["relative_humidity_2m"])),
            "rain_probability": forecast[1]["rain_probability"],
            "wind_kmh": round(float(current["wind_speed_10m"])),
            "recent_rainfall_mm": round(float(precipitation[0]), 1),
            "forecast": forecast[1:],
            "source": "Open-Meteo",
        }
        weather["irrigation"] = irrigation_advice(weather, crop)
        return weather
    except (KeyError, IndexError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return demo_weather(location, crop)


def open_meteo_json(url, params):
    cache_key = f"{url}?{urlencode(sorted(params.items()), doseq=True)}"
    cached = weather_cache.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]
    query = urlencode(params, doseq=True)
    context = ssl.create_default_context()
    for certificate_path in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(certificate_path):
            context = ssl.create_default_context(cafile=certificate_path)
            break
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(Request(f"{url}?{query}", headers={"User-Agent": "UyirnilamAI/1.0 weather"}), timeout=20, context=context) as response:
                payload = json.loads(response.read().decode("utf-8"))
            weather_cache[cache_key] = (time.time() + 3600, payload)
            return payload
        except (OSError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))
    raise last_error


def geocode_location(location):
    query = urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
    context = ssl.create_default_context()
    for certificate_path in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(certificate_path):
            context = ssl.create_default_context(cafile=certificate_path)
            break
    with urlopen(Request(f"{OPEN_METEO_GEOCODING_URL}?{query}", headers={"User-Agent": "UyirnilamAI/1.0 weather"}), timeout=12, context=context) as response:
        results = json.loads(response.read().decode("utf-8")).get("results", [])
    if not results:
        raise ValueError("Location could not be found")
    result = results[0]
    return float(result["latitude"]), float(result["longitude"]), result.get("name", location)


def weather_summary(code):
    summaries = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Foggy", 51: "Light drizzle", 61: "Rain likely", 63: "Moderate rain", 80: "Rain showers", 95: "Thunderstorms"}
    return summaries.get(code, "Variable conditions")


def irrigation_advice(weather, crop="Tomato", soil_moisture=None):
    rain_probability = weather["rain_probability"]
    humidity = weather["humidity"]
    temperature = weather["temperature"]
    recent_rainfall = weather.get("recent_rainfall_mm", 0)

    if soil_moisture is not None and soil_moisture > 70:
        status = "Reduce irrigation"
        reason = "Reported soil moisture is already high; check drainage before watering."
    elif rain_probability >= 60 or recent_rainfall >= 15:
        status = "Check the soil before watering"
        reason = f"Rain is likely and recent rainfall was {recent_rainfall} mm."
    elif temperature >= 32 and humidity < 60:
        status = "Increase irrigation"
        reason = "High heat and lower humidity may dry the soil faster."
    else:
        status = "Moderate irrigation recommended"
        reason = "The warm afternoon may dry the topsoil, but rain is still possible."

    return {"status": status, "reason": reason, "crop": crop, "rule_inputs": {"temperature": temperature, "humidity": humidity, "rain_probability": rain_probability, "recent_rainfall_mm": recent_rainfall}}
