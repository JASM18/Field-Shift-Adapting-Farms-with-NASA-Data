"""Pantalla "¿Te alcanza el agua?": compara el agua que le asignaron al agricultor
con el agua que pide cada cultivo del catálogo (data/cultivos.json, valores del INIFAP).

Agua disponible (m³) = hectáreas × lámina asignada (m) × 10,000
Agua que pide un cultivo (m³) = m³ por hectárea del catálogo × hectáreas
"""
from backend.sembrar import aviso_fuera_de_region, catalogo, region

NA = "n/a"


def _millares(m3):
    """Los distritos de riego hablan en "millares de m³" (miles de metros cúbicos)."""
    return round(m3 / 1000)


def calcular(hectareas, lamina_cm, dentro_region=True):
    disponible = hectareas * (lamina_cm / 100) * 10_000
    cultivos = []
    for c in catalogo():
        a = c["agua"]
        # Riego completo: el valor típico; si la fuente solo da un rango, el punto medio
        completo = a["m3_ha_tipico"] or (
            (a["m3_ha_min"] + a["m3_ha_max"]) / 2 if a["m3_ha_min"] and a["m3_ha_max"] else None)
        minimo = a["m3_ha_min"]  # lo menos que menciona la fuente (riego reducido o extremo bajo del rango)
        if completo is None:
            cultivos.append({"id": c["id"], "nombre": c["nombre"], "estado": "sin_dato",
                             "texto": NA, "necesita": NA})
            continue

        necesita = completo * hectareas
        necesita_min = (minimo or completo) * hectareas
        if disponible >= necesita:
            estado, texto = "alcanza", "Alcanza"
        elif disponible >= necesita_min:
            estado, texto = "limitado", "Alcanza con lo mínimo"
        else:
            estado, texto = "falta", f"Faltan {_millares(necesita_min - disponible)}"

        rango = minimo is not None and minimo != completo
        cultivos.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "estado": estado,
            "texto": texto,
            "necesita": _millares(necesita),
            "necesita_min": _millares(necesita_min) if rango else None,
            "riegos": a["riegos"] if a["riegos"] is not None else NA,
            "detalle": a["detalle"],
            "fuente": a["fuente"],
        })

    orden = {"alcanza": 0, "limitado": 1, "falta": 2, "sin_dato": 3}
    cultivos.sort(key=lambda x: (orden[x["estado"]], x["necesita"] if x["necesita"] != NA else 1e9))
    return {
        "hectareas": hectareas,
        "lamina_cm": lamina_cm,
        "disponible_m3": round(disponible),
        "disponible_millares": _millares(disponible),
        "cultivos": cultivos,
        "aviso_region": None if dentro_region else (
            f"Estás fuera de {region()['nombre']}: el agua que pide cada cultivo es la que recomienda el INIFAP "
            f"para esa región. En tu zona puede ser distinta según el calor y la lluvia."),
    }
