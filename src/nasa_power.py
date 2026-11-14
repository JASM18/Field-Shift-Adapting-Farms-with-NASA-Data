"""Cliente mínimo para la API de NASA POWER (no requiere login).

Docs: https://power.larc.nasa.gov/docs/services/api/
"""
from __future__ import annotations

import requests

BASE = "https://power.larc.nasa.gov/api/temporal"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Parámetros útiles para agricultura (comunidad AG)
PARAMS = {
    "T2M": "Temperatura media a 2 m (°C)",
    "T2M_MAX": "Temperatura máxima (°C)",
    "T2M_MIN": "Temperatura mínima extrema (°C)",
    "FROST_DAYS": "Días con helada por mes",
    "PRECTOTCORR": "Precipitación (mm/día)",
    "GWETROOT": "Humedad del suelo en zona de raíces (0-1)",
    "RH2M": "Humedad relativa (%)",
    "ALLSKY_SFC_SW_DWN": "Radiación solar (kWh/m²/día)",
}


def get_climatology(lat: float, lon: float) -> dict[str, dict[str, float]]:
    """Climatología mensual (promedio ~25 años). Devuelve {param: {"JAN": v, ..., "ANN": v}}."""
    r = requests.get(
        f"{BASE}/climatology/point",
        params={
            "parameters": ",".join(PARAMS),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "format": "JSON",
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["properties"]["parameter"]


def get_monthly_series(lat: float, lon: float, start: int = 2001, end: int = 2024,
                       params: tuple[str, ...] = ("T2M", "PRECTOTCORR")) -> dict[str, dict[str, float]]:
    """Serie mensual año por año, para ver tendencias (calentamiento, cambios de lluvia).

    Devuelve {param: {"YYYYMM": v}}; la clave "YYYY13" es el promedio anual.
    """
    r = requests.get(
        f"{BASE}/monthly/point",
        params={
            "parameters": ",".join(params),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": start,
            "end": end,
            "format": "JSON",
        },
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["properties"]["parameter"]


def season_summary(clim: dict, months: list[int]) -> dict[str, float]:
    """Resume una temporada (lista de meses 1-12): temperatura media, mín, máx y lluvia total en mm."""
    keys = [MONTHS[m - 1] for m in months]
    rain_mm = sum(clim["PRECTOTCORR"][MONTHS[m - 1]] * DAYS_IN_MONTH[m - 1] for m in months)
    return {
        "t_mean": sum(clim["T2M"][k] for k in keys) / len(keys),
        "t_min": min(clim["T2M_MIN"][k] for k in keys),
        "t_max": max(clim["T2M_MAX"][k] for k in keys),
        "rain_mm": rain_mm,
        "soil_moisture": sum(clim["GWETROOT"][k] for k in keys) / len(keys),
        "frost_days": sum(clim["FROST_DAYS"][k] for k in keys),
    }
