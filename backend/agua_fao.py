"""Agua de riego que necesita un cultivo, calculada con el método de la FAO.
Se usa FUERA de la región del catálogo (fuera de Sonora), donde no hay datos locales del INIFAP.

1. Evapotranspiración de referencia ET0 (Hargreaves-Samani, FAO-56 ec. 52) con la temperatura
   máxima y mínima de NASA POWER y la radiación extraterrestre según latitud y día (FAO-56 ec. 21).
2. Agua del cultivo ETc = Kc × ET0, con la curva de Kc por etapas (FAO-24 Tabla 21 para Kc medio y final).
3. Menos la lluvia efectiva (fórmula de la FAO / USDA, por bloques de 30 días).
4. Entre la eficiencia de riego por gravedad → agua bruta que hay que aplicar en la parcela.

Los valores de las reglas están arriba para que el equipo los ajuste.
"""
import math
from datetime import timedelta
from statistics import mean

# ---- Reglas ajustables ----
KC_INICIAL = 0.4                          # FAO-56: típico 0.3-0.5 en cultivos de campo con riegos espaciados
ETAPAS = (0.15, 0.25, 0.40, 0.20)         # proporción del ciclo: inicial, desarrollo, media, final (FAO-56 típico)
EFICIENCIA_RIEGO = 0.65                   # riego por gravedad / rodado
BLOQUE_LLUVIA = 30                        # días para aplicar la fórmula de lluvia efectiva


def radiacion_extraterrestre(lat, dia_del_año):
    """Ra en mm/día equivalentes (FAO-56 ec. 21, × 0.408 para pasar de MJ/m²/día a mm/día)."""
    phi = math.radians(lat)
    dr = 1 + 0.033 * math.cos(2 * math.pi * dia_del_año / 365)
    delta = 0.409 * math.sin(2 * math.pi * dia_del_año / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    ra_mj = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return 0.408 * ra_mj


def et0_hargreaves(tmax, tmin, lat, dia_del_año):
    tmedia = (tmax + tmin) / 2
    return 0.0023 * (tmedia + 17.8) * math.sqrt(max(tmax - tmin, 0)) * radiacion_extraterrestre(lat, dia_del_año)


def _kc(fraccion, kc_medio, kc_final):
    """Curva de Kc según qué tanto del ciclo ha pasado (0 a 1)."""
    ini, des, med, _ = ETAPAS
    if fraccion < ini:
        return KC_INICIAL
    if fraccion < ini + des:
        return KC_INICIAL + (kc_medio - KC_INICIAL) * (fraccion - ini) / des
    if fraccion < ini + des + med:
        return kc_medio
    return kc_medio + (kc_final - kc_medio) * (fraccion - ini - des - med) / (1 - ini - des - med)


def _lluvia_efectiva(mm_en_30_dias):
    """Fórmula de la FAO (USDA simplificada) para un bloque de ~30 días."""
    if mm_en_30_dias > 75:
        return 0.8 * mm_en_30_dias - 25
    return max(0.0, 0.6 * mm_en_30_dias - 10)


def necesidad_de_riego(cultivo, clima, siembra, dias, lat):
    """clima: climatología por día del año (ver sembrar._climatologia).
    Devuelve los mm del ciclo y los m³/ha de riego bruto, o None si el cultivo no tiene Kc."""
    kc = cultivo["kc"]
    if kc["media_humedo"] is None or kc["media_seco"] is None:
        return None
    # Sin humedad relativa diaria, usamos el promedio de las columnas húmeda y seca de la FAO-24
    kc_medio = (kc["media_humedo"] + kc["media_seco"]) / 2
    kc_final = (kc["final_humedo"] + kc["final_seco"]) / 2

    etc_total = lluvia_total = efectiva_total = 0.0
    bloque = 0.0
    for d in range(dias):
        dia = (siembra + timedelta(days=d)).timetuple().tm_yday
        if dia not in clima:
            continue
        c = clima[dia]
        et0 = et0_hargreaves(mean(c["tmax"]), mean(c["tmin"]), lat, dia)
        etc_total += _kc(d / dias, kc_medio, kc_final) * et0
        bloque += c["lluvia_media"]
        lluvia_total += c["lluvia_media"]
        if (d + 1) % BLOQUE_LLUVIA == 0 or d == dias - 1:
            efectiva_total += _lluvia_efectiva(bloque * BLOQUE_LLUVIA / ((d % BLOQUE_LLUVIA) + 1)) * ((d % BLOQUE_LLUVIA) + 1) / BLOQUE_LLUVIA
            bloque = 0.0

    efectiva_total = min(efectiva_total, etc_total)
    neto = max(0.0, etc_total - efectiva_total)
    return {
        "etc_mm": round(etc_total),
        "lluvia_mm": round(lluvia_total),
        "lluvia_efectiva_mm": round(efectiva_total),
        "riego_neto_mm": round(neto),
        "riego_bruto_m3_ha": round(neto / EFICIENCIA_RIEGO * 10),   # 1 mm = 10 m³/ha
        "metodo": (f"FAO calculation with your area's climate (NASA POWER): the crop uses ~{etc_total:.0f} mm over its cycle, "
                   f"rain provides ~{efectiva_total:.0f} mm of usable water; irrigation at {EFICIENCIA_RIEGO:.0%} efficiency."),
    }
