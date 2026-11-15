"""Asesor con IA (Claude Sonnet 5.5) que responde preguntas del agricultor usando
las MISMAS funciones que las pantallas: no inventa datos, los consulta con herramientas.

La llave se lee de ANTHROPIC_API_KEY (archivo .env en la raíz del proyecto, nunca en GitHub).
"""
import json
import os
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import anthropic
import httpx2
import requests
from anthropic import DefaultHttpxClient, beta_tool

from backend import agua, inicio, planes, sembrar, suelo
from backend.clima import resumen_mensual
from backend.fuentes_suelo import propiedades_suelo, relieve
from backend.nasa_power import clima_diario_historico, datos_recientes, humedad_suelo_historica
from backend.open_meteo import pronostico_diario, pronostico_estacional

MODELO = "claude-sonnet-5-5"
MAX_MENSAJES_HISTORIAL = 12      # solo se envían los últimos mensajes de la conversación
MAX_CARACTERES_MENSAJE = 1000
LIMITE_POR_HORA = 30             # mensajes por persona (IP) por hora
LIMITE_DIARIO_TOTAL = 400        # mensajes al día entre TODOS los visitantes (cuida el gasto de la llave)


def _cargar_env():
    """Lee el archivo .env (formato CLAVE=valor) sin dependencias extra."""
    archivo = Path(__file__).parent.parent / ".env"
    if archivo.exists():
        for linea in archivo.read_text().splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()
_cliente = None


def configurado():
    """¿Este servidor tiene llave para la AI? (en .env o en el entorno)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


SIN_LLAVE = ("The AI is not configured on this server: the ANTHROPIC_API_KEY key is missing from the .env file "
             "(see the README, “Asesor con IA” section).")


def cliente():
    """Cliente de Anthropic. Usa solo IPv4 (en algunas redes el IPv6 está roto, ver backend/red.py)."""
    global _cliente
    if _cliente is None:
        _cliente = anthropic.Anthropic(
            http_client=DefaultHttpxClient(transport=httpx2.HTTPTransport(local_address="0.0.0.0")),
            max_retries=3,
        )
    return _cliente


# ---------- Límite de uso por persona ----------
_uso = defaultdict(deque)
_uso_total = deque()


def permitir(ip):
    """False si la persona pasó su límite por hora o si se llegó al tope diario de todo el servidor."""
    ahora = time.time()
    while _uso_total and ahora - _uso_total[0] > 86_400:
        _uso_total.popleft()
    if len(_uso_total) >= LIMITE_DIARIO_TOTAL:
        return False
    historial = _uso[ip]
    while historial and ahora - historial[0] > 3600:
        historial.popleft()
    if len(historial) >= LIMITE_POR_HORA:
        return False
    historial.append(ahora)
    _uso_total.append(ahora)
    return True


# ---------- Instrucciones del asesor ----------
SISTEMA = """You are the farming advisor of CROPY, an app that helps farmers in regions with extreme climates \
(starting with Sonora, Mexico) decide what to plant, when, and how to rotate their crops, using NASA data.

