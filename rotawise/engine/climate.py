"""Climate context for a plot: observed seasons and projected change.

Projection uses the delta method: the observed (NASA GPM IMERG / NASA POWER)
seasonal climate is shifted by the change NEX-GDDP-CMIP6 models project
between the historical baseline (1995-2014) and the 2040s.
"""

from __future__ import annotations

from statistics import median, pstdev
from typing import Any


def _med(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return median(vals) if vals else None


def summarize(climate: dict[str, Any] | None) -> dict[str, Any]:
    if not climate:
        return {"available": False}

    observed = climate.get("observed") or []
    imerg = climate.get("imerg_season_rain_mm") or []
    rain_series = [r["mm"] for r in imerg if r.get("mm") is not None] or [
        o["season_rain_mm"] for o in observed if o.get("season_rain_mm") is not None
    ]
    rain_med = _med(rain_series)
    rain_cv = (pstdev(rain_series) / rain_med) if rain_med and len(rain_series) > 2 else None
    onset = _med([o.get("onset_doy") for o in observed])
    dry_spell = _med([o.get("max_dry_spell_days") for o in observed])
    heat = _med([o.get("heat_days") for o in observed])

    out: dict[str, Any] = {
        "available": rain_med is not None,
        "rain_source": "NASA GPM IMERG" if imerg else "NASA POWER",
        "observed": {
            "season_rain_mm_median": round(rain_med) if rain_med is not None else None,
            "season_rain_cv": round(rain_cv, 2) if rain_cv is not None else None,
            "onset_doy_median": round(onset) if onset is not None else None,
            "max_dry_spell_days_median": round(dry_spell) if dry_spell is not None else None,
            "heat_days_median": round(heat) if heat is not None else None,
            "years": len(rain_series),
        },
        "series": [{"year": r.get("year"), "mm": r.get("mm")} for r in imerg]
        or [{"year": o.get("year"), "mm": o.get("season_rain_mm")} for o in observed],
        "projections": {},
    }

    cmip = climate.get("cmip6") or {}
    hist = cmip.get("historical")
    for key in ("ssp245_2040s", "ssp585_2040s"):
        fut = cmip.get(key)
        if not (hist and fut and rain_med is not None):
            continue
        ratio = (fut["season_rain_mm"] / hist["season_rain_mm"]) if hist.get("season_rain_mm") else 1.0
        heat_delta = (fut.get("heat_days") or 0) - (hist.get("heat_days") or 0)
        out["projections"][key] = {
            "season_rain_mm": round(rain_med * ratio),
            "rain_change_pct": round(100 * (ratio - 1), 1),
            "heat_days": round((heat or 0) + heat_delta),
            "heat_days_change": round(heat_delta, 1),
            "models": cmip.get("models", []),
        }
    return out


def water_fit(rain_mm: float | None, need: list[float], deficit_frac: float) -> float | None:
    """1.0 when expected rain covers the upper need, 0.0 well below the minimum."""
    if rain_mm is None:
        return None
    lo, hi = need
    floor = lo * deficit_frac
    if rain_mm >= hi:
        return 1.0
    if rain_mm <= floor:
        return 0.0
    return round((rain_mm - floor) / (hi - floor), 2)
