"""Prueba de la API de Open-Meteo con datos del Valle del Yaqui, Sonora.

Correr:  .venv/bin/python pruebas/prueba_open_meteo.py

Hace dos consultas:
  1. Pronóstico diario de 16 días (incluye los últimos días que le faltan a NASA POWER)
  2. Pronóstico por temporada (próximos ~6 meses), resumido por mes
"""
import time

import requests

# Ubicación: Valle del Yaqui, Sonora. Cambiando esto funciona en cualquier lugar.
LAT, LON = 27.37, -109.93




def pedir(url, params, intentos=5):
    """Hace la consulta y, si falla la conexión, reintenta hasta `intentos` veces."""
    for intento in range(1, intentos + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as error:
            print(f"  Intento {intento} falló ({type(error).__name__}), reintentando…")
            time.sleep(3)
    raise SystemExit("No se pudo conectar con la API. Revisa tu internet.")


# ---------- 1. Pronóstico de 16 días ----------
dias = pedir(
    "https://api.open-meteo.com/v1/forecast",
    params={
        "latitude": LAT,
        "longitude": LON,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": 4,          # también trae los 4 días anteriores
        "forecast_days": 16,
        "timezone": "America/Hermosillo",
    },
)["daily"]

print("PRONÓSTICO DIARIO (Valle del Yaqui)")
print(f"{'Fecha':<12}{'Máx °C':>8}{'Mín °C':>8}{'Lluvia mm':>11}")
for fecha, tmax, tmin, lluvia in zip(dias["time"], dias["temperature_2m_max"],
                                     dias["temperature_2m_min"], dias["precipitation_sum"]):
    print(f"{fecha:<12}{tmax:>8}{tmin:>8}{lluvia:>11}")


# ---------- 2. Pronóstico por temporada ----------
# Este pronóstico no es un solo valor: el modelo corre varias veces con condiciones
# un poco distintas ("miembros"). Promediamos todos los miembros para cada día.
datos = pedir(
    "https://seasonal-api.open-meteo.com/v1/seasonal",
    params={
        "latitude": LAT,
        "longitude": LON,
        "daily": "temperature_2m_max,precipitation_sum",
        "forecast_days": 183,
    },
)["daily"]


def promedio_de_miembros(variable, i):
    """Promedio del día i entre todos los miembros de una variable."""
    valores = [datos[clave][i] for clave in datos
               if clave.startswith(variable) and datos[clave][i] is not None]
    return sum(valores) / len(valores) if valores else None


meses = {}  # {"2026-11": {"tmax": [...], "lluvia": [...]}}
for i, fecha in enumerate(datos["time"]):
    mes = fecha[:7]
    meses.setdefault(mes, {"tmax": [], "lluvia": []})
    tmax = promedio_de_miembros("temperature_2m_max", i)
    lluvia = promedio_de_miembros("precipitation_sum", i)
    if tmax is not None:
        meses[mes]["tmax"].append(tmax)
    if lluvia is not None:
        meses[mes]["lluvia"].append(lluvia)

print("\nPRONÓSTICO POR TEMPORADA (promedio de todos los miembros)")
print(f"{'Mes':<10}{'Máx promedio °C':>17}{'Lluvia total mm':>17}")
for mes, v in meses.items():
    if v["tmax"]:
        print(f"{mes:<10}{sum(v['tmax']) / len(v['tmax']):>17.1f}{sum(v['lluvia']):>17.0f}")
print("(El primer y último mes pueden estar incompletos.)")
