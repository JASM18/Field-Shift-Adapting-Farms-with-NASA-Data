"""Convierte los datos diarios de NASA POWER en el resumen de la pantalla
"El clima de tu zona": cómo es normalmente cada mes, en palabras sencillas.

Las reglas (umbrales) están aquí arriba para que el equipo las pueda ajustar.
"""
from statistics import mean

from backend.nasa_power import VALOR_VACIO

MESES_CORTOS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MESES_LARGOS = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]

# ---- Reglas ajustables ----
FRESCO_MENOS_DE = 30          # °C de máxima promedio: barra verde
CALUROSO_MENOS_DE = 35        # °C: barra amarilla; desde aquí, roja
DIA_DE_CALOR_EXTREMO = 38     # °C: un día con esta máxima o más es "de calor extremo"
CALOR_EXTREMO_SI_DIAS = 0.5   # "Calor extremo" si la mitad o más de los días pasan de 38 °C
CALOR_FUERTE_SI_DIAS = 0.2    # "Calor fuerte" si 2 de cada 10 días pasan de 38 °C…
#                               …o si la máxima promedio llega a CALUROSO_MENOS_DE
SECO_MENOS_DE = 10            # mm de lluvia en el mes
POCA_LLUVIA_MENOS_DE = 50     # mm; desde aquí, "Lluvias"
HELADA_SI_AÑOS = 0.1          # "Posible helada" si hubo helada en 1 de cada 10 años o más


def resumen_mensual(datos):
    tmax, tmin, lluvia = datos["T2M_MAX"], datos["T2M_MIN"], datos["PRECTOTCORR"]

    # Juntamos los datos de cada mes de todos los años
    meses = {m: {"maximas": [], "dias_calor": 0, "lluvia": 0.0, "años_con_helada": set()}
             for m in range(1, 13)}
    años = set()

    for fecha, maxima in tmax.items():
        if maxima == VALOR_VACIO:
            continue
        año, mes = int(fecha[:4]), int(fecha[4:6])
        años.add(año)
        m = meses[mes]
        m["maximas"].append(maxima)
        if maxima >= DIA_DE_CALOR_EXTREMO:
            m["dias_calor"] += 1
        if lluvia.get(fecha, VALOR_VACIO) != VALOR_VACIO:
            m["lluvia"] += lluvia[fecha]
        minima = tmin.get(fecha, VALOR_VACIO)
        if minima != VALOR_VACIO and minima <= 0:
            m["años_con_helada"].add(año)

    total_años = len(años)
    resultado = []
    for mes in range(1, 13):
        m = meses[mes]
        maxima = mean(m["maximas"])
        lluvia_mm = m["lluvia"] / total_años
        parte_dias_calor = m["dias_calor"] / len(m["maximas"])
        prob_helada = len(m["años_con_helada"]) / total_años

        # El color se decide con el número redondeado que ve el agricultor (29.6 → 30°)
        if round(maxima) < FRESCO_MENOS_DE:
            nivel = "fresco"
        elif round(maxima) < CALUROSO_MENOS_DE:
            nivel = "caluroso"
        else:
            nivel = "muy_caluroso"

        if lluvia_mm < SECO_MENOS_DE:
            texto_lluvia = "Dry"
        elif lluvia_mm < POCA_LLUVIA_MENOS_DE:
            texto_lluvia = "Little rain"
        else:
            texto_lluvia = "Rainy"

        etiquetas = []
        if parte_dias_calor >= CALOR_EXTREMO_SI_DIAS:
            etiquetas.append({"texto": "Extreme heat", "tipo": "peligro"})
        elif parte_dias_calor >= CALOR_FUERTE_SI_DIAS or maxima >= CALUROSO_MENOS_DE:
            etiquetas.append({"texto": "Strong heat", "tipo": "alerta"})
        if prob_helada >= HELADA_SI_AÑOS:
            etiquetas.append({"texto": "Possible frost", "tipo": "frio"})

        resultado.append({
            "mes": MESES_CORTOS[mes - 1],
            "maxima_promedio": round(maxima, 1),
            "nivel": nivel,
            "lluvia_mm": round(lluvia_mm),
            "texto_lluvia": texto_lluvia,
            "dias_calor_extremo_pct": round(100 * parte_dias_calor),
            "probabilidad_helada_pct": round(100 * prob_helada),
            "etiquetas": etiquetas,
        })

    return {
        "periodo": f"{min(años)}-{max(años)}",
        "total_años": total_años,
        "meses": resultado,
        "avisos": _avisos(resultado),
    }


def _avisos(meses):
    """Los dos recuadros de arriba: meses más frescos y meses de cuidado."""
    avisos = []

    frescos = [m["nivel"] == "fresco" and not any(e["tipo"] in ("peligro", "alerta") for e in m["etiquetas"])
               for m in meses]
    racha = _racha_mas_larga(frescos)
    if racha:
        avisos.append({
            "tipo": "bueno",
            "titulo": "Coolest months",
            "texto": f"{_nombre_rango(racha)}: cool days with no strong heat",
        })

    extremos = [any(e["tipo"] == "peligro" for e in m["etiquetas"]) for m in meses]
    racha = _racha_mas_larga(extremos)
    if racha:
        pct = round(mean(meses[i]["dias_calor_extremo_pct"] for i in racha))
        avisos.append({
            "tipo": "peligro",
            "titulo": "Watch out",
            "texto": f"{_nombre_rango(racha)}: above {DIA_DE_CALOR_EXTREMO} °C on {pct} out of every 100 days",
        })
    return avisos


def _racha_mas_larga(marcas):
    """Índices de los meses seguidos (puede cruzar de diciembre a enero) más larga con marca True."""
    if all(marcas):
        return list(range(12))
    if not any(marcas):
        return []
    inicio = marcas.index(False) + 1  # empezamos justo después de un mes sin marca
    mejor, actual = [], []
    for paso in range(12):
        i = (inicio + paso) % 12
        if marcas[i]:
            actual.append(i)
            if len(actual) > len(mejor):
                mejor = actual[:]
        else:
            actual = []
    return mejor


def _nombre_rango(indices):
    primero = MESES_LARGOS[indices[0]].capitalize()
    if len(indices) == 1:
        return primero
    return f"{primero} to {MESES_LARGOS[indices[-1]]}"
