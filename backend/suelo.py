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
    (10, "Muy seca", "si siembras ahora, necesitarás un riego de presiembra abundante."),
    (30, "Seca", "si siembras ahora, necesitarás un riego de presiembra."),
    (70, "Normal", "la humedad está como siempre en esta época del año."),
    (90, "Húmeda", "buen momento para sembrar si la tierra no está encharcada."),
    (101, "Muy húmeda", "espera a que la tierra oree antes de meter maquinaria."),
]
VENTANA_DIAS = 15  # días antes y después de la fecha para definir "la misma época"


def humedad(historico, reciente):
    validos = [(f, v) for f, v in sorted(reciente.items()) if v != VALOR_VACIO]
    if not validos:
        return {"error": "Sin datos recientes de humedad."}
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
        "detalle": (f"Comparado con la misma época de los últimos 30 años. Dato al "
                    f"{fecha_dato:%d/%m/%Y}. Estimado con lluvia y clima: no toma en cuenta el riego."),
        "valor": round(actual, 2),
        "percentil": round(percentil),
    }


# ---------------- Textura ----------------
GRUPOS_TEXTURA = {
    "arenosa": {
        "nombre": "Arenosa",
        "descripcion": "El agua se filtra rápido y guarda poca humedad y pocos nutrientes.",
        "que_hacer": "riega más seguido pero con menos agua cada vez, y agrega materia orgánica.",
    },
    "franca": {
        "nombre": "Franca (equilibrada)",
        "descripcion": "Una buena mezcla de arena, limo y arcilla: guarda agua sin encharcarse fácilmente.",
        "que_hacer": "es un buen suelo para casi todos los cultivos; cuida no compactarlo con maquinaria.",
    },
    "arcillosa": {
        "nombre": "Arcillosa",
        "descripcion": "Guarda bien el agua, pero se encharca con facilidad y se pone dura al secarse.",
        "que_hacer": "espacia los riegos y no metas maquinaria con la tierra mojada.",
    },
}


def _clase_usda(arena, limo, arcilla):
    """Triángulo de texturas del USDA (porcentajes que suman 100)."""
    if limo + 1.5 * arcilla < 15:
        return "Arenosa", "arenosa"
    if limo + 2 * arcilla < 30:
        return "Arena franca", "arenosa"
    if (7 <= arcilla < 20 and arena > 52) or (arcilla < 7 and limo < 50):
        return "Franco arenosa", "arenosa"
    if 7 <= arcilla < 27 and 28 <= limo < 50 and arena <= 52:
        return "Franca", "franca"
    if limo >= 80 and arcilla < 12:
        return "Limosa", "franca"
    if (limo >= 50 and 12 <= arcilla < 27) or (50 <= limo < 80 and arcilla < 12):
        return "Franco limosa", "franca"
    if 20 <= arcilla < 35 and limo < 28 and arena > 45:
        return "Franco arcillo arenosa", "franca"
    if 27 <= arcilla < 40 and 20 < arena <= 45:
        return "Franco arcillosa", "arcillosa"
    if 27 <= arcilla < 40 and arena <= 20:
        return "Franco arcillo limosa", "arcillosa"
    if arcilla >= 35 and arena > 45:
        return "Arcillo arenosa", "arcillosa"
    if arcilla >= 40 and limo >= 40:
        return "Arcillo limosa", "arcillosa"
    return "Arcillosa", "arcillosa"


def textura(props):
    arena, limo, arcilla = props.get("sand"), props.get("silt"), props.get("clay")
    if None in (arena, limo, arcilla):
        return {"error": "No hay datos de textura para este punto."}
    total = arena + limo + arcilla
    arena, limo, arcilla = (100 * x / total for x in (arena, limo, arcilla))
    clase, grupo = _clase_usda(arena, limo, arcilla)
    return {
        **GRUPOS_TEXTURA[grupo],
        "clase_tecnica": clase,
        "detalle": f"{clase}: arena {arena:.0f} %, limo {limo:.0f} %, arcilla {arcilla:.0f} %.",
    }


