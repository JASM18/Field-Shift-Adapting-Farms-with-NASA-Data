"""Pantalla "¿Qué quieres sembrar?": cruza el catálogo de cultivos (data/cultivos.json)
con el clima de la zona (30 años de NASA POWER), el pronóstico de 6 meses (Open-Meteo),
el suelo (SoilGrids) y la humedad actual. Las reglas están aquí arriba para ajustarlas.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

from backend.nasa_power import VALOR_VACIO

ARCHIVO_CATALOGO = Path(__file__).parent.parent / "data" / "cultivos.json"
NA = "n/a"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
INICIALES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

# ---- Reglas ajustables ----
CICLO_SI_NO_HAY_DATO = 120      # días, si el catálogo no trae la duración del ciclo
MIN_DIAS_EN_OPTIMO = 0.4        # si menos del 40 % del ciclo está en temperatura óptima: no conviene
MARGEN_LIMITE = 1.0             # °C fuera del límite absoluto que ya se considera "no conviene"
HELADA_RIESGOSA = 0.3           # probabilidad de helada en el ciclo (3 de cada 10 años) para "con cuidado"
DIA_DE_CALOR = 35               # °C de máxima
DIAS_CALOR_RIESGOSOS = 10       # días de calor al final del ciclo para "con cuidado"
FINAL_DEL_CICLO = 0.4           # el último 40 % del ciclo (floración y llenado de grano)
LLUVIA_SUFICIENTE = 0.8         # si la lluvia cubre el 80 % del agua que pide, no necesita riego
AGUA_MUCHA, AGUA_MEDIA = 7000, 5000   # m³/ha para decir "mucha" / "media" / "poca"
MARGEN_PH = 0.5                 # pasarse del pH límite por menos que esto solo genera un aviso


def catalogo():
    return json.loads(ARCHIVO_CATALOGO.read_text())["cultivos"]


def lista_cultivos():
    return [{"id": c["id"], "nombre": c["nombre"]} for c in catalogo()]


def _fecha(mm_dd, año):
    mes, dia = map(int, mm_dd.split("-"))
    return date(año, mes, dia)


def _ventanas_para(cultivo, grupo_textura):
    """Elige las ventanas de siembra que aplican a la parcela.
    Si el catálogo distingue por tipo de suelo, se usa el de la parcela."""
    ventanas = cultivo["siembra"]["ventanas"]
    por_suelo = [v for v in ventanas if "suelo" in v["region"].lower()]
    if por_suelo:
        clave = "arcilloso" if grupo_textura == "Arcillosa" else "aluvión"
        elegidas = [v for v in por_suelo if clave in v["region"].lower()]
        return elegidas or por_suelo[:1]
    return [v for v in ventanas if "hermosillo" not in v["region"].lower()] or ventanas


def _proximo_fin(ventana, hoy):
    """Fecha en que termina la próxima vez que se abre esta ventana de siembra."""
    fin = _fecha(ventana["fin"], hoy.year)
    return fin if fin >= hoy else _fecha(ventana["fin"], hoy.year + 1)


def _calendario(ventanas):
    """Clase de cada mes: 'mejor' (fecha óptima), 'se_puede' (resto de la ventana) o 'no'."""
    meses = ["no"] * 12

    def marcar(inicio, fin, clase):
        actual = _fecha(inicio, 2001)
        final = _fecha(fin, 2001 if _fecha(fin, 2001) >= actual else 2002)
        while actual <= final:
            i = actual.month - 1
            if meses[i] != "mejor":
                meses[i] = clase
            actual += timedelta(days=1)

    for v in ventanas:
        if v.get("optima_inicio"):
            marcar(v["inicio"], v["fin"], "se_puede")
            marcar(v["optima_inicio"], v["optima_fin"], "mejor")
        else:
            marcar(v["inicio"], v["fin"], "mejor")
    return meses


def _texto_fechas(v):
    ini, fin = _fecha(v.get("optima_inicio") or v["inicio"], 2001), _fecha(v.get("optima_fin") or v["fin"], 2001)
    return f"Del {ini.day} de {MESES[ini.month - 1]} al {fin.day} de {MESES[fin.month - 1]}"


def _climatologia(historico):
    """Promedio de 30 años para cada día del año: máxima, mínima, media y lluvia.
    También guarda, por año, la mínima de cada día (para calcular heladas)."""
    por_dia = {}
    for fecha, tmax in historico["T2M_MAX"].items():
        tmin = historico["T2M_MIN"].get(fecha, VALOR_VACIO)
        lluvia = historico["PRECTOTCORR"].get(fecha, VALOR_VACIO)
        if VALOR_VACIO in (tmax, tmin):
            continue
        dia = datetime.strptime(fecha, "%Y%m%d").timetuple().tm_yday
        d = por_dia.setdefault(dia, {"tmax": [], "tmin": [], "lluvia": [], "minimas_por_año": {}})
        d["tmax"].append(tmax)
        d["tmin"].append(tmin)
        if lluvia != VALOR_VACIO:
            d["lluvia"].append(lluvia)
        d["minimas_por_año"][fecha[:4]] = tmin
    return por_dia


def _periodo(inicio, dias):
    """Días del año (1-366) que dura el ciclo empezando en la fecha de siembra."""
    return [(inicio + timedelta(days=d)).timetuple().tm_yday for d in range(dias)]


def evaluar(cultivo_id, historico, pronostico=None, suelo_props=None, grupo_textura=None, humedad=None):
    cultivo = next((c for c in catalogo() if c["id"] == cultivo_id), None)
    if cultivo is None:
        return {"error": f"No conozco el cultivo '{cultivo_id}'."}

    hoy = date.today()
    ventanas = _ventanas_para(cultivo, grupo_textura)
    principal = min(ventanas, key=lambda v: _proximo_fin(v, hoy))  # la próxima (o la que está abierta)

    # Fecha de siembra de referencia: el centro de la fecha óptima, en la próxima temporada
    ini = principal.get("optima_inicio") or principal["inicio"]
    fin = principal.get("optima_fin") or principal["fin"]
    año = hoy.year if _fecha(fin, hoy.year) >= hoy else hoy.year + 1
    f_ini = _fecha(ini, año if _fecha(ini, año) <= _fecha(fin, año) else año - 1)
    f_fin = _fecha(fin, año)
    siembra = f_ini + (f_fin - f_ini) / 2

    ciclo = cultivo["ciclo_dias"]
    dias = ciclo["max"] or ciclo["min"] or CICLO_SI_NO_HAY_DATO
    if ciclo["max"] is None and ciclo["min"]:
        dias = max(dias, CICLO_SI_NO_HAY_DATO)  # ej. sorgo: primer corte a los 50 días, pero da varios
    periodo = _periodo(siembra, dias)

    # ---- Clima del ciclo (30 años) ----
    clima = _climatologia(historico)
    medias = [mean(clima[d]["tmax"] + clima[d]["tmin"]) for d in periodo if d in clima]
    opt_min, opt_max = cultivo["clima"]["temp_media_optima"]
    lim_min, lim_max = cultivo["clima"]["temp_media_limite"]
    en_optimo = sum(opt_min <= t <= opt_max for t in medias) / len(medias)
    fuera_limite = [t for t in medias if t < lim_min - MARGEN_LIMITE or t > lim_max + MARGEN_LIMITE]
    temp_media = mean(medias)

    años = {a for d in periodo if d in clima for a in clima[d]["minimas_por_año"]}
    años_helada = {a for d in periodo if d in clima
                   for a, tmin in clima[d]["minimas_por_año"].items() if tmin <= 0}
    prob_helada = len(años_helada) / len(años) if años else 0
    sensible_helada = (cultivo["clima"]["temp_mortal_crecimiento"] is None
                       or cultivo["clima"]["temp_mortal_crecimiento"] > -3)

    final = periodo[int(len(periodo) * (1 - FINAL_DEL_CICLO)):]
    dias_calor = sum(mean(1 if t >= DIA_DE_CALOR else 0 for t in clima[d]["tmax"]) for d in final if d in clima)

    lluvia_ciclo = sum(mean(clima[d]["lluvia"]) for d in periodo if d in clima and clima[d]["lluvia"])
    agua = cultivo["agua"]
    agua_m3 = agua["m3_ha_tipico"] or (mean([agua["m3_ha_min"], agua["m3_ha_max"]])
                                       if agua["m3_ha_min"] and agua["m3_ha_max"] else None)

    # ---- Veredicto ----
    avisos = []
    if fuera_limite or en_optimo < MIN_DIAS_EN_OPTIMO:
        veredicto, tipo = "No conviene aquí", "peligro"
        razon = (f"Durante su ciclo la temperatura media es de ~{temp_media:.0f} °C y este cultivo "
                 f"necesita {opt_min}–{opt_max} °C.")
    else:
        razon = f"El clima de {MESES[siembra.month - 1]} a {MESES[(siembra + timedelta(days=dias)).month - 1]} le queda bien"
        if prob_helada >= HELADA_RIESGOSA and sensible_helada:
            veredicto, tipo = "Con cuidado", "alerta"
            razon += f", pero en {round(prob_helada * 10)} de cada 10 años hubo heladas durante su ciclo."
        elif dias_calor >= DIAS_CALOR_RIESGOSOS:
            veredicto, tipo = "Con cuidado", "alerta"
            razon += f", pero al final del ciclo hay ~{dias_calor:.0f} días de más de {DIA_DE_CALOR} °C."
        elif agua_m3 and lluvia_ciclo * 10 >= LLUVIA_SUFICIENTE * agua_m3:
            veredicto, tipo = "Sí conviene", "bueno"
            razon += " y la lluvia normal cubre lo que necesita."
        else:
            veredicto, tipo = "Sí, si tienes riego asegurado", "alerta"
            razon += f", pero la lluvia normal (~{lluvia_ciclo:.0f} mm) no alcanza: necesita riego."

    # Suelo
    if suelo_props and suelo_props.get("phh2o") is not None:
        ph = suelo_props["phh2o"]
        p_min, p_max = cultivo["suelo"]["ph_limite"]
        if not p_min <= ph <= p_max:
            avisos.append(f"Tu suelo tiene pH {ph:.1f} y este cultivo tolera {p_min}–{p_max}.")
            fuera = max(p_min - ph, ph - p_max)
            if fuera > MARGEN_PH and tipo in ("bueno", "alerta") and veredicto != "Con cuidado":
                veredicto, tipo = "Con cuidado", "alerta"

    # Humedad actual
    if humedad and "nombre" in humedad and humedad["indice"] <= 1:
        avisos.append("Ahora el suelo está más seco de lo normal: necesitarás un buen riego de presiembra.")

    # ---- Este año (pronóstico de 6 meses) ----
    este_año = _resumen_pronostico(pronostico, siembra, dias) if pronostico else None

    # ---- Riesgos ----
    riesgos = []
    if prob_helada > 0 and sensible_helada:
        riesgos.append(f"En {round(prob_helada * 10) or 1} de cada 10 años hubo al menos una helada durante su ciclo.")
    if dias_calor >= 1:
        riesgos.append(f"Al final del ciclo hay ~{dias_calor:.0f} días de más de {DIA_DE_CALOR} °C al año.")
    riesgos += [r["texto"] for r in cultivo["clima"]["riesgos"]]

    return {
        "id": cultivo["id"],
        "nombre": cultivo["nombre"],
        "veredicto": veredicto,
        "tipo": tipo,
        "razon": razon,
        "avisos": avisos,
        "este_año": este_año,
        "siembra": {
            "texto": _texto_fechas(principal),
            "region": principal["region"],
            "nota": principal.get("nota") or NA,
            "otras": [f"{v['region']}: {_texto_fechas(v)}" for v in cultivo["siembra"]["ventanas"] if v is not principal],
            "meses": [{"inicial": INICIALES[i], "mes": MESES[i], "clase": c} for i, c in enumerate(_calendario(ventanas))],
        },
        "agua": {
            "nivel": NA if agua_m3 is None else ("Mucha" if agua_m3 >= AGUA_MUCHA else "Media" if agua_m3 >= AGUA_MEDIA else "Poca"),
            "m3_ha": NA if agua_m3 is None else round(agua_m3),
            "lamina_cm": NA if agua_m3 is None else round(agua_m3 / 100),
            "riegos": agua["riegos"] if agua["riegos"] is not None else NA,
            "detalle": agua["detalle"],
            "porcentaje": None if agua_m3 is None else min(100, round(100 * agua_m3 / 12000)),
        },
        "riesgos": riesgos,
        "bueno_saber": _consejo_rotacion(cultivo),
        "rendimiento": _texto_rendimiento(cultivo["rendimiento"]),
        "ciclo": f"{dias} días" + ("" if ciclo["max"] or ciclo["min"] else " (estimado; n/a en la fuente)"),
        "detalle_clima": (f"Temperatura media durante el ciclo: ~{temp_media:.0f} °C "
                          f"({en_optimo:.0%} de los días en su rango óptimo de {opt_min}–{opt_max} °C). "
                          f"Lluvia normal en el ciclo: ~{lluvia_ciclo:.0f} mm. Promedio de 30 años de NASA POWER."),
        "fuentes": sorted({cultivo["siembra"]["fuente"], cultivo["agua"]["fuente"], cultivo["clima"]["fuente"],
                           cultivo["suelo"]["fuente"], cultivo["rendimiento"]["fuente"]} - {None}),
    }


def _resumen_pronostico(pronostico, siembra, dias):
    """Qué dice el pronóstico de 6 meses para el ciclo (solo la parte que alcanza a cubrir)."""
    fechas = pronostico["time"]
    fin_ciclo = siembra + timedelta(days=dias)
    indices = [i for i, f in enumerate(fechas) if siembra.isoformat() <= f <= fin_ciclo.isoformat()]
    if not indices:
        return None
    maximas = pronostico["miembros"]["temperature_2m_max"]
    minimas = pronostico["miembros"]["temperature_2m_min"]
    lluvias = pronostico["miembros"]["precipitation_sum"]
    n = len(maximas)
    con_helada = sum(1 for m in minimas if any(m[i] is not None and m[i] <= 0 for i in indices))
    con_calor = sum(1 for m in maximas if sum(1 for i in indices if m[i] is not None and m[i] >= DIA_DE_CALOR) >= 5)
    lluvia = mean(sum(m[i] or 0 for i in indices) for m in lluvias)
    hasta = datetime.strptime(fechas[indices[-1]], "%Y-%m-%d").date()

    def de_cada_10(cuantos):
        decimos = round(10 * cuantos / n)
        return f"{decimos} de cada 10 escenarios" if decimos else "menos de 1 de cada 10 escenarios"

    partes = []
    partes.append(f"helada en {de_cada_10(con_helada)}" if con_helada else "sin heladas")
    if con_calor:
        partes.append(f"5 o más días de más de {DIA_DE_CALOR} °C en {de_cada_10(con_calor)}")
    partes.append(f"~{lluvia:.0f} mm de lluvia")
    cubre = "todo el ciclo" if hasta >= fin_ciclo - timedelta(days=1) else f"hasta el {hasta.day} de {MESES[hasta.month - 1]}"
    return f"Pronóstico de 6 meses de Open-Meteo/ECMWF ({cubre}): " + ", ".join(partes) + "."


def _consejo_rotacion(cultivo):
    nombre = cultivo["nombre"].lower()
    consejos = {
        "gasta_mucho": f"El {nombre} gasta mucho nitrógeno: después conviene una leguminosa como garbanzo o frijol, que lo devuelve al suelo y usa menos agua.",
        "gasta": f"Después del {nombre} conviene una leguminosa (garbanzo o frijol) para reponer nitrógeno.",
        "aporta": f"El {nombre} deja nitrógeno en el suelo: el cultivo que siembres después necesitará menos fertilizante.",
    }
    return consejos.get(cultivo["rotacion"]["nitrogeno"], NA)


def _texto_rendimiento(r):
    if r["promedio"] is not None:
        valor = f"~{r['promedio']:g}"
    elif r.get("rango"):
        valor = f"{r['rango'][0]:g}–{r['rango'][1]:g}"
    else:
        return NA
    return f"{valor} {r['unidad']}"
