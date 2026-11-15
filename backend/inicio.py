"""Tarjetas del Inicio, "¿Cómo está tu zona hoy?": comparan lo que pasa ahora
con lo normal (30 años de NASA POWER). Las reglas están aquí para ajustarlas.

Cada tarjeta devuelve: nombre (palabra grande), tipo (color), descripcion y detalle.
Tipos de color: "bueno" (verde), "alerta" (amarillo), "peligro" (rojo), "agua" (azul).
"""
from datetime import date, datetime, timedelta
from statistics import mean

from backend.nasa_power import VALOR_VACIO

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------- Agua en el suelo ----------------
# Reutiliza el cálculo de "Mi suelo" (backend/suelo.py → humedad)
DESCRIPCION_HUMEDAD = ["Mucho menos humedad que lo normal", "Menos humedad que lo normal",
                       "Como siempre en esta época", "Más humedad que lo normal",
                       "Mucha más humedad que lo normal"]
COLOR_HUMEDAD = ["peligro", "alerta", "bueno", "agua", "agua"]


def tarjeta_humedad(humedad):
    if "error" in humedad:
        return humedad
    i = humedad["indice"]
    return {"nombre": humedad["nombre"], "tipo": COLOR_HUMEDAD[i],
            "descripcion": DESCRIPCION_HUMEDAD[i],
            "detalle": "Estimado con lluvia y clima; no toma en cuenta el riego."}


# ---------------- Lluvia del mes ----------------
LLUVIA_CASI_NADA_MM = 5  # si lo normal en estas fechas es menos que esto, es temporada seca
NIVELES_LLUVIA = [  # (proporción de lo normal menor a…, nombre, color, descripción)
    (0.25, "Muy poca", "peligro", "Muy por debajo de lo normal"),
    (0.75, "Poca", "alerta", "Menos de lo normal"),
    (1.25, "Normal", "bueno", "Como siempre en esta época"),
    (2.0, "Más de lo normal", "agua", "Ha llovido más que otros años"),
    (999, "Mucha", "agua", "Mucho más que lo normal"),
]


def tarjeta_lluvia(historico, reciente_power, pronostico):
    hoy = date.today()
    # Lluvia en lo que va del mes: NASA POWER y, para los días que aún no tiene (~3), Open-Meteo
    abierto = dict(zip(pronostico["time"], pronostico["precipitation_sum"]))
    lluvia_mes = 0.0
    for dia in range(1, hoy.day + 1):
        fecha = hoy.replace(day=dia)
        valor = reciente_power.get(f"{fecha:%Y%m%d}", VALOR_VACIO)
        if valor == VALOR_VACIO:
            valor = abierto.get(f"{fecha:%Y-%m-%d}") or 0.0
        lluvia_mes += valor

    # Lo normal: promedio de 30 años para los mismos días del mes
    por_año = {}
    for fecha, valor in historico.items():
        if valor != VALOR_VACIO and int(fecha[4:6]) == hoy.month and int(fecha[6:8]) <= hoy.day:
            por_año[fecha[:4]] = por_año.get(fecha[:4], 0) + valor
    normal = mean(por_año.values())

    proximos = sum(v or 0 for t, v in abierto.items() if t > f"{hoy:%Y-%m-%d}")
    detalle = (f"{lluvia_mes:.0f} mm en lo que va de {MESES[hoy.month - 1]} (normal: {normal:.0f} mm). "
               f"Pronóstico próximos 16 días: {proximos:.0f} mm.")

    if normal < LLUVIA_CASI_NADA_MM:
        # En temporada seca, solo decimos "más" si llovió al menos el doble de lo normal
        if lluvia_mes < max(LLUVIA_CASI_NADA_MM, 2 * normal):
            return {"nombre": "Normal", "tipo": "bueno", "descripcion": "En esta época casi no llueve",
                    "detalle": detalle}
        return {"nombre": "Más de lo normal", "tipo": "agua",
                "descripcion": "Llovió en una época que casi siempre es seca", "detalle": detalle}

    proporcion = lluvia_mes / normal
    for limite, nombre, tipo, descripcion in NIVELES_LLUVIA:
        if proporcion < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "detalle": detalle}


