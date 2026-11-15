"""Consultas a NASA POWER (https://power.larc.nasa.gov), sin cuenta.

- La conexión (IPv4 + reintentos) está en backend/red.py.
- Guarda en disco lo que descarga: el clima histórico no cambia, así que
  solo se le pide a la NASA la primera vez para cada zona.
"""
import json
from datetime import date, timedelta
from pathlib import Path

from backend.red import pedir_json

URL_DIARIO = "https://power.larc.nasa.gov/api/temporal/daily/point"
CARPETA_CACHE = Path(__file__).parent / "cache"

# 30 años completos de datos diarios
AÑO_INICIO, AÑO_FIN = 1995, 2024
VALOR_VACIO = -999  # así marca NASA POWER los días sin dato


def clima_diario_historico(lat, lon):
    """Temperatura máxima, mínima y lluvia de cada día de los últimos 30 años.

    Devuelve {"T2M_MAX": {"19950101": 25.3, ...}, "T2M_MIN": {...}, "PRECTOTCORR": {...}}
    """
    # Redondeamos a 0.1° (~11 km): NASA POWER usa cuadros de ~50 km,
    # así que parcelas vecinas comparten los mismos datos guardados.
    lat, lon = round(lat, 1), round(lon, 1)
    archivo = CARPETA_CACHE / f"power_diario_{lat}_{lon}_{AÑO_INICIO}_{AÑO_FIN}.json"

    if archivo.exists():
        return json.loads(archivo.read_text())

    datos = pedir_json(URL_DIARIO, {
        "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": f"{AÑO_INICIO}0101",
        "end": f"{AÑO_FIN}1231",
        "format": "JSON",
    })["properties"]["parameter"]

    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos


def humedad_suelo_historica(lat, lon):
    """Humedad del suelo en la zona de raíces (GWETROOT, 0 = seca, 1 = saturada),
    día por día, de los últimos 30 años. Sirve para saber qué es "normal" en cada época."""
    lat, lon = round(lat, 1), round(lon, 1)
    archivo = CARPETA_CACHE / f"power_humedad_{lat}_{lon}_{AÑO_INICIO}_{AÑO_FIN}.json"
    if archivo.exists():
        return json.loads(archivo.read_text())

    datos = pedir_json(URL_DIARIO, {
        "parameters": "GWETROOT",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": f"{AÑO_INICIO}0101",
        "end": f"{AÑO_FIN}1231",
        "format": "JSON",
    })["properties"]["parameter"]["GWETROOT"]

    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos


def humedad_suelo_reciente(lat, lon, dias=45):
    """Humedad del suelo de los últimos días. NASA POWER tiene ~3 días de retraso,
    así que los más recientes vienen vacíos (-999). Se guarda un archivo por día."""
    hoy = date.today()
    lat, lon = round(lat, 1), round(lon, 1)
    archivo = CARPETA_CACHE / f"power_humedad_reciente_{lat}_{lon}_{hoy:%Y%m%d}.json"
    if archivo.exists():
        return json.loads(archivo.read_text())

    datos = pedir_json(URL_DIARIO, {
        "parameters": "GWETROOT",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": f"{hoy - timedelta(days=dias):%Y%m%d}",
        "end": f"{hoy:%Y%m%d}",
        "format": "JSON",
    })["properties"]["parameter"]["GWETROOT"]

    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos
