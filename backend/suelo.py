"""Pantalla "Así es tu suelo": convierte los números en palabras sencillas y
en un "Qué hacer". Las reglas están aquí para que el equipo las ajuste.

Referencias de clasificación:
- Textura: triángulo de texturas del USDA.
- pH y materia orgánica: NOM-021-SEMARNAT-2000 (análisis de suelos en México).
"""
from datetime import datetime
from statistics import mean

from backend.nasa_power import VALOR_VACIO

# ---------------- Humedad ----------------
# Se compara la humedad de los últimos 7 días con la de la misma época en 30 años.
# "Percentil" = de cada 100 años parecidos, en cuántos hubo menos humedad que ahora.
NIVELES_HUMEDAD = [  # (percentil menor a…, nombre, qué hacer)
    (10, "Very dry", "if you plant now, you'll need a heavy pre-planting irrigation."),
    (30, "Dry", "if you plant now, you'll need a pre-planting irrigation."),
    (70, "Normal", "moisture is as usual for this time of year."),
    (90, "Moist", "good time to plant as long as the soil isn't waterlogged."),
    (101, "Very wet", "wait for the soil to dry out before bringing in machinery."),
]
VENTANA_DIAS = 15  # días antes y después de la fecha para definir "la misma época"


def humedad(historico, reciente):
    validos = [(f, v) for f, v in sorted(reciente.items()) if v != VALOR_VACIO]
    if not validos:
        return {"error": "No recent moisture data."}
    ultimos = validos[-7:]
    actual = mean(v for _, v in ultimos)
    fecha_dato = datetime.strptime(ultimos[-1][0], "%Y%m%d").date()

    # Valores de la misma época del año en los 30 años
    dia_objetivo = fecha_dato.timetuple().tm_yday
    misma_epoca = []
    for fecha, valor in historico.items():
        if valor == VALOR_VACIO:
            continue
        dia = datetime.strptime(fecha, "%Y%m%d").timetuple().tm_yday
        distancia = min(abs(dia - dia_objetivo), 365 - abs(dia - dia_objetivo))
        if distancia <= VENTANA_DIAS:
            misma_epoca.append(valor)

    percentil = 100 * sum(v < actual for v in misma_epoca) / len(misma_epoca)
    for indice, (limite, nombre, que_hacer) in enumerate(NIVELES_HUMEDAD):
        if percentil < limite:
            break

    return {
        "nombre": nombre,
        "indice": indice,  # 0 = muy seca … 4 = muy húmeda
        "escala": [n for _, n, _ in NIVELES_HUMEDAD],
        "que_hacer": que_hacer,
        "detalle": (f"Compared with the same time of year over the last 30 years. Data as of "
                    f"{fecha_dato:%b %d, %Y}. Estimated from rainfall and weather: irrigation is not taken into account."),
        "valor": round(actual, 2),
        "percentil": round(percentil),
    }


# ---------------- Textura ----------------
GRUPOS_TEXTURA = {
    "arenosa": {
        "nombre": "Sandy",
        "descripcion": "Water drains quickly and it holds little moisture and few nutrients.",
        "que_hacer": "irrigate more often but with less water each time, and add organic matter.",
    },
    "franca": {
        "nombre": "Loam (balanced)",
        "descripcion": "A good mix of sand, silt and clay: it holds water without waterlogging easily.",
        "que_hacer": "it's a good soil for almost every crop; be careful not to compact it with machinery.",
    },
    "arcillosa": {
        "nombre": "Clay",
        "descripcion": "It holds water well, but waterlogs easily and gets hard when it dries.",
        "que_hacer": "space out irrigations and keep machinery off wet soil.",
    },
}


def _clase_usda(arena, limo, arcilla):
    """Triángulo de texturas del USDA (porcentajes que suman 100)."""
    if limo + 1.5 * arcilla < 15:
        return "Sand", "arenosa"
    if limo + 2 * arcilla < 30:
        return "Loamy sand", "arenosa"
    if (7 <= arcilla < 20 and arena > 52) or (arcilla < 7 and limo < 50):
        return "Sandy loam", "arenosa"
    if 7 <= arcilla < 27 and 28 <= limo < 50 and arena <= 52:
        return "Loam", "franca"
    if limo >= 80 and arcilla < 12:
        return "Silt", "franca"
    if (limo >= 50 and 12 <= arcilla < 27) or (50 <= limo < 80 and arcilla < 12):
        return "Silt loam", "franca"
    if 20 <= arcilla < 35 and limo < 28 and arena > 45:
        return "Sandy clay loam", "franca"
    if 27 <= arcilla < 40 and 20 < arena <= 45:
        return "Clay loam", "arcillosa"
    if 27 <= arcilla < 40 and arena <= 20:
        return "Silty clay loam", "arcillosa"
    if arcilla >= 35 and arena > 45:
        return "Sandy clay", "arcillosa"
    if arcilla >= 40 and limo >= 40:
        return "Silty clay", "arcillosa"
    return "Clay", "arcillosa"