# ---------------- Materia orgánica ----------------
# Materia orgánica (%) ≈ carbono orgánico (g/kg) × 1.724 / 10
NIVELES_MATERIA_ORGANICA = [  # (MO % menor a…, nombre, tipo de color, descripción, qué hacer)
    (1.6, "Poca", "alerta", "Tu tierra tiene poca «comida» guardada para los cultivos.",
     "deja los rastrojos en la parcela e incluye garbanzo o frijol en tu rotación."),
    (3.6, "Regular", "normal", "Tu tierra tiene una cantidad media de «comida» para los cultivos.",
     "deja los rastrojos en la parcela para mantenerla."),
    (999, "Buena", "bueno", "Tu tierra tiene buena «comida» guardada para los cultivos.",
     "sigue dejando los rastrojos y evita quemarlos."),
]


def materia_organica(props):
    carbono = props.get("soc")
    if carbono is None:
        return {"error": "No hay datos de materia orgánica para este punto."}
    mo = carbono * 1.724 / 10
    for limite, nombre, tipo, descripcion, que_hacer in NIVELES_MATERIA_ORGANICA:
        if mo < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "que_hacer": que_hacer,
            "detalle": f"Materia orgánica estimada: {mo:.1f} %."}


# ---------------- pH ----------------
NIVELES_PH = [  # (pH menor a…, nombre, tipo de color, descripción)
    (5.1, "Ácida", "alerta", "Muchos cultivos crecen mal; puede necesitar cal agrícola."),
    (6.6, "Un poco ácida", "bueno", "La mayoría de los cultivos la toleran bien."),
    (7.4, "Neutra", "bueno", "Ideal: casi todos los cultivos crecen bien."),
    (8.6, "Un poco alcalina", "bueno",
     "Es común en zonas secas. Muchos cultivos la toleran; algunos pueden "
     "tener problemas para aprovechar el hierro y el zinc."),
    (99, "Muy alcalina", "alerta",
     "Puede haber sales o sodio que dañan a los cultivos; conviene un análisis de laboratorio."),
]


def ph(props):
    valor = props.get("phh2o")
    if valor is None:
        return {"error": "No hay datos de pH para este punto."}
    for limite, nombre, tipo, descripcion in NIVELES_PH:
        if valor < limite:
            break
    return {"nombre": nombre, "tipo": tipo, "descripcion": descripcion, "detalle": f"pH estimado: {valor:.1f}."}


# ---------------- Terreno (SRTM) ----------------
NIVELES_PENDIENTE = [  # (pendiente % menor a…, nombre, descripción)
    (2, "Plano", "El agua de lluvia o riego casi no escurre."),
    (5, "Poco inclinado", "El agua escurre un poco; hay algo de riesgo de que arrastre la tierra."),
    (10, "Inclinado", "El agua escurre y puede arrastrar la tierra fértil (erosión)."),
    (999, "Muy inclinado", "Alto riesgo de que la lluvia arrastre la tierra fértil (erosión)."),
]


def terreno(rel, grupo_textura=None):
    pendiente = rel.get("pendiente_pct")
    if pendiente is None:
        return {"error": "No hay datos de relieve para este punto."}
    for limite, nombre, descripcion in NIVELES_PENDIENTE:
        if pendiente < limite:
            break
    if nombre == "Plano" and grupo_textura == "Arcillosa":
        que_hacer = "nivela bien la parcela: en tierra plana y arcillosa el agua se encharca."
    elif nombre == "Plano":
        que_hacer = "no necesitas cuidados especiales por la pendiente."
    else:
        que_hacer = "deja el rastrojo como cobertura y siembra en contra de la pendiente (curvas de nivel)."
    return {"nombre": nombre, "descripcion": descripcion, "que_hacer": que_hacer,
            "detalle": f"Pendiente aproximada {pendiente:.1f} %, altura {rel['altura_m']} m sobre el nivel del mar."}
