"""Datos de suelo desde SoilGrids (ISRIC), API gratuita sin login.

Ojo: en zonas urbanas o cuerpos de agua devuelve valores vacíos (None);
en ese caso la app pide al agricultor capturar los datos a mano.
Docs: https://rest.isric.org/soilgrids/v2.0/docs
"""
from __future__ import annotations

import requests

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


def get_topsoil(lat: float, lon: float) -> dict[str, float | None]:
    """Promedio 0-30 cm de pH, carbono orgánico (g/kg), arcilla y arena (%)."""
    r = requests.get(
        URL,
        params=[("lon", lon), ("lat", lat), ("value", "mean")]
        + [("property", p) for p in ("phh2o", "soc", "clay", "sand")]
        + [("depth", d) for d in ("0-5cm", "5-15cm", "15-30cm")],
        timeout=60,
    )
    r.raise_for_status()
    out: dict[str, float | None] = {}
    names = {"phh2o": "ph", "soc": "soc_g_kg", "clay": "clay_pct", "sand": "sand_pct"}
    for layer in r.json()["properties"]["layers"]:
        factor = layer["unit_measure"]["d_factor"]
        vals = [d["values"]["mean"] for d in layer["depths"] if d["values"]["mean"] is not None]
        out[names[layer["name"]]] = round(sum(vals) / len(vals) / factor, 1) if vals else None
    return out


def texture_class(clay: float, sand: float) -> str:
    """Clasificación simplificada de textura."""
    if sand >= 70:
        return "arenoso"
    if clay >= 40:
        return "arcilloso"
    return "franco"