def textura(props):
    arena, limo, arcilla = props.get("sand"), props.get("silt"), props.get("clay")
    if None in (arena, limo, arcilla):
        return {"error": "No texture data for this location."}
    total = arena + limo + arcilla
    arena, limo, arcilla = (100 * x / total for x in (arena, limo, arcilla))
    clase, grupo = _clase_usda(arena, limo, arcilla)
    return {
        **GRUPOS_TEXTURA[grupo],
        "clase_tecnica": clase,
        "detalle": f"{clase}: sand {arena:.0f} %, silt {limo:.0f} %, clay {arcilla:.0f} %.",
    }


# ---------------- Materia orgánica ----------------
# Materia orgánica (%) ≈ carbono orgánico (g/kg) × 1.724 / 10
NIVELES_MATERIA_ORGANICA = [  # (MO % menor a…, nombre, tipo de color, descripción, qué hacer)
    (1.6, "Low", "alerta", "Your soil has little “food” stored for crops.",
     "leave crop residue in the field and include chickpea or beans in your rotation."),
    (3.6, "Fair", "normal", "Your soil has a medium amount of “food” for crops.",
     "leave crop residue in the field to keep it that way."),
    (999, "Good", "bueno", "Your soil has plenty of “food” stored for crops.",
     "keep leaving crop residue and avoid burning it."),
]


def materia_organica(props):
    carbono = props.get("soc")
    if carbono is None:
        return {"error": "No organic matter data for this location."}
    mo = carbono * 1.724 / 10
    for limite, nombre, tipo, descripcion, que_hacer in NIVELES_MATERIA_ORGANICA:
        if mo < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "que_hacer": que_hacer,
            "detalle": f"Estimated organic matter: {mo:.1f} %."}


# ---------------- pH ----------------
NIVELES_PH = [  # (pH menor a…, nombre, tipo de color, descripción)
    (5.1, "Acidic", "alerta", "Many crops grow poorly; it may need agricultural lime."),
    (6.6, "Slightly acidic", "bueno", "Most crops tolerate it well."),
    (7.4, "Neutral", "bueno", "Ideal: almost every crop grows well."),
    (8.6, "Slightly alkaline", "bueno",
     "Common in dry areas. Many crops tolerate it; some may "
     "have trouble taking up iron and zinc."),
    (99, "Very alkaline", "alerta",
     "There may be salts or sodium that harm crops; a lab test is advisable."),
]


def ph(props):
    valor = props.get("phh2o")
    if valor is None:
        return {"error": "No pH data for this location."}
    for limite, nombre, tipo, descripcion in NIVELES_PH:
        if valor < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "detalle": f"Estimated pH: {valor:.1f}."}


# ---------------- Terreno (SRTM) ----------------
NIVELES_PENDIENTE = [  # (pendiente % menor a…, nombre, descripción)
    (2, "Flat", "Rain or irrigation water barely runs off."),
    (5, "Gently sloped", "Water runs off a little; there's some risk of it washing soil away."),
    (10, "Sloped", "Water runs off and can wash away fertile soil (erosion)."),
    (999, "Steep", "High risk of rain washing away fertile soil (erosion)."),
]


def terreno(rel, grupo_textura=None):
    pendiente = rel.get("pendiente_pct")
    if pendiente is None:
        return {"error": "No terrain data for this location."}
    for limite, nombre, descripcion in NIVELES_PENDIENTE:
        if pendiente < limite:
            break
    if nombre == "Flat" and grupo_textura == "Clay":
        que_hacer = "level the field well: on flat clay soil water pools."
    elif nombre == "Flat":
        que_hacer = "no special care is needed because of the slope."
    else:
        que_hacer = "leave crop residue as cover and plant across the slope (contour lines)."
    return {"nombre": nombre, "descripcion": descripcion, "que_hacer": que_hacer,
            "detalle": f"Approximate slope {pendiente:.1f} %, elevation {rel['altura_m']} m above sea level."}
