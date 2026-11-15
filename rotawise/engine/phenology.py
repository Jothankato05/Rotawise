"""Field memory: classify each growing season from an NDVI time series.

The classifier is deliberately transparent. For each season it measures the
baseline, peak, amplitude, green-up date and length of the green period, then
applies thresholds from coefficients.yaml. It returns a class with a
confidence score, never a crop name, because 30 m pixels on small,
intercropped Nigerian plots cannot reliably separate individual crops.

Classes:
    cereal_like            long green period with a high peak (maize, sorghum, millet, rice)
    legume_or_short_cycle  shorter or lower green period (soybean, cowpea, groundnut, vegetables)
    bare_or_fallow         little or no green-up above the dry-season baseline
    unknown                too few cloud-free observations to decide
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from statistics import median
from typing import Any, Iterable

CLASSES = ("cereal_like", "legume_or_short_cycle", "bare_or_fallow", "unknown")


@dataclass(frozen=True)
class Season:
    year: int
    season_class: str
    confidence: float
    n_obs: int
    baseline: float | None
    peak: float | None
    amplitude: float | None
    greenup: str | None
    senescence: str | None
    length_days: int | None
    bare_months: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse(obs: Iterable[dict[str, Any]]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for o in obs:
        v = o.get("ndvi")
        if v is None:
            continue
        v = float(v)
        if not -0.2 <= v <= 1.0:  # discard physically impossible values
            continue
        out.append((date.fromisoformat(str(o["date"])[:10]), v))
    out.sort(key=lambda t: t[0])
    return out


def _smooth(values: list[float]) -> list[float]:
    """3-point rolling median: removes single cloud-contaminated dips/spikes."""
    if len(values) < 3:
        return list(values)
    out = [values[0]]
    for i in range(1, len(values) - 1):
        out.append(median(values[i - 1 : i + 2]))
    out.append(values[-1])
    return out


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def classify_season(
    year: int, series: list[tuple[date, float]], dry_baseline: float | None, cfg: dict[str, Any]
) -> Season:
    start_m, end_m = cfg["season_start_month"], cfg["season_end_month"]
    pts = [(d, v) for d, v in series if d.year == year and start_m <= d.month <= end_m]
    n = len(pts)
    if n < cfg["min_observations"]:
        return Season(year, "unknown", 0.0, n, None, None, None, None, None, None, [])

    dates = [d for d, _ in pts]
    vals = _smooth([v for _, v in pts])
    in_season_floor = min(vals)
    baseline = min(dry_baseline, in_season_floor) if dry_baseline is not None else in_season_floor
    peak = max(vals)
    amplitude = peak - baseline

    thr = baseline + cfg["green_threshold_fraction"] * amplitude
    green_idx = [i for i, v in enumerate(vals) if v >= thr]
    greenup = dates[green_idx[0]] if green_idx else None
    senescence = dates[green_idx[-1]] if green_idx else None
    length = (senescence - greenup).days if greenup and senescence else 0

    # Months in the season where the plot looked bare (below green threshold).
    green_months = {d.month for d, v in zip(dates, vals, strict=True) if v >= max(thr, cfg["bare_max_peak"])}
    bare_months = [m for m in range(start_m, end_m + 1) if m not in green_months]

    max_conf = cfg["max_confidence"]
    # Observation density factor: 12 or more clear observations = full weight.
    density = _clamp(n / 12.0, 0.3, 1.0)

    if amplitude < cfg["bare_max_amplitude"] or peak < cfg["bare_max_peak"]:
        cls = "bare_or_fallow"
        margin = max(
            (cfg["bare_max_amplitude"] - amplitude) / cfg["bare_max_amplitude"],
            (cfg["bare_max_peak"] - peak) / cfg["bare_max_peak"],
        )
    elif peak >= cfg["cereal_min_peak"] and length >= cfg["cereal_min_length_days"]:
        cls = "cereal_like"
        margin = min(
            (peak - cfg["cereal_min_peak"]) / 0.15,
            (length - cfg["cereal_min_length_days"]) / 45.0,
        )
    else:
        cls = "legume_or_short_cycle"
        gaps = []
        if peak < cfg["cereal_min_peak"]:
            gaps.append((cfg["cereal_min_peak"] - peak) / 0.15)
        if length < cfg["cereal_min_length_days"]:
            gaps.append((cfg["cereal_min_length_days"] - length) / 45.0)
        margin = max(gaps) if gaps else 0.0
        margin = min(margin, (amplitude - cfg["bare_max_amplitude"]) / 0.15)

    confidence = round(_clamp(0.4 + 0.45 * _clamp(margin), 0.0, max_conf) * density, 2)
    return Season(
        year=year,
        season_class=cls,
        confidence=confidence,
        n_obs=n,
        baseline=round(baseline, 3),
        peak=round(peak, 3),
        amplitude=round(amplitude, 3),
        greenup=greenup.isoformat() if greenup else None,
        senescence=senescence.isoformat() if senescence else None,
        length_days=length,
        bare_months=bare_months,
    )


def field_memory(ndvi_obs: Iterable[dict[str, Any]], cfg: dict[str, Any]) -> list[Season]:
    """Return one Season per year present in the observations, oldest first."""
    series = _parse(ndvi_obs)
    if not series:
        return []
    years = sorted({d.year for d, _ in series})
    seasons: list[Season] = []
    for y in years:
        dry = [v for d, v in series if d.year == y and d.month <= 3]
        dry_baseline = median(dry) if len(dry) >= 2 else None
        seasons.append(classify_season(y, series, dry_baseline, cfg))
    return seasons


def current_rotation_label(seasons: list[Season], lookback: int = 4) -> dict[str, Any]:
    """Describe what the farmer has been doing, from the last known seasons."""
    known = [s for s in seasons if s.season_class != "unknown"][-lookback:]
    if not known:
        return {"id": "unknown", "pattern": [], "cereal_run": 0}
    pattern = [s.season_class for s in known]
    run = 0
    for s in reversed(known):
        if s.season_class == "cereal_like":
            run += 1
        else:
            break
    if all(c == "cereal_like" for c in pattern):
        rid = "continuous_cereal"
    elif "legume_or_short_cycle" in pattern and "cereal_like" in pattern:
        rid = "mixed_cereal_legume"
    elif all(c == "bare_or_fallow" for c in pattern):
        rid = "fallow"
    else:
        rid = "irregular"
    return {"id": rid, "pattern": pattern, "cereal_run": run}