# ---------------- Temperatura ----------------
DIAS_ATRAS, DIAS_ADELANTE = 3, 6   # "estos días" = 3 días atrás, hoy y 6 adelante
VENTANA_NORMAL = 7                 # días antes/después para calcular la máxima normal
DIA_CALOR_EXTREMO = 38             # °C
NIVELES_DIFERENCIA = [  # (diferencia con lo normal menor a… °C, nombre, color)
    (-3, "Más fresco", "agua"),
    (3, "Normal", "bueno"),
    (5, "Más caluroso", "alerta"),
    (99, "Muy caluroso", "peligro"),
]
DESCRIPCION_TEMPERATURA = [  # (máxima promedio menor a… °C, descripción)
    (30, "Días templados, buenos para sembrar"),
    (35, "Días calurosos"),
    (38, "Días muy calurosos"),
    (99, "Calor extremo"),
]


def tarjeta_temperatura(historico_tmax, pronostico):
    hoy = date.today()
    fechas = {(hoy + timedelta(days=d)).isoformat() for d in range(-DIAS_ATRAS, DIAS_ADELANTE + 1)}
    maximas = [v for t, v in zip(pronostico["time"], pronostico["temperature_2m_max"])
               if t in fechas and v is not None]
    actual = mean(maximas)

    # Máxima normal para estas fechas (30 años, ± VENTANA_NORMAL días)
    dias_objetivo = {(hoy + timedelta(days=d)).timetuple().tm_yday
                     for d in range(-DIAS_ATRAS - VENTANA_NORMAL, DIAS_ADELANTE + VENTANA_NORMAL + 1)}
    normales = [v for f, v in historico_tmax.items()
                if v != VALOR_VACIO and datetime.strptime(f, "%Y%m%d").timetuple().tm_yday in dias_objetivo]
    normal = mean(normales)

    diferencia = actual - normal
    for limite, nombre, tipo in NIVELES_DIFERENCIA:
        if diferencia < limite:
            break
    for limite, descripcion in DESCRIPCION_TEMPERATURA:
        if actual < limite:
            break

    # Avisos con el pronóstico de 16 días
    futuros = [(t, mx, mn) for t, mx, mn in zip(pronostico["time"], pronostico["temperature_2m_max"],
                                                pronostico["temperature_2m_min"]) if t > hoy.isoformat()]
    dias_calor = sum(1 for _, mx, _ in futuros if mx is not None and mx >= DIA_CALOR_EXTREMO)
    dias_helada = sum(1 for _, _, mn in futuros if mn is not None and mn <= 0)
    avisos = []
    if dias_calor:
        avisos.append(f"⚠ {dias_calor} día(s) de más de {DIA_CALOR_EXTREMO} °C en las próximas 2 semanas")
    if dias_helada:
        avisos.append(f"❄ Posible helada en {dias_helada} día(s) de las próximas 2 semanas")

    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "avisos": avisos,
            "detalle": f"Máximas de ~{actual:.0f} °C estos días (normal para estas fechas: {normal:.0f} °C)."}


# ---------------- Siembras alrededor (MODIS) ----------------
SIN_CULTIVOS_SI_MENOS_DE = 10  # % de superficie verde: por debajo, es época sin cultivos
NIVELES_SIEMBRAS = [  # (proporción contra otros años menor a…, nombre, color, descripción)
    (0.5, "Pocas", "alerta", "Menos parcelas verdes que otros años"),
    (0.85, "Algo menos", "alerta", "Un poco menos parcelas verdes que otros años"),
    (1.15, "Normal", "bueno", "Parecido a otros años"),
    (999, "Más", "bueno", "Más parcelas verdes que otros años"),
]


def tarjeta_siembras(actual, otros_años):
    """actual y cada elemento de otros_años: {"fecha", "pct_verde", "ndvi_promedio"}."""
    if len(otros_años) < 2:
        return {"error": "No hay suficientes imágenes de otros años para comparar."}
    normal = mean(a["pct_verde"] for a in otros_años)
    fecha = datetime.strptime(actual["fecha"], "%Y-%m-%d").date()
    detalle = (f"Imagen MODIS del {fecha:%d/%m/%Y}: {actual['pct_verde']} % de la zona verde "
               f"(misma fecha en {len(otros_años)} años anteriores: {normal:.0f} %).")

    if normal < SIN_CULTIVOS_SI_MENOS_DE and actual["pct_verde"] < SIN_CULTIVOS_SI_MENOS_DE:
        return {"nombre": "Sin cultivos", "tipo": "bueno",
                "descripcion": "Época sin siembras en la zona, igual que otros años", "detalle": detalle}

    proporcion = actual["pct_verde"] / max(normal, 1)
    for limite, nombre, tipo, descripcion in NIVELES_SIEMBRAS:
        if proporcion < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "detalle": detalle}
