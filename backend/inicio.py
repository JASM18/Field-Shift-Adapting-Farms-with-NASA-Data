"""Tarjetas del Inicio, "¿Cómo está tu zona hoy?": comparan lo que pasa ahora
con lo normal (30 años de NASA POWER). Las reglas están aquí para ajustarlas.

Cada tarjeta devuelve: nombre (palabra grande), tipo (color), descripcion y detalle.
Tipos de color: "bueno" (verde), "alerta" (amarillo), "peligro" (rojo), "agua" (azul).
"""
from datetime import date, datetime, timedelta
from statistics import mean

from backend.nasa_power import VALOR_VACIO

MESES = ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"]


# ---------------- Agua en el suelo ----------------
# Reutiliza el cálculo de "Mi suelo" (backend/suelo.py → humedad)
DESCRIPCION_HUMEDAD = ["Much less moisture than normal", "Less moisture than normal",
                       "As usual for this time of year", "More moisture than normal",
                       "Much more moisture than normal"]
COLOR_HUMEDAD = ["peligro", "alerta", "bueno", "agua", "agua"]


def tarjeta_humedad(humedad):
    if "error" in humedad:
        return humedad
    i = humedad["indice"]
    return {"nombre": humedad["nombre"], "tipo": COLOR_HUMEDAD[i],
            "descripcion": DESCRIPCION_HUMEDAD[i],
            "detalle": "Estimated from rainfall and weather; irrigation is not taken into account."}


# ---------------- Lluvia del mes ----------------
LLUVIA_CASI_NADA_MM = 5  # si lo normal en estas fechas es menos que esto, es temporada seca
NIVELES_LLUVIA = [  # (proporción de lo normal menor a…, nombre, color, descripción)
    (0.25, "Very little", "peligro", "Far below normal"),
    (0.75, "Little", "alerta", "Less than normal"),
    (1.25, "Normal", "bueno", "As usual for this time of year"),
    (2.0, "Above normal", "agua", "It has rained more than in other years"),
    (999, "A lot", "agua", "Much more than normal"),
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
    detalle = (f"{lluvia_mes:.0f} mm so far in {MESES[hoy.month - 1]} (normal: {normal:.0f} mm). "
               f"Forecast for the next 16 days: {proximos:.0f} mm.")

    if normal < LLUVIA_CASI_NADA_MM:
        # En temporada seca, solo decimos "más" si llovió al menos el doble de lo normal
        if lluvia_mes < max(LLUVIA_CASI_NADA_MM, 2 * normal):
            return {"nombre": "Normal", "tipo": "bueno", "descripcion": "It hardly ever rains at this time of year",
                    "detalle": detalle}
        return {"nombre": "Above normal", "tipo": "agua",
                "descripcion": "It rained during a season that is almost always dry", "detalle": detalle}

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
    (-3, "Cooler", "agua"),
    (3, "Normal", "bueno"),
    (5, "Hotter", "alerta"),
    (99, "Very hot", "peligro"),
]
DESCRIPCION_TEMPERATURA = [  # (máxima promedio menor a… °C, descripción)
    (30, "Mild days, good for planting"),
    (35, "Hot days"),
    (38, "Very hot days"),
    (99, "Extreme heat"),
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
        avisos.append(f"⚠ {dias_calor} day(s) above {DIA_CALOR_EXTREMO} °C in the next 2 weeks")
    if dias_helada:
        avisos.append(f"❄ Possible frost on {dias_helada} day(s) in the next 2 weeks")

    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "avisos": avisos,
            "detalle": f"Highs of ~{actual:.0f} °C these days (normal for this time of year: {normal:.0f} °C)."}


# ---------------- Siembras alrededor (MODIS) ----------------
SIN_CULTIVOS_SI_MENOS_DE = 10  # % de superficie verde: por debajo, es época sin cultivos
NIVELES_SIEMBRAS = [  # (proporción contra otros años menor a…, nombre, color, descripción)
    (0.5, "Few", "alerta", "Fewer green fields than in other years"),
    (0.85, "Slightly fewer", "alerta", "Slightly fewer green fields than in other years"),
    (1.15, "Normal", "bueno", "Similar to other years"),
    (999, "More", "bueno", "More green fields than in other years"),
]


def tarjeta_siembras(actual, otros_años):
    """actual y cada elemento de otros_años: {"fecha", "pct_verde", "ndvi_promedio"}."""
    if len(otros_años) < 2:
        return {"error": "There aren't enough images from other years to compare."}
    normal = mean(a["pct_verde"] for a in otros_años)
    fecha = datetime.strptime(actual["fecha"], "%Y-%m-%d").date()
    detalle = (f"MODIS image from {fecha:%b %d, %Y}: {actual['pct_verde']} % of the area is green "
               f"(same date in the {len(otros_años)} previous years: {normal:.0f} %).")

    if normal < SIN_CULTIVOS_SI_MENOS_DE and actual["pct_verde"] < SIN_CULTIVOS_SI_MENOS_DE:
        return {"nombre": "No crops", "tipo": "bueno",
                "descripcion": "No-planting season in the area, same as other years", "detalle": detalle}

    proporcion = actual["pct_verde"] / max(normal, 1)
    for limite, nombre, tipo, descripcion in NIVELES_SIEMBRAS:
        if proporcion < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "detalle": detalle}
