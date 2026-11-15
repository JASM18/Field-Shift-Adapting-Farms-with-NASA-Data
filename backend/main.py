"""Servidor de Field Shift.

- /api/...  → datos ya procesados para cada pantalla
- /         → las páginas (carpeta frontend/)

Correr en desarrollo:
    DEV=1 .venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.clima import resumen_mensual
from backend.nasa_power import clima_diario_historico

CARPETA_FRONTEND = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Field Shift")


@app.get("/api/clima")
def api_clima(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    """Pantalla 'El clima de tu zona'."""
    try:
        datos = clima_diario_historico(lat, lon)
    except requests.RequestException:
        raise HTTPException(503, "NASA POWER no respondió. Intenta de nuevo en un momento.")
    return resumen_mensual(datos)


if os.getenv("DEV"):
    # Solo en desarrollo: la página pregunta cada segundo si algún archivo cambió
    # y, si cambió, se recarga sola.
    @app.get("/dev/version")
    def version_archivos():
        return {"version": max(f.stat().st_mtime for f in CARPETA_FRONTEND.rglob("*") if f.is_file())}


# Va al final para que no tape las rutas /api
app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
