"""Pantalla "Tus próximos 3 ciclos": arma planes de rotación (A, B, C) a partir del
catálogo (data/cultivos.json) y los califica en agua, suelo y riesgo si hay sequía.
Las reglas están aquí arriba para que el equipo las ajuste.
"""
from datetime import date

from backend.sembrar import catalogo

NA = "n/a"
DESCANSO = {"id": "descanso", "nombre": "Descanso", "familia": "—", "nitrogeno": "neutro", "agua": 0}

# ---- Reglas ajustables ----
AGUA_MUCHA, AGUA_MEDIA = 7000, 5000          # m³/ha promedio por ciclo sembrado
SEQUIA_BAJO, SEQUIA_MEDIO = 3000, 5000       # m³/ha del cultivo que más pide (con lo mínimo)
ORDEN_VEREDICTO = {"Sí conviene": 0, "Sí, si tienes riego asegurado": 1, "Con cuidado": 2}
NO_CONVIENE = "No conviene aquí"


def _temporada(cultivo):
    return "PV" if cultivo["temporada"].startswith("Primavera") else "OI"


def _resumen(c, veredictos):
    """Lo que necesitan los planes de cada cultivo."""
    a = c["agua"]
    completo = a["m3_ha_tipico"] or ((a["m3_ha_min"] + a["m3_ha_max"]) / 2 if a["m3_ha_min"] and a["m3_ha_max"] else None)
    return {
        "id": c["id"],
        "nombre": c["nombre"],
        "familia": c["familia"].split(" (")[0],   # "Gramínea", "Leguminosa", "Oleaginosa"
        "nitrogeno": c["rotacion"]["nitrogeno"],
        "temporada": _temporada(c),
        "agua": completo,
        "agua_min": a["m3_ha_min"] or completo,
        "superficie": c["superficie_sonora_2025_ha"]["valor"] or 0,
        "veredicto": veredictos.get(c["id"], NA),
    }


def _ciclos(hoy):
    """Los próximos 3 ciclos, alternando Otoño-Invierno (OI) y Primavera-Verano (PV)."""
    if hoy.month >= 7:
        inicio = ("OI", hoy.year)
    else:
        inicio = ("PV", hoy.year)
    ciclos, (temporada, año) = [], inicio
    for _ in range(3):
        if temporada == "OI":
            ciclos.append({"temporada": "OI", "etiqueta": f"Inv. {año % 100}-{(año + 1) % 100}"})
            temporada, año = "PV", año + 1
        else:
            ciclos.append({"temporada": "PV", "etiqueta": f"Ver. {año}"})
            temporada = "OI"
    return ciclos


def _mejor(opciones, clave):
    return min(opciones, key=clave) if opciones else None


def generar(ultimo_id, lamina_cm, veredictos):
    """veredictos: {cultivo_id: veredicto de "¿Qué sembrar?"} para descartar los que no convienen."""
    cultivos = [_resumen(c, veredictos) for c in catalogo()]
    viables = [c for c in cultivos if c["veredicto"] != NO_CONVIENE]
    ultimo = next((c for c in cultivos if c["id"] == ultimo_id), DESCANSO)
    disponible = lamina_cm * 100 if lamina_cm else None   # m³/ha
    ciclos = _ciclos(date.today())

    def candidatos(temporada, evitar_familia=None):
        return [c for c in viables if c["temporada"] == temporada and c["familia"] != evitar_familia]

    def rango(c):  # mejor veredicto primero, luego lo más sembrado en la región
        return (ORDEN_VEREDICTO.get(c["veredicto"], 9), -c["superficie"])

    def armar(elegir):
        """Recorre los ciclos; en verano descansa salvo que el plan diga otra cosa."""
        plan, anterior = [], ultimo
        for ciclo in ciclos:
            cultivo = elegir(ciclo["temporada"], anterior) or DESCANSO
            plan.append(cultivo)
            if cultivo is not DESCANSO:
                anterior = cultivo
        return plan

    # Plan A: seguir igual (repite lo último en su temporada)
    def seguir_igual(temporada, anterior):
        return ultimo if ultimo is not DESCANSO and ultimo["temporada"] == temporada else None

    # Plan B: rotar para cuidar el suelo
    def rotar(temporada, anterior):
        if temporada == "PV":
            return None
        if anterior["nitrogeno"] in ("gasta", "gasta_mucho"):
            leguminosas = [c for c in candidatos("OI") if c["nitrogeno"] == "aporta"]
            return _mejor(leguminosas, rango)
        opciones = [c for c in candidatos("OI", evitar_familia=anterior["familia"]) if c["nitrogeno"] != "aporta"]
        return _mejor(opciones, rango)

    # Plan C: ahorrar agua (lo que menos pide, sin repetir familia)
    def ahorrar(temporada, anterior):
        if temporada == "PV":
            return None
        opciones = candidatos("OI", evitar_familia=anterior["familia"])
        return _mejor(opciones, lambda c: (c["agua_min"], rango(c)))

    planes = [
        _calificar("A", "Seguir igual", armar(seguir_igual), ciclos, ultimo, disponible),
        _calificar("B", "Rotar para cuidar tu suelo", armar(rotar), ciclos, ultimo, disponible),
        _calificar("C", "Ahorrar agua", armar(ahorrar), ciclos, ultimo, disponible),
    ]

    # Recomendado: el que mejora el suelo y cabe en el agua; si no cabe ninguno, el que menos agua pide
    def puntaje(p):
        suelo = {"Mejora": 0, "Se mantiene": 1, "Se desgasta": 2}[p["suelo"]["nivel"]]
        return (0 if p["alcanza"] is not False else 1, suelo, p["agua"]["promedio_m3"])
    recomendado = min((p for p in planes if p["aplica"]), key=puntaje)
    recomendado["recomendado"] = True
    return {"ultimo": ultimo["nombre"], "lamina_cm": lamina_cm, "ciclos": [c["etiqueta"] for c in ciclos],
            "planes": planes}


