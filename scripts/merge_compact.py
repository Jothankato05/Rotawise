"""Unpack compact pipeline output into data/plots and update data/plots.json coordinates."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.compact import unpack  # noqa: E402

root = Path(__file__).resolve().parent.parent
index_path = root / "data" / "plots.json"
index = json.loads(index_path.read_text())
for txt in sys.argv[1:]:
    for path in unpack(Path(txt).read_text(), root / "data" / "plots"):
        d = json.loads(Path(path).read_text())
        c = d["cropland_check"]
        for p in index["plots"]:
            if p["id"] == d["plot_id"]:
                p.setdefault("lga_lat", p["lat"])
                p.setdefault("lga_lon", p["lon"])
                p.update(lat=c["lat"], lon=c["lon"], coords_verified=True,
                         coords_source=f"ESA WorldCover cropland block ({c['cropland_fraction']:.0%} cropland), {c['distance_km']} km from the LGA reference point")
        print("merged", path)
index["_note"] = "Pilot plots. Each point is a cropland block found automatically on ESA WorldCover 10 m near the LGA reference point (lga_lat, lga_lon)."
index_path.write_text(json.dumps(index, indent=2) + "\n")
