"""Open-Meteo (https://open-meteo.com), sin cuenta: días recientes y pronóstico de 16 días.

Se guarda cada 6 horas para no consultar en cada visita.
"""
import json
from datetime import datetime
from pathlib import Path

from backend.red import pedir_json

CARPETA_CACHE = Path(__file__).parent / "cache"


def pronostico_diario(lat, lon):
    """Devuelve {"time": [...], "temperature_2m_max": [...], "temperature_2m_min": [...],
    "precipitation_sum": [...]} desde hace 7 días hasta dentro de 16 días."""
    ahora = datetime.now()
    lat, lon = round(lat, 2), round(lon, 2)
    archivo = CARPETA_CACHE / f"openmeteo_{lat}_{lon}_{ahora:%Y%m%d}_{ahora.hour // 6}.json"
    if archivo.exists():
        return json.loads(archivo.read_text())

    datos = pedir_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": 7,
        "forecast_days": 16,
        "timezone": "auto",
    })["daily"]

    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos
