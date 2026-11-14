"""Motor de recomendación: aptitud de cultivos por temporada + búsqueda de rotaciones.

Es un sistema de reglas transparente (no una caja negra), para que el agricultor
vea POR QUÉ se sugiere algo y mantenga su propio criterio.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "crops.json"

# Temporadas típicas en México (ajustables): Primavera-Verano y Otoño-Invierno
SEASONS = {
    "PV": {"nombre": "Primavera-Verano", "meses": [5, 6, 7, 8, 9, 10]},
    "OI": {"nombre": "Otoño-Invierno", "meses": [11, 12, 1, 2, 3, 4]},
}

FALLOW = {"nombre": "Descanso (rastrojo como cobertura)", "familia": "—", "nitrogeno": 0,
          "raiz": "superficial", "biomasa": 1, "forraje": 0}


def load_crops() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["cultivos"]


@dataclass
class Fit:
    crop: dict
    score: float                     # 0-100
    water_deficit_mm: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _range_score(value: float, lo: float, hi: float, tolerance: float) -> float:
    """1 dentro del rango, decae linealmente hasta 0 a `tolerance` unidades fuera."""
    if lo <= value <= hi:
        return 1.0
    dist = lo - value if value < lo else value - hi
    return max(0.0, 1 - dist / tolerance)


def crop_fit(crop: dict, season: dict, soil: dict, irrigation: bool) -> Fit:
    reasons, warnings = [], []

    lo, hi = crop["t_opt"]
    t = _range_score(season["t_mean"], lo, hi, tolerance=6)
    if t == 1:
        # Dentro del rango: un poco mejor cuanto más cerca del centro (desempata)
        t = 1 - 0.2 * abs(season["t_mean"] - (lo + hi) / 2) / ((hi - lo) / 2)
        reasons.append(f"Temperatura media {season['t_mean']:.1f}°C dentro de su óptimo")
    elif t < 0.5:
        warnings.append(f"Temperatura media {season['t_mean']:.1f}°C fuera de su rango {crop['t_opt']}")

    frost = 1.0
    if season["frost_days"] >= 0.5 and crop["t_min_abs"] > -2:
        sensitivity = 0.15 if crop["t_min_abs"] > 0 else 0.05
        frost = max(0.4, 1 - sensitivity * season["frost_days"])
        warnings.append(f"~{season['frost_days']:.1f} días de helada al año en esta temporada")

    need_min, need_opt = crop["agua_mm"]
    deficit = max(0.0, need_opt - season["rain_mm"])
    if season["rain_mm"] > 1.3 * need_opt and crop["sequia"] >= 2:
        # Cultivos de secano sufren con exceso de agua (hongos, encharcamiento)
        w = max(0.4, 1 - 0.8 * (season["rain_mm"] / need_opt - 1.3))
        warnings.append(f"Exceso de lluvia (~{season['rain_mm']:.0f} mm): riesgo de enfermedades/encharcamiento")
    elif season["rain_mm"] >= need_opt:
        w = 1.0
        reasons.append(f"La lluvia de temporada (~{season['rain_mm']:.0f} mm) cubre su necesidad")
    elif irrigation:
        w = 0.75
        warnings.append(f"Requiere ~{deficit:.0f} mm de riego")
    else:
        w = max(0.0, (season["rain_mm"] - need_min * 0.6) / (need_opt - need_min * 0.6))
        warnings.append(f"Lluvia insuficiente sin riego (~{season['rain_mm']:.0f} de {need_opt} mm)")

    s = 1.0
    if soil.get("ph") is not None:
        s *= _range_score(soil["ph"], *crop["ph"], tolerance=1.5)
        if soil["ph"] < crop["ph"][0] or soil["ph"] > crop["ph"][1]:
            warnings.append(f"pH {soil['ph']} fuera de su rango {crop['ph']}")
    if soil.get("textura") and soil["textura"] not in crop["texturas"]:
        s *= 0.7
        warnings.append(f"Suelo {soil['textura']} no es el ideal")

    score = 100 * (0.35 * t + 0.35 * w + 0.30 * s) * frost
    return Fit(crop, round(score, 1), deficit, reasons, warnings)


def soil_health_score(seq: list[dict]) -> tuple[float, list[str]]:
    """Evalúa la secuencia completa (circular: el último precede al primero). 0-1."""
    notes, pts = [], 0.0
    n = len(seq)
    pairs = [(seq[i], seq[(i + 1) % n]) for i in range(n)]

    same_family = sum(1 for a, b in pairs if a["familia"] == b["familia"] and a["familia"] != "—")
    pts += 1 - same_family / n
    if same_family:
        notes.append(f"{same_family} repetición(es) de familia seguida(s): más riesgo de plagas y desgaste")

    legumes = sum(1 for c in seq if c["nitrogeno"] > 0)
    pts += min(1.0, legumes / max(1, n / 2))
    if legumes:
        notes.append(f"{legumes} leguminosa(s) aportan nitrógeno al suelo")

    heavy_then_legume = sum(1 for a, b in pairs if a["nitrogeno"] <= -2 and b["nitrogeno"] > 0)
    heavy = sum(1 for c in seq if c["nitrogeno"] <= -2)
    pts += heavy_then_legume / heavy if heavy else 1.0

    root_changes = sum(1 for a, b in pairs if a["raiz"] != b["raiz"])
    pts += root_changes / n
    pts += sum(c["biomasa"] for c in seq) / (3 * n)

    return pts / 5, notes


@dataclass
class Rotation:
    sequence: list[tuple[str, dict]]  # [(clave temporada, cultivo)]
    total: float
    climate: float
    soil: float
    water_mm: float
    forage: float
    resilience: float
    notes: list[str]


def best_rotations(fits_by_season: dict[str, list[Fit]], season_order: list[str],
                   priorities: dict[str, float], top_k: int = 6, n_results: int = 5) -> list[Rotation]:
    """Prueba todas las combinaciones entre los mejores `top_k` cultivos de cada temporada."""
    cand = {}
    for key in set(season_order):
        ranked = sorted(fits_by_season[key], key=lambda f: f.score, reverse=True)[:top_k]
        cand[key] = ranked + [Fit(FALLOW, 50.0, 0.0)]

    wp = priorities
    wsum = sum(wp.values()) or 1
    results = []
    for combo in itertools.product(*(cand[k] for k in season_order)):
        crops = [f.crop for f in combo]
        if len({c["nombre"] for c in crops}) < len(crops) - 1:
            continue  # evita monocultivo disfrazado
        climate = sum(f.score for f in combo) / (100 * len(combo))
        soil, notes = soil_health_score(crops)
        water = sum(f.water_deficit_mm for f in combo)
        water_s = max(0.0, 1 - water / (400 * len(combo)))
        forage = sum(c["forraje"] for c in crops) / (3 * len(crops))
        real = [c for c in crops if "sequia" in c]
        resil = sum(c["sequia"] + c["calor"] for c in real) / (6 * len(real)) if real else 0.5

        total = 0.4 * climate + 0.6 * (
            wp["agua"] * water_s + wp["suelo"] * soil + wp["forraje"] * forage + wp["resiliencia"] * resil
        ) / wsum
        results.append(Rotation(list(zip(season_order, crops)), round(100 * total, 1),
                                climate, soil, water, forage, resil, notes))

    results.sort(key=lambda r: r.total, reverse=True)
    # Diversidad en resultados: no mostrar rotaciones que sean la misma con distinto orden
    seen, unique = set(), []
    for r in results:
        sig = frozenset(c["nombre"] for _, c in r.sequence)
        if sig not in seen:
            seen.add(sig)
            unique.append(r)
        if len(unique) == n_results:
            break
    return unique
