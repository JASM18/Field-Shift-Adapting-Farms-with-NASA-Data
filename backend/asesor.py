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


def permitir(ip):
    ahora = time.time()
    historial = _uso[ip]
    while historial and ahora - historial[0] > 3600:
        historial.popleft()
    if len(historial) >= LIMITE_POR_HORA:
        return False
    historial.append(ahora)
    return True


# ---------- Instrucciones del asesor ----------
SISTEMA = """Eres el asesor agrícola de CROPY, una app que ayuda a agricultores de regiones con clima extremo \
(empezando por Sonora, México) a decidir qué sembrar, cuándo y cómo rotar sus cultivos, usando datos de la NASA.

Cómo responder:
- Hablas con agricultores desde su celular: español sencillo, frases cortas, sin tecnicismos. \
Si usas un término técnico (lámina, NDVI, Kc), explícalo en pocas palabras.
- Respuestas breves: unas 120 palabras como máximo, salvo que pidan más detalle. Puedes usar listas cortas; no uses tablas.
- Todo dato sobre clima, suelo, agua o cultivos debe salir de tus herramientas. No inventes números. \
Si una herramienta no tiene el dato (aparece "n/a") o falla, dilo con honestidad.
- Di de dónde sale la información, de forma natural (por ejemplo: "según 30 años de datos de la NASA", \
"según el INIFAP", "según el satélite MODIS").
- Sugiere, no ordenes: la decisión siempre es del agricultor, que conoce su parcela. Menciona los riesgos. \
El pronóstico de 6 meses es una tendencia, no una certeza.
- El catálogo tiene solo 7 cultivos: trigo, maíz, cártamo, garbanzo, frijol, sorgo forrajero y canola. \
Si preguntan por otro, acláralo y, si das orientación, márcala como general.
- Los datos de clima son de la zona (cuadros de unos 50 km), no de la parcela exacta.
- Atribuye bien las fuentes: NASA POWER (clima de 30 años y humedad del suelo), NASA MODIS (siembras vistas \
por satélite), NASA SRTM (relieve), SoilGrids (tipo de suelo), INIFAP / FAO / ECOCROP (datos de cultivos). \
Los pronósticos de 16 días y de 6 meses son de Open-Meteo (modelo europeo ECMWF), NO de la NASA.
- Si la pregunta no tiene que ver con el campo, redirige amablemente a temas agrícolas."""


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
            return _json({"error": "La fuente de datos no respondió. Intenta más tarde."})

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
                "fuentes": "NASA POWER (30 años y días recientes), Open-Meteo (pronóstico de 16 días)",
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
                                   props, grupo, humedad())
        return proteger(calcular)

    @beta_tool
    def ficha_cultivo(cultivo: str) -> str:
        """Ficha completa del catálogo de un cultivo con su fuente en cada dato: fechas de siembra, agua y riegos,
        temperaturas, pH, nitrógeno, rendimiento y duración del ciclo (INIFAP, FAO, ECOCROP, SIAP).

        Args:
            cultivo: id del cultivo: trigo, maiz, cartamo, garbanzo, frijol, sorgo o canola.
        """
        ficha = next((c for c in sembrar.catalogo() if c["id"] == cultivo), None)
        return _json(ficha or {"error": f"'{cultivo}' no está en el catálogo."})

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
        return _json(agua.calcular(hectareas, lamina_cm))

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
            veredictos = {c["id"]: sembrar.evaluar(c["id"], historico)["veredicto"] for c in sembrar.lista_cultivos()}
            return planes.generar(ultimo, lamina_cm, veredictos)
        return proteger(calcular)

    return [estado_actual_zona, clima_por_mes, evaluar_cultivo, ficha_cultivo,
            suelo_de_la_parcela, agua_disponible, planes_rotacion]


NOMBRES_AMIGABLES = {
    "estado_actual_zona": "cómo está tu zona hoy", "clima_por_mes": "el clima de cada mes",
    "evaluar_cultivo": "la evaluación del cultivo", "ficha_cultivo": "el catálogo de cultivos",
    "suelo_de_la_parcela": "tu suelo", "agua_disponible": "el cálculo de agua",
    "planes_rotacion": "los planes de rotación",
}


def responder(mensajes, lat, lon, nombre_lugar):
    """mensajes: [{"rol": "user"|"assistant", "texto": "..."}]. Devuelve {"texto", "consultas"}."""
    historial = [{"role": m["rol"], "content": m["texto"][:MAX_CARACTERES_MENSAJE]}
                 for m in mensajes[-MAX_MENSAJES_HISTORIAL:] if m.get("texto")]
    while historial and historial[0]["role"] != "user":
        historial.pop(0)  # la conversación debe empezar con el usuario
    contexto = f"Hoy es {date.today():%d/%m/%Y}. La parcela del agricultor está en {nombre_lugar} (lat {lat}, lon {lon})."

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
        return {"texto": "No puedo ayudarte con esa pregunta. Intenta preguntarme sobre tus cultivos, "
                         "tu suelo, el clima o el agua.", "consultas": []}
    texto = "\n".join(b.text for b in final.content if b.type == "text").strip()
    return {"texto": texto or "No tengo una respuesta para eso. ¿Puedes preguntarlo de otra forma?",
            "consultas": list(dict.fromkeys(NOMBRES_AMIGABLES.get(n, n) for n in consultas))}
