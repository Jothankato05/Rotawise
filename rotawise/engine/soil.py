"""Soil fatigue score (0 = healthy, 100 = exhausted) with explained drivers."""

from __future__ import annotations

from itertools import combinations
from statistics import median
from typing import Any

from .phenology import Season


def theil_sen_slope(points: list[tuple[float, float]]) -> float | None:
    """Robust trend: median of pairwise slopes. Resistant to cloudy outlier years."""
    slopes = [
        (y2 - y1) / (x2 - x1) for (x1, y1), (x2, y2) in combinations(points, 2) if x2 != x1
    ]
    return median(slopes) if slopes else None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _deficit(value: float, low: float) -> float:
    """0 at 1.5x the 'low' threshold or above, 0.5 at the threshold, 1 at half of it."""
    return _clamp01((1.5 * low - value) / low)


def fatigue_score(
    seasons: list[Season], soil: dict[str, Any] | None, cereal_run: int, cfg: dict[str, Any]
) -> dict[str, Any]:
    s_cfg = cfg["soil"]
    w = s_cfg["fatigue_weights"]
    drivers: list[dict[str, Any]] = []
    gaps: list[str] = []
    total_w = 0.0
    score = 0.0

    # 1. Consecutive cereal seasons: 4 or more in a row = maximum pressure.
    run_part = _clamp01(cereal_run / 4.0)
    score += w["cereal_run"] * run_part
    total_w += w["cereal_run"]
    drivers.append({
        "id": "cereal_run",
        "value": cereal_run,
        "contribution": round(100 * w["cereal_run"] * run_part, 1),
        "text": f"{cereal_run} cereal-like season(s) in a row on this plot",
    })

    # 2. Productivity trend: peak NDVI across cropped seasons.
    pts = [
        (float(s.year), float(s.peak))
        for s in seasons
        if s.season_class in ("cereal_like", "legume_or_short_cycle") and s.peak is not None
    ]
    slope = theil_sen_slope(pts) if len(pts) >= 4 else None
    if slope is not None:
        # A loss of 0.02 NDVI per year or worse counts as full pressure.
        trend_part = _clamp01(-slope / 0.02)
        score += w["productivity_trend"] * trend_part
        total_w += w["productivity_trend"]
        start_peak = median(p for _, p in pts[:3])
        pct = 100 * slope * (pts[-1][0] - pts[0][0]) / start_peak if start_peak else 0.0
        drivers.append({
            "id": "productivity_trend",
            "value": round(slope, 4),
            "contribution": round(100 * w["productivity_trend"] * trend_part, 1),
            "text": f"Peak greenness changed by about {pct:+.0f}% over {len(pts)} cropped seasons",
        })
    else:
        gaps.append("Fewer than 4 cropped seasons with clear imagery, so no productivity trend.")

    # 3-5. iSDAsoil properties.
    if soil:
        oc = soil.get("organic_carbon_g_kg")
        if oc is not None:
            part = _deficit(oc, s_cfg["organic_carbon_low_g_kg"])
            score += w["organic_carbon"] * part
            total_w += w["organic_carbon"]
            drivers.append({
                "id": "organic_carbon", "value": round(oc, 2),
                "contribution": round(100 * w["organic_carbon"] * part, 1),
                "text": f"Soil organic carbon {oc:.1f} g/kg (low below {s_cfg['organic_carbon_low_g_kg']:.0f})",
            })
        n = soil.get("nitrogen_total_g_kg")
        if n is not None:
            part = _deficit(n, s_cfg["nitrogen_total_low_g_kg"])
            score += w["nitrogen"] * part
            total_w += w["nitrogen"]
            drivers.append({
                "id": "nitrogen", "value": round(n, 2),
                "contribution": round(100 * w["nitrogen"] * part, 1),
                "text": f"Total nitrogen {n:.2f} g/kg (low below {s_cfg['nitrogen_total_low_g_kg']:.1f})",
            })
        ph = soil.get("ph")
        if ph is not None:
            lo, hi = s_cfg["ph_ok_range"]
            dist = lo - ph if ph < lo else (ph - hi if ph > hi else 0.0)
            part = _clamp01(dist / 1.0)
            score += w["ph"] * part
            total_w += w["ph"]
            drivers.append({
                "id": "ph", "value": round(ph, 2),
                "contribution": round(100 * w["ph"] * part, 1),
                "text": f"Soil pH {ph:.1f} (comfortable range {lo} to {hi})",
            })
    else:
        gaps.append("No soil data for this plot yet.")

    value = round(100 * score / total_w) if total_w else None
    level = None
    if value is not None:
        level = "high" if value >= 60 else "moderate" if value >= 35 else "low"
    return {
        "score": value,
        "level": level,
        "drivers": sorted(drivers, key=lambda d: -d["contribution"]),
        "information_gaps": gaps,
        "weights_used": round(total_w, 2),
    }
