"""Live Weather & City Telemetry Fetcher (Zero API key required via wttr.in / Open-Meteo)."""

import urllib.parse
import requests


def fetch_weather(city: str = "") -> dict:
    """Fetch current weather concisely for the HUD Telemetry Rail."""
    city = (city or "").strip()
    target = urllib.parse.quote(city) if city else ""
    url = f"https://wttr.in/{target}?format=j1"

    resp = requests.get(
        url,
        headers={"User-Agent": "JARVIS-HUD/2.0", "Accept": "application/json"},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()

    current = data.get("current_condition", [{}])[0]
    area = data.get("nearest_area", [{}])[0]
    area_name = (area.get("areaName", [{}])[0].get("value") or city or "Local").strip()
    desc = (current.get("weatherDesc", [{}])[0].get("value") or "Clear").strip()
    temp_c = current.get("temp_C", "--")
    feels_c = current.get("FeelsLikeC", "--")
    humidity = current.get("humidity", "--")
    wind_kph = current.get("windspeedKmph", "--")

    return {
        "city": area_name,
        "temp_c": temp_c,
        "feels_c": feels_c,
        "condition": desc,
        "humidity": humidity,
        "wind_kph": wind_kph,
        "summary": f"{area_name}: {temp_c}°C ({desc}) | Hum {humidity}% | Wind {wind_kph} km/h",
    }

