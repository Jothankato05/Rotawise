"""NASA POWER daily agroclimatology for a point, summarized per growing season.

API docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
No API key needed. Parameters:
    PRECTOTCORR  bias-corrected precipitation (mm/day)
    T2M_MAX      daily maximum 2 m air temperature (deg C)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from .retry import with_retry

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL = -999.0


def fetch_daily(lat: float, lon: float, start_year: int, end_year: int) -> dict[str, dict[str, float]]:
    params = {
        "parameters": "PRECTOTCORR,T2M_MAX",
        "community": "AG",
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
    }

    def call() -> dict[str, Any]:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            r = client.get(POWER_URL, params=params)
            r.raise_for_status()
            return r.json()

    payload = with_retry(call, what=f"NASA POWER {lat},{lon}")
    return payload["properties"]["parameter"]


def _daily_series(param: dict[str, float], year: int, m0: int, m1: int) -> list[tuple[date, float | None]]:
    out = []
    d = date(year, m0, 1)
    end = date(year, m1 + 1, 1) - timedelta(days=1) if m1 < 12 else date(year, 12, 31)
    while d <= end:
        v = param.get(d.strftime("%Y%m%d"))
        out.append((d, None if v is None or v <= FILL else float(v)))
        d += timedelta(days=1)
    return out


def onset_doy(rain: list[tuple[date, float | None]]) -> int | None:
    """Agronomic onset: first day from April with >= 20 mm over 3 days and no
    dry spell longer than 7 days in the following 30 days."""
    vals = [v or 0.0 for _, v in rain]
    for i in range(len(vals) - 32):
        if sum(vals[i : i + 3]) >= 20.0:
            run = longest = 0
            for v in vals[i + 3 : i + 33]:
                run = run + 1 if v < 1.0 else 0
                longest = max(longest, run)
            if longest <= 7:
                return rain[i][0].timetuple().tm_yday
    return None


def max_dry_spell(rain: list[tuple[date, float | None]], start_doy: int | None) -> int | None:
    if start_doy is None:
        return None
    run = longest = 0
    for d, v in rain:
        if d.timetuple().tm_yday < start_doy or d.month > 9:
            continue
        run = run + 1 if (v or 0.0) < 1.0 else 0
        longest = max(longest, run)
    return longest


def seasonal_summary(params: dict[str, dict[str, float]], start_year: int, end_year: int, heat_c: float) -> list[dict[str, Any]]:
    pr, tx = params["PRECTOTCORR"], params["T2M_MAX"]
    out = []
    for y in range(start_year, end_year + 1):
        rain_season = _daily_series(pr, y, 4, 10)
        if sum(1 for _, v in rain_season if v is not None) < 150:
            continue  # incomplete year (e.g. current year)
        season_total = sum(v for d, v in rain_season if v is not None and d.month >= 5)
        o = onset_doy(rain_season)
        temps = _daily_series(tx, y, 5, 10)
        out.append({
            "year": y,
            "season_rain_mm": round(season_total, 1),
            "onset_doy": o,
            "max_dry_spell_days": max_dry_spell(rain_season, o),
            "heat_days": sum(1 for _, v in temps if v is not None and v > heat_c),
        })
    return out
