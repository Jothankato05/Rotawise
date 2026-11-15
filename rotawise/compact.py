"""Parse the compact plot format written by pipeline.compact.pack."""

from __future__ import annotations

from datetime import date, timedelta


def _num(x: str):
    if x in ("None", ""):
        return None
    f = float(x)
    return int(f) if f.is_integer() and "." not in x else f


def parse(text: str) -> list[dict]:
    """Rebuild plot observation dicts from packed text."""
    plots: list[dict] = []
    cur: dict | None = None
    for line in text.strip().splitlines():
        f = line.strip().split("|")
        if f[0] == "P":
            cur = {"plot_id": f[1], "extracted_at": f[6], "coords": {"lat": float(f[2]), "lon": float(f[3])},
                   "cropland_check": {"lat": float(f[2]), "lon": float(f[3]), "cropland_fraction": float(f[4]), "distance_km": float(f[5])},
                   "ndvi": [], "climate": {"observed": [], "cmip6": {"models": ["ACCESS-CM2", "MRI-ESM2-0"]}}, "soil": None}
            plots.append(cur)
        elif f[0] == "N":
            y = int(f[1])
            for item in f[2].split(","):
                b, v, n = item.split(":")
                d = date(y, 1, 1) + timedelta(days=int(b) * 16 + 7)
                if d.year == y:
                    cur["ndvi"].append({"date": d.isoformat(), "ndvi": int(v) / 1000, "n_scenes": int(n), "composite": "16-day median"})
        elif f[0] == "C":
            cur["climate"]["observed"].append({"year": int(f[1]), "season_rain_mm": _num(f[2]), "onset_doy": _num(f[3]),
                                               "max_dry_spell_days": _num(f[4]), "heat_days": _num(f[5])})
        elif f[0] == "M":
            cur["climate"]["cmip6"][f[1]] = {"season_rain_mm": float(f[2]), "heat_days": _num(f[3])}
        elif f[0] == "S":
            cur["soil"] = {"organic_carbon_g_kg": _num(f[1]), "nitrogen_total_g_kg": _num(f[2]), "ph": _num(f[3]),
                           "phosphorus_ppm": None, "depth": "0-30 cm, depth-weighted"}
        elif f[0] == "X":
            cur["n_raw_observations"] = int(f[1])
            cur["sources"] = {
                "ndvi": (f"NASA HLS v2 HLSL30 + HLSS30 via Microsoft Planetary Computer; Fmask cloud-masked 3x3 pixel NDVI, "
                         f"{f[1]} clear observations, stored as 16-day median composites"),
                "climate_observed": "NASA POWER daily agroclimatology (PRECTOTCORR, T2M_MAX)",
                "projections": f[2],
                "soil": "ISRIC SoilGrids 2.0 (CC BY 4.0), 0-30 cm depth-weighted mean",
                "cropland": "ESA WorldCover 10 m via Microsoft Planetary Computer (CC BY 4.0)",
            }
    return plots
