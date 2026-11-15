"""Pack extracted plot files into a compact text form and back.

pack:   python -m pipeline.compact pack data/plots/*.json > plots.txt
unpack: python -m pipeline.compact unpack plots.txt data/plots

NDVI is reduced to 16-day median composites (values x1000); everything
else is kept as is. Used to move pipeline output between machines.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from statistics import median

from rotawise.compact import parse


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


def unpack(text: str, outdir: Path) -> list[str]:
    written = []
    outdir.mkdir(parents=True, exist_ok=True)
    for p in parse(text):
        path = outdir / f"{p['plot_id']}.json"
        path.write_text(json.dumps(p, indent=1))
        written.append(str(path))
    return written


if __name__ == "__main__":
    if sys.argv[1] == "pack":
        print(pack(sys.argv[2:]))
    else:
        print("\n".join(unpack(Path(sys.argv[2]).read_text(), Path(sys.argv[3]))))
