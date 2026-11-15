"""Extract NASA (and partner) data for the pilot plots without Earth Engine.

Sources, all open and keyless:
    ESA WorldCover 2021 (Planetary Computer)   choose a real cropland point in each LGA
    NASA HLS v2 L30 + S30 (Planetary Computer) plot NDVI time series, 2016-2025
    NASA POWER daily API                       rain onset, dry spells, heat days, season rain
    NASA NEX-GDDP-CMIP6 (NCCS THREDDS)         season rain and hot days, 1995-2014 vs 2040s
    ISRIC SoilGrids 2.0                        soil organic carbon, total nitrogen, pH (0-30 cm)

Usage:  python -m pipeline.pc_extract [--plot 101] [--workers 16]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import io
import json
import logging
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import planetary_computer
import pystac_client
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

from . import power

log = logging.getLogger("rotawise.pc")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
THREDDS = "https://ds.nccs.nasa.gov/thredds"
FMASK_BAD = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)  # cloud, adjacent, shadow, snow, water
HEAT_C = 35.0
GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "1",
    "VSI_CACHE": "TRUE",
}


def catalog():
    return pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)


def retry(fn, what, attempts=5):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if i == attempts - 1:
                raise
            wait = 2 ** i
            log.warning("%s failed (%s), retry in %ss", what, exc, wait)
            time.sleep(wait)


# ---------------------------------------------------------------- cropland point
def find_cropland(cat, lat: float, lon: float, radius_km: float = 10.0) -> dict:
    items = list(cat.search(collections=["esa-worldcover"], intersects={"type": "Point", "coordinates": [lon, lat]}).items())
    item = sorted(items, key=lambda i: i.datetime or datetime.min.replace(tzinfo=timezone.utc))[-1]
    with rasterio.Env(**GDAL_ENV), rasterio.open(item.assets["map"].href) as ds:
        row, col = ds.index(lon, lat)
        r = int(radius_km * 1000 / 10)
        win = Window(col - r, row - r, 2 * r, 2 * r)
        arr = ds.read(1, window=win, boundless=True, fill_value=0)
        tf = ds.window_transform(win)
    best = None
    step, half = 20, 6  # 200 m grid; 13x13 px block = 130 m
    for i in range(half, arr.shape[0] - half, step):
        for j in range(half, arr.shape[1] - half, step):
            block = arr[i - half : i + half + 1, j - half : j + half + 1]
            frac = float((block == 40).mean())
            if frac < 0.95:
                continue
            d = math.hypot(i - r, j - r)
            if best is None or d < best[0]:
                best = (d, i, j, frac)
    if best is None:
        raise RuntimeError(f"no cropland block within {radius_km} km of {lat},{lon}")
    _, i, j, frac = best
    x, y = rasterio.transform.xy(tf, i, j)
    return {"lat": round(y, 5), "lon": round(x, 5), "cropland_fraction": round(frac, 3), "distance_km": round(best[0] * 10 / 1000, 2),
            "worldcover_item": item.id}


# ---------------------------------------------------------------- HLS NDVI
HLS = {"hls2-l30": "B05", "hls2-s30": "B8A"}


def _sample(item, nir_key: str, lon: float, lat: float) -> dict | None:
    def read():
        with rasterio.Env(**GDAL_ENV):
            with rasterio.open(item.assets["Fmask"].href) as fm:
                x, y = Transformer.from_crs("EPSG:4326", fm.crs, always_xy=True).transform(lon, lat)
                row, col = fm.index(x, y)
                win = Window(col - 1, row - 1, 3, 3)
                mask = fm.read(1, window=win, boundless=True, fill_value=255)
            with rasterio.open(item.assets["B04"].href) as rd:
                red = rd.read(1, window=win, boundless=True, fill_value=-9999).astype("float64")
            with rasterio.open(item.assets[nir_key].href) as nr:
                nir = nr.read(1, window=win, boundless=True, fill_value=-9999).astype("float64")
        return mask, red, nir

    mask, red, nir = retry(read, f"HLS {item.id}")
    ok = ((mask.astype("int64") & FMASK_BAD) == 0) & (mask != 255) & (red > 0) & (nir > 0)
    if ok.sum() < 3:
        return None
    ndvi = (nir[ok] - red[ok]) / (nir[ok] + red[ok])
    v = float(np.mean(ndvi))
    if not -0.2 <= v <= 1.0:
        return None
    return {"date": item.datetime.strftime("%Y-%m-%d"), "ndvi": round(v, 4), "sensor": item.collection_id, "clear_px": int(ok.sum())}


def hls_ndvi(cat, lat: float, lon: float, workers: int) -> list[dict]:
    jobs = []
    for coll, nir in HLS.items():
        items = list(cat.search(
            collections=[coll], intersects={"type": "Point", "coordinates": [lon, lat]},
            datetime="2016-01-01/2025-12-31", query={"eo:cloud_cover": {"lt": 85}},
        ).items())
        log.info("  %s: %d scenes", coll, len(items))
        jobs += [(it, nir) for it in items]
    out = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for res in ex.map(lambda j: _safe(_sample, j[0], j[1], lon, lat), jobs):
            if res:
                out.append(res)
    out.sort(key=lambda o: o["date"])
    return out


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as exc:  # noqa: BLE001
        log.warning("skip: %s", exc)
        return None


# ---------------------------------------------------------------- SoilGrids
def soilgrids(lat: float, lon: float) -> dict:
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = [("lon", lon), ("lat", lat), ("value", "mean")] + [("property", p) for p in ("soc", "nitrogen", "phh2o")] + \
             [("depth", d) for d in ("0-5cm", "5-15cm", "15-30cm")]

    def call():
        r = httpx.get(url, params=params, timeout=90)
        r.raise_for_status()
        return r.json()

    js = retry(call, "SoilGrids", attempts=6)
    w = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    out = {}
    for layer in js["properties"]["layers"]:
        f = layer["unit_measure"]["d_factor"]
        vals = [(w[d["label"]], d["values"]["mean"]) for d in layer["depths"] if d["values"]["mean"] is not None]
        if not vals:
            continue
        mean = sum(a * b for a, b in vals) / sum(a for a, _ in vals) / f
        out[layer["name"]] = mean
    return {
        "organic_carbon_g_kg": round(out["soc"], 2) if "soc" in out else None,
        "nitrogen_total_g_kg": round(out["nitrogen"], 3) if "nitrogen" in out else None,
        "ph": round(out["phh2o"], 2) if "phh2o" in out else None,
        "phosphorus_ppm": None,
        "depth": "0-30 cm, depth-weighted",
    }


# ---------------------------------------------------------------- CMIP6 (NCCS THREDDS)
MODELS = ["ACCESS-CM2", "MRI-ESM2-0"]
PERIODS = {"historical": ("historical", [1996, 2000, 2005, 2010, 2014]),
           "ssp245_2040s": ("ssp245", [2041, 2043, 2045, 2047, 2049]),
           "ssp585_2040s": ("ssp585", [2041, 2043, 2045, 2047, 2049])}
_cat_cache: dict = {}


def _files(model: str, scen: str, var: str) -> dict[int, str]:
    key = (model, scen, var)
    if key not in _cat_cache:
        url = f"{THREDDS}/catalog/AMES/NEX/GDDP-CMIP6/{model}/{scen}/r1i1p1f1/{var}/catalog.xml"
        xml = retry(lambda: httpx.get(url, timeout=60).text, f"catalog {key}")
        names = re.findall(r'name="(' + var + r'_day_[^"]+\.nc)"', xml)
        files: dict[int, str] = {}
        for n in sorted(names):  # later versions sort last and win
            m = re.search(r"_(\d{4})(?:_v[\d.]+)?\.nc$", n)
            if m:
                files[int(m.group(1))] = n
        if not files:
            raise RuntimeError(f"empty THREDDS catalog for {key}")
        _cat_cache[key] = files
    return _cat_cache[key]


def _season(model: str, scen: str, var: str, year: int, lat: float, lon: float) -> list[float]:
    name = _files(model, scen, var)[year]
    url = (f"{THREDDS}/ncss/grid/AMES/NEX/GDDP-CMIP6/{model}/{scen}/r1i1p1f1/{var}/{name}"
           f"?var={var}&latitude={lat}&longitude={lon}&time_start={year}-05-01&time_end={year}-10-31&accept=csv")
    txt = retry(lambda: httpx.get(url, timeout=120).raise_for_status().text, f"NCSS {model} {scen} {var} {year}")
    rows = list(csv.reader(io.StringIO(txt)))
    return [float(r[-1]) for r in rows[1:] if r and r[-1] not in ("", "NaN")]


def cmip6(lat: float, lon: float, workers: int) -> dict:
    tasks = [(m, k, s, y, v) for m in MODELS for k, (s, ys) in PERIODS.items() for y in ys for v in ("pr", "tasmax")]
    for m in MODELS:  # fill the catalog cache sequentially to avoid racing threads
        for _, (s, _) in PERIODS.items():
            for v in ("pr", "tasmax"):
                _files(m, s, v)
    with cf.ThreadPoolExecutor(min(workers, 8)) as ex:
        res = list(ex.map(lambda t: (t, _safe(_season, t[0], t[2], t[4], t[3], lat, lon)), tasks))
    out: dict = {"models": MODELS, "source": "NASA NEX-GDDP-CMIP6 via NCCS THREDDS, May to October"}
    for k in PERIODS:
        rains, heats = [], []
        for m in MODELS:
            pr = [v for (t, v) in res if t[0] == m and t[1] == k and t[4] == "pr" and v]
            tx = [v for (t, v) in res if t[0] == m and t[1] == k and t[4] == "tasmax" and v]
            if pr:
                rains.append(sum(sum(x) * 86400 for x in pr) / len(pr))
            if tx:
                heats.append(sum(sum(1 for t in x if t > 273.15 + HEAT_C) for x in tx) / len(tx))
        if rains:
            out[k] = {"season_rain_mm": round(sum(rains) / len(rains), 1),
                      "heat_days": round(sum(heats) / len(heats), 1) if heats else None}
    return out


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    index = json.loads((DATA / "plots.json").read_text())
    cat = catalog()
    for p in index["plots"]:
        if args.plot and p["id"] != args.plot:
            continue
        log.info("[%s] %s: finding cropland", p["id"], p["lga"])
        crop = find_cropland(cat, p.get("lga_lat", p["lat"]), p.get("lga_lon", p["lon"]))
        p.setdefault("lga_lat", p["lat"])
        p.setdefault("lga_lon", p["lon"])
        p.update(lat=crop["lat"], lon=crop["lon"], coords_verified=True,
                 coords_source=f"ESA WorldCover 2021 cropland block ({crop['cropland_fraction']:.0%} cropland), {crop['distance_km']} km from the LGA reference point")
        lat, lon = crop["lat"], crop["lon"]
        out = {"plot_id": p["id"], "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "coords": {"lat": lat, "lon": lon}, "cropland_check": crop, "sources": {}, "climate": {}}

        log.info("[%s] HLS NDVI at %s,%s", p["id"], lat, lon)
        out["ndvi"] = hls_ndvi(cat, lat, lon, args.workers)
        out["sources"]["ndvi"] = "NASA HLS v2 HLSL30 + HLSS30 via Microsoft Planetary Computer; Fmask cloud-masked 3x3 pixel mean NDVI"
        log.info("[%s] %d clear NDVI observations", p["id"], len(out["ndvi"]))

        log.info("[%s] NASA POWER", p["id"])
        params = power.fetch_daily(lat, lon, 2016, 2025)
        out["climate"]["observed"] = power.seasonal_summary(params, 2016, 2025, HEAT_C)
        out["sources"]["climate_observed"] = "NASA POWER daily agroclimatology (PRECTOTCORR, T2M_MAX)"

        log.info("[%s] CMIP6", p["id"])
        out["climate"]["cmip6"] = cmip6(lat, lon, args.workers)
        out["sources"]["projections"] = "NASA NEX-GDDP-CMIP6 (ACCESS-CM2, MRI-ESM2-0; 5 sample years per period)"

        log.info("[%s] SoilGrids", p["id"])
        out["soil"] = _safe(soilgrids, lat, lon)
        out["sources"]["soil"] = "ISRIC SoilGrids 2.0 (CC BY 4.0), 0-30 cm depth-weighted mean"
        out["sources"]["cropland"] = "ESA WorldCover 2021 v200 via Microsoft Planetary Computer (CC BY 4.0)"

        (DATA / "plots").mkdir(exist_ok=True)
        (DATA / "plots" / f"{p['id']}.json").write_text(json.dumps(out, indent=1))
        (DATA / "plots.json").write_text(json.dumps(index, indent=2))
        log.info("[%s] done", p["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
