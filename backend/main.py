"""Servidor de Field Shift.

- /api/...  → datos ya procesados para cada pantalla
- /         → las páginas (carpeta frontend/)

Correr en desarrollo:
    DEV=1 .venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
import os
from pathlib import Path

from typing import Literal

import anthropic
import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import agua, asesor, inicio, planes, sembrar, suelo
from backend.clima import resumen_mensual
from backend.fuentes_suelo import propiedades_suelo, relieve
from backend.modis import superficie_verde, ultima_fecha
from backend.nasa_power import clima_diario_historico, datos_recientes, humedad_suelo_historica
from backend.open_meteo import pronostico_diario, pronostico_estacional

AÑOS_A_COMPARAR = 5  # años anteriores para la tarjeta "Siembras alrededor"

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


@app.get("/api/suelo")
def api_suelo(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    """Pantalla 'Así es tu suelo'. Cada tarjeta usa una fuente distinta: si una
    falla, las demás se muestran igual y esa tarjeta dice que no hubo datos."""
    def intentar(funcion, mensaje):
        try:
            return funcion()
        except requests.RequestException:
            return {"error": mensaje}

    humedad = intentar(
        lambda: suelo.humedad(humedad_suelo_historica(lat, lon), datos_recientes(lat, lon)["GWETROOT"]),
        "NASA POWER no respondió.")

    props = intentar(lambda: propiedades_suelo(lat, lon), "SoilGrids no respondió.")
    if "error" in props:
        textura = materia = acidez = props
    else:
        textura, materia, acidez = suelo.textura(props), suelo.materia_organica(props), suelo.ph(props)

    rel = intentar(lambda: relieve(lat, lon), "El servicio de relieve (SRTM) no respondió.")
    terreno = rel if "error" in rel else suelo.terreno(rel, textura.get("nombre"))

    return {"humedad": humedad, "textura": textura, "materia_organica": materia,
            "ph": acidez, "terreno": terreno}


# ---- ¿Qué quieres sembrar? ----

@app.get("/api/cultivos")
def api_cultivos():
    return sembrar.lista_cultivos()


@app.get("/api/sembrar")
def api_sembrar(cultivo: str, lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    """Evalúa un cultivo para la parcela. El clima histórico es obligatorio; el pronóstico,
    el suelo y la humedad son opcionales: si alguno falla, se evalúa sin él."""
    try:
        historico = clima_diario_historico(lat, lon)
    except requests.RequestException:
        raise HTTPException(503, "NASA POWER no respondió. Intenta de nuevo en un momento.")

    def opcional(funcion):
        try:
            return funcion()
        except requests.RequestException:
            return None

    pronostico = opcional(lambda: pronostico_estacional(lat, lon))
    props = opcional(lambda: propiedades_suelo(lat, lon))
    grupo = suelo.textura(props).get("nombre") if props else None
    humedad = opcional(lambda: suelo.humedad(humedad_suelo_historica(lat, lon), datos_recientes(lat, lon)["GWETROOT"]))
    resultado = sembrar.evaluar(cultivo, historico, pronostico, props, grupo, humedad)
    if "error" in resultado:
        raise HTTPException(404, resultado["error"])
    return resultado


# ---- Asesor con IA ----

class Mensaje(BaseModel):
    rol: Literal["user", "assistant"]
    texto: str = Field(max_length=4000)


class PreguntaAsesor(BaseModel):
    mensajes: list[Mensaje] = Field(min_length=1, max_length=40)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    nombre: str = Field(default="tu zona", max_length=80)


@app.post("/api/asesor")
def api_asesor(pregunta: PreguntaAsesor, request: Request):
    if not asesor.permitir(request.client.host if request.client else "?"):
        raise HTTPException(429, "Llegaste al límite de preguntas por hora. Intenta más tarde.")
    try:
        return asesor.responder([m.model_dump() for m in pregunta.mensajes],
                                pregunta.lat, pregunta.lon, pregunta.nombre)
    except anthropic.AuthenticationError:
        raise HTTPException(500, "El asesor no está configurado (revisa la llave en el archivo .env).")
    except anthropic.RateLimitError:
        raise HTTPException(429, "El asesor está muy ocupado. Intenta en un minuto.")
    except anthropic.APIConnectionError:
        raise HTTPException(503, "No hay conexión con el asesor. Revisa tu internet.")
    except anthropic.APIStatusError:
        raise HTTPException(502, "El asesor tuvo un problema. Intenta de nuevo.")


# ---- Tus próximos 3 ciclos ----

@app.get("/api/planes")
def api_planes(ultimo: str, lamina_cm: float = Query(gt=0, le=300),
               lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    """Planes de rotación. Usa el clima de la zona para descartar cultivos que no convienen."""
    try:
        historico = clima_diario_historico(lat, lon)
    except requests.RequestException:
        raise HTTPException(503, "NASA POWER no respondió. Intenta de nuevo en un momento.")
    veredictos = {c["id"]: sembrar.evaluar(c["id"], historico)["veredicto"] for c in sembrar.lista_cultivos()}
    return planes.generar(ultimo, lamina_cm, veredictos)


# ---- ¿Te alcanza el agua? ----

@app.get("/api/agua")
def api_agua(hectareas: float = Query(gt=0, le=10_000), lamina_cm: float = Query(gt=0, le=300)):
    return agua.calcular(hectareas, lamina_cm)


# ---- Inicio: una ruta por tarjeta, para que la página las cargue por separado ----

def _tarjeta(calcular, mensaje):
    """Si una fuente falla, la tarjeta muestra el error en vez de tumbar la página."""
    try:
        return calcular()
    except requests.RequestException:
        return {"error": mensaje}


@app.get("/api/inicio/humedad")
def api_inicio_humedad(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    return _tarjeta(lambda: inicio.tarjeta_humedad(suelo.humedad(
        humedad_suelo_historica(lat, lon), datos_recientes(lat, lon)["GWETROOT"])),
        "NASA POWER no respondió.")


@app.get("/api/inicio/lluvia")
def api_inicio_lluvia(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    return _tarjeta(lambda: inicio.tarjeta_lluvia(
        clima_diario_historico(lat, lon)["PRECTOTCORR"],
        datos_recientes(lat, lon)["PRECTOTCORR"],
        pronostico_diario(lat, lon)),
        "No se pudo consultar la lluvia.")


@app.get("/api/inicio/temperatura")
def api_inicio_temperatura(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    return _tarjeta(lambda: inicio.tarjeta_temperatura(
        clima_diario_historico(lat, lon)["T2M_MAX"], pronostico_diario(lat, lon)),
        "No se pudo consultar la temperatura.")


@app.get("/api/inicio/siembras")
def api_inicio_siembras(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)):
    def calcular():
        ultima = ultima_fecha(lat, lon)
        actual = superficie_verde(lat, lon, ultima["modis_date"])
        # Misma fecha (mismo día del año) en años anteriores
        año, dia = int(ultima["modis_date"][1:5]), ultima["modis_date"][5:]
        otros = []
        for anterior in range(año - AÑOS_A_COMPARAR, año):
            try:
                otros.append(superficie_verde(lat, lon, f"A{anterior}{dia}"))
            except (requests.RequestException, KeyError, IndexError):
                pass  # si un año falla, comparamos con los demás
        return inicio.tarjeta_siembras(actual, otros)

    return _tarjeta(calcular, "El servidor de MODIS no respondió.")


if os.getenv("DEV"):
    # Solo en desarrollo: la página pregunta cada segundo si algún archivo cambió
    # y, si cambió, se recarga sola.
    @app.get("/dev/version")
    def version_archivos():
        return {"version": max(f.stat().st_mtime for f in CARPETA_FRONTEND.rglob("*") if f.is_file())}


# Va al final para que no tape las rutas /api
app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