How to answer:
- ALWAYS answer in English, even if the tool results or the question contain Spanish text.
- You are talking to farmers on their phones: plain English, short sentences, no jargon. \
If you use a technical term (irrigation depth, NDVI, Kc), explain it in a few words.
- Keep answers short: about 120 words at most, unless they ask for more detail. You may use short lists; do not use tables.
- Every figure about climate, soil, water or crops must come from your tools. Do not make up numbers. \
If a tool doesn't have the data (it shows "n/a") or fails, say so honestly.
- Say where the information comes from, naturally (for example: "according to 30 years of NASA data", \
"according to INIFAP", "according to the MODIS satellite").
- Suggest, don't order: the decision always belongs to the farmer, who knows their field. Mention the risks. \
The 6-month forecast is a trend, not a certainty.
- The catalog has only 7 crops (tool id in parentheses): wheat (trigo), corn (maiz), safflower (cartamo), \
chickpea (garbanzo), beans (frijol), forage sorghum (sorgo) and canola (canola). \
If they ask about another crop, make that clear and, if you give guidance, mark it as general.
- Water is measured as irrigation depth in cm (1 cm = 100 m³ per hectare); "millares" means thousands of m³.
- Climate data is for the area (grid cells of about 50 km), not for the exact field.
- The crop catalog (dates, water, yield, management risks) is from Sonora, Mexico (INIFAP). If the \
tools say the field is outside that region ("aviso_region"), make that clear: there, dates are estimated \
from the local NASA POWER climate and water and yield are only reference values. Do not mention places in Sonora \
to a farmer who is somewhere else.
- Attribute sources correctly: NASA POWER (30-year climate and soil moisture), NASA MODIS (crops seen \
by satellite), NASA SRTM (terrain), SoilGrids (soil type), INIFAP / FAO / ECOCROP (crop data). \
The 16-day and 6-month forecasts are from Open-Meteo (European ECMWF model), NOT from NASA.
- If the question has nothing to do with farming, kindly steer back to agricultural topics."""


def _json(dato):
    return json.dumps(dato, ensure_ascii=False, default=str)


def _herramientas(lat, lon):
    """Herramientas ligadas a la ubicación del agricultor (el modelo no puede cambiarla)."""

    def humedad():
        return suelo.humedad(humedad_suelo_historica(lat, lon), datos_recientes(lat, lon)["GWETROOT"])

    def contexto_cultivo():
        props = propiedades_suelo(lat, lon)
        return props, suelo.textura(props).get("nombre")

    def proteger(funcion):
        try:
            return _json(funcion())
        except requests.RequestException:
            return _json({"error": "The data source did not respond. Try again later."})

    @beta_tool
    def estado_actual_zona() -> str:
        """Cómo está la zona HOY comparada con lo normal para esta época: agua en el suelo, lluvia del mes,
        temperatura de estos días (con avisos de calor o helada de los próximos 16 días) y siembras alrededor
        (satélite MODIS). Úsala para preguntas sobre la situación actual."""
        def calcular():
            historico = clima_diario_historico(lat, lon)
            pron = pronostico_diario(lat, lon)
            return {
                "agua_en_el_suelo": inicio.tarjeta_humedad(humedad()),
                "lluvia_del_mes": inicio.tarjeta_lluvia(historico["PRECTOTCORR"],
                                                        datos_recientes(lat, lon)["PRECTOTCORR"], pron),
                "temperatura": inicio.tarjeta_temperatura(historico["T2M_MAX"], pron),
                "fuentes": "NASA POWER (30 years and recent days), Open-Meteo (16-day forecast)",
            }
        return proteger(calcular)

    @beta_tool
    def clima_por_mes() -> str:
        """Cómo es normalmente cada mes en la zona (promedio de 30 años de NASA POWER): máxima de la tarde,
        lluvia, días de calor extremo, probabilidad de helada, y los meses más frescos y más peligrosos."""
        return proteger(lambda: resumen_mensual(clima_diario_historico(lat, lon)))

    @beta_tool
    def evaluar_cultivo(cultivo: str) -> str:
        """Evalúa si conviene sembrar un cultivo en la zona: veredicto, mejor fecha de siembra, agua que necesita,
        riesgos (heladas, calor), pronóstico de 6 meses para su ciclo y consejo de rotación.

        Args:
            cultivo: id del cultivo: trigo, maiz, cartamo, garbanzo, frijol, sorgo o canola.
        """
        def calcular():
            props, grupo = contexto_cultivo()
            return sembrar.evaluar(cultivo, clima_diario_historico(lat, lon), pronostico_estacional(lat, lon),
                                   props, grupo, humedad(), lat=lat, lon=lon)
        return proteger(calcular)

    @beta_tool
    def ficha_cultivo(cultivo: str) -> str:
        """Ficha completa del catálogo de un cultivo con su fuente en cada dato: fechas de siembra, agua y riegos,
        temperaturas, pH, nitrógeno, rendimiento y duración del ciclo (INIFAP, FAO, ECOCROP, SIAP).

        Args:
            cultivo: id del cultivo: trigo, maiz, cartamo, garbanzo, frijol, sorgo o canola.
        """
        ficha = next((c for c in sembrar.catalogo() if c["id"] == cultivo), None)
        return _json(ficha or {"error": f"'{cultivo}' is not in the catalog."})

    @beta_tool
    def suelo_de_la_parcela() -> str:
        """Cómo es el suelo de la parcela: humedad actual, tipo de tierra (textura), materia orgánica, pH
        (SoilGrids) y si el terreno es plano o inclinado (NASA SRTM)."""
        def calcular():
            props = propiedades_suelo(lat, lon)
            textura = suelo.textura(props)
            return {"humedad": humedad(), "textura": textura, "materia_organica": suelo.materia_organica(props),
                    "ph": suelo.ph(props), "terreno": suelo.terreno(relieve(lat, lon), textura.get("nombre"))}
        return proteger(calcular)

    @beta_tool
    def agua_disponible(hectareas: float, lamina_cm: float) -> str:
        """Qué cultivos alcanzan con el agua asignada. Agua disponible = hectáreas × lámina; compara con el agua
        de riego que recomienda el INIFAP para cada cultivo.

        Args:
            hectareas: hectáreas que va a sembrar.
            lamina_cm: lámina de riego asignada en centímetros (por ejemplo 30 = poca, 45 = media, 70 = completa).
        """
        return _json(agua.calcular(hectareas, lamina_cm, dentro_region=sembrar.en_region(lat, lon)))

    @beta_tool
    def planes_rotacion(ultimo: str, lamina_cm: float) -> str:
        """Tres planes para los próximos 3 ciclos (seguir igual, rotar para cuidar el suelo, ahorrar agua),
        calificados en agua, suelo y riesgo si hay sequía, con el plan recomendado.

        Args:
            ultimo: id de lo último que sembró (trigo, maiz, cartamo, garbanzo, frijol, sorgo, canola) o "descanso".
            lamina_cm: lámina de agua que suele tener, en centímetros.
        """
        def calcular():
            historico = clima_diario_historico(lat, lon)
            veredictos = {c["id"]: sembrar.evaluar(c["id"], historico, lat=lat, lon=lon)["veredicto"]
                          for c in sembrar.lista_cultivos()}
            return planes.generar(ultimo, lamina_cm, veredictos, dentro_region=sembrar.en_region(lat, lon))
        return proteger(calcular)

    return [estado_actual_zona, clima_por_mes, evaluar_cultivo, ficha_cultivo,
            suelo_de_la_parcela, agua_disponible, planes_rotacion]


NOMBRES_AMIGABLES = {
    "estado_actual_zona": "how your area is today", "clima_por_mes": "the climate for each month",
    "evaluar_cultivo": "the crop evaluation", "ficha_cultivo": "the crop catalog",
    "suelo_de_la_parcela": "your soil", "agua_disponible": "the water calculation",
    "planes_rotacion": "the rotation plans",
}


def responder(mensajes, lat, lon, nombre_lugar):
    """mensajes: [{"rol": "user"|"assistant", "texto": "..."}]. Devuelve {"texto", "consultas"}."""
    historial = [{"role": m["rol"], "content": m["texto"][:MAX_CARACTERES_MENSAJE]}
                 for m in mensajes[-MAX_MENSAJES_HISTORIAL:] if m.get("texto")]
    while historial and historial[0]["role"] != "user":
        historial.pop(0)  # la conversación debe empezar con el usuario
    contexto = f"Today is {date.today():%B %d, %Y}. The farmer's field is in {nombre_lugar} (lat {lat}, lon {lon})."

    runner = cliente().beta.messages.tool_runner(
        model=MODELO,
        max_tokens=4096,
        system=[{"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": contexto}],
        tools=_herramientas(lat, lon),
        messages=historial,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        max_iterations=8,
    )

    consultas, final = [], None
    for mensaje in runner:
        final = mensaje
        consultas += [b.name for b in mensaje.content if b.type == "tool_use"]

    if final is None or final.stop_reason == "refusal":
        return {"texto": "I can't help you with that question. Try asking me about your crops, "
                         "your soil, the climate or water.", "consultas": []}
    texto = "\n".join(b.text for b in final.content if b.type == "text").strip()
    return {"texto": texto or "I don't have an answer for that. Could you ask it another way?",
            "consultas": list(dict.fromkeys(NOMBRES_AMIGABLES.get(n, n) for n in consultas))}
