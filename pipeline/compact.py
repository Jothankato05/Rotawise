"""Pack extracted plot files into a compact text form and back.

pack:   python -m pipeline.compact pack data/plots/*.json > plots.txt
unpack: python -m pipeline.compact unpack plots.txt data/plots

NDVI is reduced to 16-day median composites (values x1000); everything
else is kept as is. Used to move pipeline output between machines.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import median


def pack(paths: list[str]) -> str:
    out = []
    for p in paths:
        d = json.loads(Path(p).read_text())
        c = d["cropland_check"]
        out.append(f"P|{d['plot_id']}|{c['lat']}|{c['lon']}|{c['cropland_fraction']}|{c['distance_km']}|{d['extracted_at']}")
        bins: dict[tuple[int, int], list[float]] = {}
        for o in d["ndvi"]:
            dt = date.fromisoformat(o["date"])
            bins.setdefault((dt.year, (dt.timetuple().tm_yday - 1) // 16), []).append(o["ndvi"])
        years = sorted({y for y, _ in bins})
        for y in years:
            vals = ",".join(f"{b}:{round(median(v) * 1000)}:{len(v)}" for (yy, b), v in sorted(bins.items()) if yy == y)
            out.append(f"N|{y}|{vals}")
        for o in d["climate"].get("observed", []):
            out.append(f"C|{o['year']}|{o['season_rain_mm']}|{o['onset_doy']}|{o['max_dry_spell_days']}|{o['heat_days']}")
        cm = d["climate"].get("cmip6", {})
        for k in ("historical", "ssp245_2040s", "ssp585_2040s"):
            if k in cm:
                out.append(f"M|{k}|{cm[k]['season_rain_mm']}|{cm[k]['heat_days']}")
        s = d.get("soil") or {}
        out.append(f"S|{s.get('organic_carbon_g_kg')}|{s.get('nitrogen_total_g_kg')}|{s.get('ph')}")
        out.append(f"X|{len(d['ndvi'])}|{d['sources'].get('projections', '')}")
    return "\n".join(out)


def _num(x: str):
    if x in ("None", ""):
        return None
    f = float(x)
    return int(f) if f.is_integer() and "." not in x else f


def unpack(text: str, outdir: Path) -> list[str]:
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
                "ndvi": f"NASA HLS v2 HLSL30 + HLSS30 via Microsoft Planetary Computer; Fmask cloud-masked 3x3 pixel NDVI, {f[1]} clear observations, stored as 16-day median composites",
                "climate_observed": "NASA POWER daily agroclimatology (PRECTOTCORR, T2M_MAX)",
                "projections": f[2],
                "soil": "ISRIC SoilGrids 2.0 (CC BY 4.0), 0-30 cm depth-weighted mean",
                "cropland": "ESA WorldCover 10 m via Microsoft Planetary Computer (CC BY 4.0)",
            }
    written = []
    outdir.mkdir(parents=True, exist_ok=True)
    for p in plots:
        path = outdir / f"{p['plot_id']}.json"
        path.write_text(json.dumps(p, indent=1))
        written.append(str(path))
    return written


if __name__ == "__main__":
    if sys.argv[1] == "pack":
        print(pack(sys.argv[2:]))
    else:
        print("\n".join(unpack(Path(sys.argv[2]).read_text(), Path(sys.argv[3]))))
