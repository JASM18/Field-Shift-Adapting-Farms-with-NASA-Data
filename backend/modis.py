"""MODIS (NASA): qué tan verde está la vegetación (NDVI), vía el servicio del
ORNL DAAC, sin cuenta. https://modis.ornl.gov/data/modis_webservice.html

El servidor es lento y a veces falla: cada imagen consultada se guarda para siempre
(una imagen vieja no cambia) y la lista de fechas se guarda por día.
"""
import json
from datetime import date
from pathlib import Path

from backend.red import pedir_json

URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
ENCABEZADOS = {"Accept": "application/json"}
CARPETA_CACHE = Path(__file__).parent / "cache"
KM_ALREDEDOR = 2       # área de (2·2+1) × (2·2+1) ≈ 5 × 5 km alrededor de la parcela
VERDE_DESDE = 0.5      # NDVI desde el cual consideramos que hay cultivo verde


def _con_cache(nombre, obtener):
    archivo = CARPETA_CACHE / nombre
    if archivo.exists():
        return json.loads(archivo.read_text())
    datos = obtener()
    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos


def ultima_fecha(lat, lon):
    """Fecha de la imagen más reciente disponible, ej. {"modis_date": "A2026289", "calendar_date": "2026-10-16"}."""
    lat, lon = round(lat, 2), round(lon, 2)
    fechas = _con_cache(
        f"modis_fechas_{lat}_{lon}_{date.today():%Y%m%d}.json",
        lambda: pedir_json(f"{URL}/dates", {"latitude": lat, "longitude": lon},
                           encabezados=ENCABEZADOS)["dates"])
    return fechas[-1]


def superficie_verde(lat, lon, fecha_modis):
    """Porcentaje del área alrededor de la parcela con vegetación verde en esa imagen."""
    lat, lon = round(lat, 2), round(lon, 2)

    def obtener():
        respuesta = pedir_json(f"{URL}/subset", {
            "latitude": lat, "longitude": lon, "band": "250m_16_days_NDVI",
            "startDate": fecha_modis, "endDate": fecha_modis,
            "kmAboveBelow": KM_ALREDEDOR, "kmLeftRight": KM_ALREDEDOR,
        }, encabezados=ENCABEZADOS)
        imagen = respuesta["subset"][0]
        ndvi = [v * 0.0001 for v in imagen["data"] if v > -2000]  # -3000 = sin dato
        return {
            "fecha": imagen["calendar_date"],
            "pct_verde": round(100 * sum(v >= VERDE_DESDE for v in ndvi) / len(ndvi)),
            "ndvi_promedio": round(sum(ndvi) / len(ndvi), 2),
        }

    return _con_cache(f"modis_ndvi_{lat}_{lon}_{fecha_modis}.json", obtener)
