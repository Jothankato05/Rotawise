"""Compare rotation strategies for one plot and explain each option.

Every option card answers what the Field Shift challenge asks for: why it was
suggested, the evidence, the benefits, the information gaps and the risks a
local extension agent should review. All money figures are ranges built from
editable prices, never single falsely precise numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..messages import m
from .climate import water_fit


@dataclass(frozen=True)
class Prices:
    urea_ngn_per_bag: float
    maize_ngn_per_bag: float
    baseline_maize_t_ha: float


def zone_for(lat: float, cfg: dict[str, Any], lang: str = "en") -> dict[str, str]:
    zones = cfg["zones"]  # ordered north to south
    z = next((z for z in zones if lat >= z["min_lat"]), zones[-1])
    label = m(lang, f"zone_{z['name']}") if lang != "en" else z["label"]
    return {"id": z["name"], "label": label}


def _rng(a: float, b: float, nd: int = 0) -> list[float]:
    return [round(a, nd), round(b, nd)] if nd else [round(a), round(b)]


def economics(crop: dict[str, Any], zone: str, prices: Prices, area_ha: float, cfg: dict[str, Any]) -> dict[str, Any]:
    e = cfg["economics"]
    n_lo, n_hi = crop["n_credit_kg_ha"][zone]
    urea_kg = [n / e["urea_n_fraction"] for n in (n_lo, n_hi)]
    bags = [u / e["urea_bag_kg"] for u in urea_kg]
    fert_ngn = [b * prices.urea_ngn_per_bag for b in bags]

    g_lo, g_hi = crop["maize_yield_gain_after"]
    extra_t = [prices.baseline_maize_t_ha * g for g in (g_lo, g_hi)]
    ngn_per_t = prices.maize_ngn_per_bag * (1000 / e["maize_bag_kg"])
    yield_ngn = [t * ngn_per_t for t in extra_t]

    return {
        "per_ha": {
            "n_credit_kg": _rng(n_lo, n_hi),
            "urea_bags_saved": _rng(*bags, nd=1),
            "fertilizer_saved_ngn": _rng(*fert_ngn),
            "extra_maize_t": _rng(*extra_t, nd=2),
            "extra_maize_value_ngn": _rng(*yield_ngn),
        },
        "plot": {
            "area_ha": area_ha,
            "total_value_ngn": _rng((fert_ngn[0] + yield_ngn[0]) * area_ha, (fert_ngn[1] + yield_ngn[1]) * area_ha),
        },
    }


def _climate_fit(crop: dict[str, Any], proj: dict[str, Any] | None, observed_rain: float | None, cfg: dict[str, Any]) -> dict[str, Any]:
    deficit = cfg["climate"]["rain_deficit_warning_fraction"]
    now = water_fit(observed_rain, crop["water_need_mm"], deficit)
    future_rain = proj["season_rain_mm"] if proj else None
    fut = water_fit(future_rain, crop["water_need_mm"], deficit)
    heat_penalty = 0.0
    if crop.get("heat_sensitive") and proj and proj.get("heat_days") is not None:
        heat_penalty = min(0.3, proj["heat_days"] / 100.0)
    return {
        "water_fit_now": now,
        "water_fit_2040s": fut,
        "heat_penalty": round(heat_penalty, 2),
    }


def compare(
    plot: dict[str, Any],
    memory: dict[str, Any],
    fatigue: dict[str, Any],
    climate: dict[str, Any],
    cfg: dict[str, Any],
    prices: Prices,
    lang: str = "en",
) -> dict[str, Any]:
    crops = cfg["crops"]
    sources = cfg["sources"]
    zone = zone_for(plot["lat"], cfg, lang)
    label = lambda c: crops[c]["label"].get(lang, crops[c]["label"]["en"])  # noqa: E731
    area = float(plot.get("area_ha") or 1.0)
    proj = (climate.get("projections") or {}).get("ssp245_2040s")
    obs_rain = (climate.get("observed") or {}).get("season_rain_mm_median")
    cereal_run = memory["current"]["cereal_run"]
    seasons = memory["seasons"]
    known = [s for s in seasons if s["season_class"] != "unknown"]
    mean_conf = round(sum(s["confidence"] for s in known) / len(known), 2) if known else 0.0
    fatigue_score = fatigue.get("score")

    def card(rid: str, sequence: list[str], is_current: bool) -> dict[str, Any]:
        legume = next((c for c in sequence if crops[c]["type"] == "legume"), None)
        fits = {c: _climate_fit(crops[c], proj, obs_rain, cfg) for c in sequence}
        worst_now = min((f["water_fit_now"] for f in fits.values() if f["water_fit_now"] is not None), default=None)
        worst_fut = min((f["water_fit_2040s"] for f in fits.values() if f["water_fit_2040s"] is not None), default=None)
        heat = max(f["heat_penalty"] for f in fits.values())

        econ = economics(crops[legume], zone["id"], prices, area, cfg) if legume else None
        if econ and "maize" not in sequence:
            # Yield coefficients are measured on maize; do not claim them for other cereals.
            econ["per_ha"]["extra_maize_t"] = None
            econ["per_ha"]["extra_maize_value_ngn"] = None
            fert = econ["per_ha"]["fertilizer_saved_ngn"]
            econ["plot"]["total_value_ngn"] = [round(fert[0] * area), round(fert[1] * area)]
        striga = crops[legume]["striga_reduction"] if legume else [0.0, 0.0]
        n_hi = crops[legume]["n_credit_kg_ha"][zone["id"]][1] if legume else 0

        # Composite score 0-100. Transparent weights.
        soil_part = (n_hi / 55.0) if legume else 0.0
        striga_part = striga[1] if cereal_run >= 2 else striga[1] * 0.5
        water_part = worst_fut if worst_fut is not None else (worst_now if worst_now is not None else 0.5)
        score = 100 * (0.35 * soil_part + 0.25 * striga_part + 0.30 * water_part + 0.10 * (1 - heat * 3))
        if is_current and cereal_run >= 2 and fatigue_score is not None:
            score -= 0.15 * fatigue_score
        score = max(0, min(100, round(score)))

        why: list[str] = []
        if is_current:
            pattern = memory["current"]["pattern"]
            why.append(m(lang, "why_current", pattern=", ".join(m(lang, f"cls_{p}") for p in pattern) or m(lang, "why_current_none")))
            if cereal_run >= 2:
                why.append(m(lang, "why_cereal_run", n=cereal_run))
        else:
            if legume:
                why.append(m(lang, "why_legume", crop=label(legume)))
            if fatigue_score is not None and fatigue_score >= 35:
                why.append(m(lang, "why_fatigue", score=fatigue_score))
        if worst_fut is not None and proj:
            why.append(m(lang, "why_water", mm=proj["season_rain_mm"], fit=f"{worst_fut:.0%}"))

        evidence = sorted({k for c in sequence for k in crops[c]["sources"]})
        gaps: list[str] = []
        if mean_conf < 0.6:
            gaps.append(m(lang, "gap_confidence", pct=f"{mean_conf:.0%}"))
        if obs_rain is None:
            gaps.append(m(lang, "gap_no_rain"))
        if legume:
            gaps.append(m(lang, "gap_legume_price"))
        if not plot.get("coords_verified"):
            gaps.append(m(lang, "gap_coords"))

        risks: list[str] = []
        if legume and zone["id"] == "sudan_savanna":
            risks.append(m(lang, "risk_sudan"))
        if legume:
            risks.append(m(lang, "risk_phosphorus"))
            risks.append(m(lang, "risk_striga"))
            risks.append(m(lang, "risk_seed"))
        for c, f in fits.items():
            if f["water_fit_2040s"] is not None and f["water_fit_2040s"] < 0.5:
                risks.append(m(lang, "risk_water", crop=label(c)))
        if heat > 0.1:
            risks.append(m(lang, "risk_heat"))
        if is_current and cereal_run >= 3:
            risks.append(m(lang, "risk_same_cereal"))

        return {
            "id": rid,
            "is_current": is_current,
            "sequence": sequence,
            "sequence_labels": [label(c) for c in sequence],
            "score": score,
            "why": why,
            "evidence": [{"id": k, "text": sources[k]} for k in evidence],
            "benefits": {
                "economics": econ,
                "striga_reduction_pct": [round(100 * striga[0]), round(100 * striga[1])],
                "climate": fits,
            },
            "information_gaps": gaps,
            "risks_for_local_review": risks,
        }

    current = memory["current"]["id"]
    current_seq = {"mixed_cereal_legume": ["maize", "cowpea"]}.get(current, ["maize", "maize"])
    cards = [card(f"current_{current}", current_seq, True)]
    cards += [card(r["id"], r["sequence"], False) for r in cfg["rotations"]]
    ranked = sorted(cards[1:], key=lambda c: -c["score"])
    best = ranked[0] if ranked else None
    return {
        "zone": zone,
        "season_confidence_mean": mean_conf,
        "options": [cards[0]] + ranked,
        "recommended": best["id"] if best else None,
        "prices_used": {
            "urea_ngn_per_bag": prices.urea_ngn_per_bag,
            "maize_ngn_per_bag": prices.maize_ngn_per_bag,
            "baseline_maize_t_ha": prices.baseline_maize_t_ha,
        },
        "disclaimer": m(lang, "disclaimer"),
    }
