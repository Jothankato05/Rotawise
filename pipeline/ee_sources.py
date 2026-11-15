"""Google Earth Engine extraction of NASA and partner datasets for one point.

Requires: pip install earthengine-api, then `earthengine authenticate` and a
Google Cloud project registered for Earth Engine (non-commercial is free).

Dataset IDs used (verify in the Earth Engine catalog if a call fails):
    NASA/HLS/HLSL30/v002          HLS Landsat 30 m        bands B4 (red), B5 (NIR), Fmask
    NASA/HLS/HLSS30/v002          HLS Sentinel-2 30 m     bands B4 (red), B8A (NIR), Fmask
    MODIS/061/MOD13Q1             MODIS 16-day NDVI 250 m
    NASA/GPM_L3/IMERG_MONTHLY_V07 GPM IMERG monthly precipitation
    NASA/GDDP-CMIP6               NEX-GDDP-CMIP6 daily downscaled projections
    ISDASOIL/Africa/v1/*          iSDAsoil 30 m soil properties (0-20 cm)
    USGS/SRTMGL1_003              SRTM 30 m elevation
"""

from __future__ import annotations

import math
from typing import Any

import ee

from .retry import with_retry

HLS_COLLECTIONS = {
    "HLSL30": ("NASA/HLS/HLSL30/v002", "B5"),
    "HLSS30": ("NASA/HLS/HLSS30/v002", "B8A"),
}
# Fmask bits: 1 cloud, 2 adjacent to cloud/shadow, 3 cloud shadow, 4 snow/ice, 5 water.
FMASK_BAD_BITS = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)
CMIP6_MODELS = ["ACCESS-CM2", "MRI-ESM2-0", "MIROC6"]


def init(project: str) -> None:
    ee.Initialize(project=project)


def _region(lat: float, lon: float, radius_m: float) -> ee.Geometry:
    return ee.Geometry.Point([lon, lat]).buffer(radius_m)


def _getinfo(obj: Any, what: str) -> Any:
    return with_retry(obj.getInfo, what=what)


def hls_ndvi(lat: float, lon: float, start: str, end: str, radius_m: float = 45.0) -> list[dict[str, Any]]:
    """Plot-mean NDVI per clear HLS acquisition. 45 m radius ~ 0.6 ha."""
    region = _region(lat, lon, radius_m)
    out: list[dict[str, Any]] = []
    for sensor, (cid, nir) in HLS_COLLECTIONS.items():
        def to_feature(img: ee.Image, nir: str = nir, sensor: str = sensor) -> ee.Feature:
            clear = img.select("Fmask").bitwiseAnd(FMASK_BAD_BITS).eq(0)
            ndvi = img.normalizedDifference([nir, "B4"]).rename("ndvi").updateMask(clear)
            stats = ndvi.reduceRegion(ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), region, 30)
            return ee.Feature(None, {
                "date": img.date().format("YYYY-MM-dd"),
                "ndvi": stats.get("ndvi_mean"),
                "clear_px": stats.get("ndvi_count"),
                "sensor": sensor,
            })

        fc = (
            ee.ImageCollection(cid)
            .filterBounds(region)
            .filterDate(start, end)
            .map(to_feature)
            .filter(ee.Filter.notNull(["ndvi"]))
            .filter(ee.Filter.gte("clear_px", 3))
        )
        feats = _getinfo(fc, f"HLS {sensor} NDVI")["features"]
        out += [f["properties"] for f in feats]
    out.sort(key=lambda o: o["date"])
    return [{"date": o["date"], "ndvi": round(o["ndvi"], 4), "sensor": o["sensor"]} for o in out]


def modis_ndvi(lat: float, lon: float, start: str, end: str) -> list[dict[str, Any]]:
    pt = ee.Geometry.Point([lon, lat])

    def to_feature(img: ee.Image) -> ee.Feature:
        good = img.select("SummaryQA").lte(1)
        v = img.select("NDVI").multiply(0.0001).updateMask(good)
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "ndvi": v.reduceRegion(ee.Reducer.first(), pt, 250).get("NDVI"),
        })

    fc = ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(start, end).map(to_feature).filter(ee.Filter.notNull(["ndvi"]))
    feats = _getinfo(fc, "MODIS NDVI")["features"]
    return [{"date": f["properties"]["date"], "ndvi": round(f["properties"]["ndvi"], 4)} for f in feats]