def _calificar(letra, titulo, plan, ciclos, ultimo, disponible):
    sembrados = [c for c in plan if c is not DESCANSO]
    if not sembrados:
        return {"letra": letra, "titulo": titulo, "recomendado": False, "aplica": False, "ciclos": [],
                "texto": "No aplica: la última vez dejaste la tierra en descanso."}

    # Agua
    promedio = sum(c["agua"] or 0 for c in sembrados) / len(sembrados)
    nivel_agua = ("Mucha", "peligro") if promedio >= AGUA_MUCHA else ("Media", "alerta") if promedio >= AGUA_MEDIA else ("Poca", "bueno")

    # Suelo: se desgasta si se repite familia seguida (contando lo último que sembró)
    secuencia = ([ultimo] if ultimo is not DESCANSO else []) + sembrados
    repite = any(a["familia"] == b["familia"] for a, b in zip(secuencia, secuencia[1:]))
    leguminosa_tras_gasto = any(a["nitrogeno"] in ("gasta", "gasta_mucho") and b["nitrogeno"] == "aporta"
                                for a, b in zip(secuencia, secuencia[1:]))
    if repite:
        suelo = ("Se desgasta", "peligro")
    elif leguminosa_tras_gasto:
        suelo = ("Mejora", "bueno")
    else:
        suelo = ("Se mantiene", "alerta")

    # Si hay sequía: el cultivo que más agua necesita, aun con lo mínimo
    peor = max(sembrados, key=lambda c: c["agua_min"] or 0)
    m = peor["agua_min"] or 0
    sequia = ("Bajo", "bueno") if m <= SEQUIA_BAJO else ("Medio", "alerta") if m <= SEQUIA_MEDIO else ("Alto", "peligro")

    # ¿Cabe en el agua que suele tener?
    alcanza = None if disponible is None else all((c["agua_min"] or 0) <= disponible for c in sembrados)
    no_caben = [] if disponible is None else list(dict.fromkeys(c["nombre"] for c in sembrados if (c["agua_min"] or 0) > disponible))

    return {
        "letra": letra,
        "titulo": titulo,
        "recomendado": False,
        "aplica": True,
        "ciclos": [{"id": c["id"], "nombre": c["nombre"], "etiqueta": ciclo["etiqueta"]} for c, ciclo in zip(plan, ciclos)],
        "agua": {"nivel": nivel_agua[0], "tipo": nivel_agua[1], "promedio_m3": round(promedio)},
        "suelo": {"nivel": suelo[0], "tipo": suelo[1]},
        "sequia": {"nivel": sequia[0], "tipo": sequia[1], "cultivo": peor["nombre"]},
        "alcanza": alcanza,
        "aviso": f"Con el agua que sueles tener no alcanza para: {', '.join(no_caben)}." if no_caben else None,
        "texto": _explicar(letra, plan, ultimo, repite, leguminosa_tras_gasto, peor),
    }


def _explicar(letra, plan, ultimo, repite, leguminosa_tras_gasto, peor):
    sembrados = [c for c in plan if c is not DESCANSO]
    nombres = [c["nombre"].lower() for c in sembrados]
    if letra == "A":
        if repite:
            return (f"Repetir {nombres[0]} agota la tierra, favorece plagas y enfermedades, "
                    f"y depende de que haya suficiente agua cada año.")
        return f"Mantiene lo que ya conoces: {', '.join(nombres)}."
    partes = []
    leguminosa = next((c for c in sembrados if c["nitrogeno"] == "aporta"), None)
    if leguminosa_tras_gasto and leguminosa:
        partes.append(f"El {leguminosa['nombre'].lower()} deja nitrógeno en el suelo; "
                      f"el cultivo siguiente necesita menos fertilizante")
    if letra == "C":
        partes.append(f"Son los que menos agua piden: el que más necesita es {peor['nombre'].lower()}, "
                      f"con ~{round((peor['agua_min'] or 0) / 100)} cm de lámina como mínimo")
    if any(c is DESCANSO for c in plan):
        partes.append("en verano la tierra descansa y se ahorra agua en la época más caliente")
    return " ".join(f[0].upper() + f[1:] + "." for f in partes) if partes else NA
