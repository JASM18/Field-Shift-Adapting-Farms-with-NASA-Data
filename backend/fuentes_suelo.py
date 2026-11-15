"""Datos fijos del terreno (no cambian con el tiempo), se guardan una vez por punto:

- SoilGrids (ISRIC): arcilla, arena, limo, pH y carbono orgánico. https://rest.isric.org
- SRTM (NASA) vía Open Topo Data: altura del terreno. https://www.opentopodata.org
"""
import json
import math
from pathlib import Path

from backend.red import pedir_json

CARPETA_CACHE = Path(__file__).parent / "cache"


def _con_cache(nombre, obtener):
    archivo = CARPETA_CACHE / nombre
    if archivo.exists():
        return json.loads(archivo.read_text())
    datos = obtener()
    CARPETA_CACHE.mkdir(exist_ok=True)
    archivo.write_text(json.dumps(datos))
    return datos


def propiedades_suelo(lat, lon):
    """Promedio de 0 a 30 cm. Devuelve None en cada propiedad si no hay dato
    (pasa en zonas urbanas o cuerpos de agua)."""
    # Redondeo a 0.01° (~1 km); SoilGrids usa cuadros de 250 m
    lat, lon = round(lat, 2), round(lon, 2)

    def obtener():
        params = [("lat", lat), ("lon", lon), ("value", "mean")]
        params += [("property", p) for p in ("clay", "sand", "silt", "phh2o", "soc")]
        params += [("depth", d) for d in ("0-5cm", "5-15cm", "15-30cm")]
        capas = pedir_json("https://rest.isric.org/soilgrids/v2.0/properties/query", params, intentos=2, tiempo=(10, 30))
        grosor = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}  # para promediar según el grosor de cada capa
        resultado = {}
        for capa in capas["properties"]["layers"]:
            factor = capa["unit_measure"]["d_factor"]
            valores = [(d["values"]["mean"], grosor[d["label"]]) for d in capa["depths"]
                       if d["values"]["mean"] is not None]
            if valores:
                total = sum(g for _, g in valores)
                resultado[capa["name"]] = round(sum(v * g for v, g in valores) / total / factor, 1)
            else:
                resultado[capa["name"]] = None
        return resultado

    return _con_cache(f"soilgrids_{lat}_{lon}.json", obtener)


def relieve(lat, lon, distancia_m=90):
    """Altura del punto y pendiente, comparando con 4 puntos vecinos (norte, sur, este, oeste)."""
    lat, lon = round(lat, 4), round(lon, 4)

    def obtener():
        d_lat = distancia_m / 111_320
        d_lon = distancia_m / (111_320 * math.cos(math.radians(lat)))
        puntos = [(lat, lon), (lat + d_lat, lon), (lat - d_lat, lon), (lat, lon + d_lon), (lat, lon - d_lon)]
        respuesta = pedir_json("https://api.opentopodata.org/v1/srtm30m",
                               {"locations": "|".join(f"{a:.5f},{b:.5f}" for a, b in puntos)},
                               intentos=2, tiempo=(10, 30))
        centro, norte, sur, este, oeste = (r["elevation"] for r in respuesta["results"])
        if None in (centro, norte, sur, este, oeste):
            return {"altura_m": centro, "pendiente_pct": None}
        cambio_ns = (norte - sur) / (2 * distancia_m)
        cambio_eo = (este - oeste) / (2 * distancia_m)
        pendiente = 100 * math.hypot(cambio_ns, cambio_eo)
        return {"altura_m": round(centro), "pendiente_pct": round(pendiente, 1)}

    return _con_cache(f"srtm_{lat}_{lon}.json", obtener)