def imerg_season_rain(lat: float, lon: float, start_year: int, end_year: int) -> list[dict[str, Any]]:
    """May to October rainfall total per year from IMERG monthly (rate mm/hr x hours)."""
    pt = ee.Geometry.Point([lon, lat])
    col = ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V07")

    def to_feature(img: ee.Image) -> ee.Feature:
        d = img.date()
        hours = d.advance(1, "month").difference(d, "hour")
        mm = img.select("precipitation").multiply(hours)
        return ee.Feature(None, {
            "year": d.get("year"),
            "month": d.get("month"),
            "mm": mm.reduceRegion(ee.Reducer.first(), pt, 11132).get("precipitation"),
        })

    fc = col.filterDate(f"{start_year}-01-01", f"{end_year + 1}-01-01").filter(ee.Filter.calendarRange(5, 10, "month")).map(to_feature)
    rows = [f["properties"] for f in _getinfo(fc, "IMERG monthly")["features"] if f["properties"].get("mm") is not None]
    totals: dict[int, list[float]] = {}
    for r in rows:
        totals.setdefault(int(r["year"]), []).append(float(r["mm"]))
    return [{"year": y, "mm": round(sum(v), 1)} for y, v in sorted(totals.items()) if len(v) == 6]


def isda_soil(lat: float, lon: float) -> dict[str, float | None]:
    """iSDAsoil 0-20 cm, back-transformed to physical units (see iSDA docs)."""
    pt = ee.Geometry.Point([lon, lat])
    layers = {
        "nitrogen_total": ("nitrogen_total_g_kg", lambda x: math.exp(x / 100) - 1),
        "carbon_organic": ("organic_carbon_g_kg", lambda x: math.exp(x / 10) - 1),
        "phosphorus_extractable": ("phosphorus_ppm", lambda x: math.exp(x / 10) - 1),
        "ph": ("ph", lambda x: x / 10),
    }
    out: dict[str, float | None] = {}
    for layer, (key, fn) in layers.items():
        img = ee.Image(f"ISDASOIL/Africa/v1/{layer}").select("mean_0_20")
        raw = _getinfo(img.reduceRegion(ee.Reducer.first(), pt, 30).get("mean_0_20"), f"iSDAsoil {layer}")
        out[key] = round(fn(raw), 3) if raw is not None else None
    return out


def srtm_slope(lat: float, lon: float) -> dict[str, float | None]:
    pt = ee.Geometry.Point([lon, lat])
    dem = ee.Image("USGS/SRTMGL1_003")
    vals = _getinfo(
        ee.Image.cat(dem.rename("elev"), ee.Terrain.slope(dem).rename("slope")).reduceRegion(ee.Reducer.first(), pt, 30),
        "SRTM",
    )
    return {"elevation_m": vals.get("elev"), "slope_deg": round(vals["slope"], 2) if vals.get("slope") is not None else None}


def cmip6_season(lat: float, lon: float, heat_c: float) -> dict[str, Any]:
    """Multi-model mean May to October rain and hot days, historical vs 2040s."""
    pt = ee.Geometry.Point([lon, lat])
    base = ee.ImageCollection("NASA/GDDP-CMIP6").filter(ee.Filter.calendarRange(5, 10, "month"))
    periods = {
        "historical": ("historical", "1995-01-01", "2015-01-01"),
        "ssp245_2040s": ("ssp245", "2040-01-01", "2050-01-01"),
        "ssp585_2040s": ("ssp585", "2040-01-01", "2050-01-01"),
    }
    out: dict[str, Any] = {"models": CMIP6_MODELS}
    for key, (scenario, start, end) in periods.items():
        rains, heats = [], []
        for model in CMIP6_MODELS:
            col = base.filter(ee.Filter.eq("model", model)).filter(ee.Filter.eq("scenario", scenario)).filterDate(start, end)
            img = ee.Image.cat(
                col.select("pr").mean().multiply(86400 * 184).rename("rain"),
                col.select("tasmax").map(lambda i: i.gt(273.15 + heat_c)).mean().multiply(184).rename("heat"),
            )
            v = _getinfo(img.reduceRegion(ee.Reducer.first(), pt, 27830), f"CMIP6 {model} {key}")
            if v.get("rain") is not None:
                rains.append(v["rain"])
                heats.append(v["heat"])
        if rains:
            out[key] = {"season_rain_mm": round(sum(rains) / len(rains), 1), "heat_days": round(sum(heats) / len(heats), 1)}
    return out
