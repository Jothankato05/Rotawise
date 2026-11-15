"""Extract all NASA and partner data for the pilot plots.

Usage:
    python -m pipeline.extract --project YOUR_GEE_PROJECT            # all plots
    python -m pipeline.extract --project YOUR_GEE_PROJECT --plot 101 # one plot
    python -m pipeline.extract --power-only                          # no Earth Engine

Writes data/plots/<id>.json atomically, so a crash never leaves a half file.
Already extracted plots are skipped unless --force is given.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from rotawise import config

from . import power

log = logging.getLogger("rotawise.pipeline")
HLS_START, HLS_END = "2016-01-01", "2026-01-01"
YEARS = (2016, 2025)


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, path)


def extract_plot(plot: dict, use_ee: bool, heat_c: float) -> dict:
    lat, lon = plot["lat"], plot["lon"]
    out: dict = {
        "plot_id": plot["id"],
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coords": {"lat": lat, "lon": lon},
        "sources": {},
        "climate": {},
    }

    log.info("[%s] NASA POWER daily %s-%s", plot["id"], *YEARS)
    params = power.fetch_daily(lat, lon, *YEARS)
    out["climate"]["observed"] = power.seasonal_summary(params, *YEARS, heat_c)
    out["sources"]["climate_observed"] = "NASA POWER daily agroclimatology (PRECTOTCORR, T2M_MAX)"

    if use_ee:
        from . import ee_sources as src

        log.info("[%s] HLS NDVI", plot["id"])
        out["ndvi"] = src.hls_ndvi(lat, lon, HLS_START, HLS_END)
        out["sources"]["ndvi"] = "NASA HLS HLSL30 v002 and HLSS30 v002 (Fmask cloud-masked, plot-mean NDVI)"
        log.info("[%s] MODIS NDVI", plot["id"])
        out["modis_ndvi"] = src.modis_ndvi(lat, lon, HLS_START, HLS_END)
        out["sources"]["modis_ndvi"] = "NASA MODIS MOD13Q1 v061"
        log.info("[%s] IMERG rainfall", plot["id"])
        out["climate"]["imerg_season_rain_mm"] = src.imerg_season_rain(lat, lon, *YEARS)
        out["sources"]["rain"] = "NASA GPM IMERG V07 monthly"
        log.info("[%s] CMIP6 projections", plot["id"])
        out["climate"]["cmip6"] = src.cmip6_season(lat, lon, heat_c)
        out["sources"]["projections"] = "NASA NEX-GDDP-CMIP6 (ACCESS-CM2, MRI-ESM2-0, MIROC6)"
        log.info("[%s] iSDAsoil + SRTM", plot["id"])
        out["soil"] = src.isda_soil(lat, lon)
        out["sources"]["soil"] = "iSDAsoil Africa v1, 0-20 cm (CC BY 4.0)"
        out["terrain"] = src.srtm_slope(lat, lon)
        out["sources"]["terrain"] = "NASA SRTM GL1 v003"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="Google Cloud project registered for Earth Engine")
    ap.add_argument("--plot", help="only this plot id")
    ap.add_argument("--power-only", action="store_true", help="skip Earth Engine datasets")
    ap.add_argument("--force", action="store_true", help="re-extract plots that already have data")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    use_ee = not args.power_only
    if use_ee:
        if not args.project:
            ap.error("--project is required unless --power-only is set")
        from . import ee_sources

        ee_sources.init(args.project)

    heat_c = config.coefficients()["climate"]["heat_day_threshold_c"]
    plots = [p for p in config.plots_index() if not args.plot or p["id"] == args.plot]
    if not plots:
        log.error("no plot matches %s", args.plot)
        return 2

    failures = 0
    for plot in plots:
        target = config.DATA_DIR / "plots" / f"{plot['id']}.json"
        if target.exists() and not args.force:
            log.info("[%s] already extracted, skipping (use --force)", plot["id"])
            continue
        if not plot.get("coords_verified"):
            log.warning("[%s] coordinates not verified against a real field", plot["id"])
        try:
            write_atomic(target, extract_plot(plot, use_ee, heat_c))
            log.info("[%s] written to %s", plot["id"], target)
        except Exception:  # noqa: BLE001 - keep going with the other plots
            failures += 1
            log.exception("[%s] extraction failed", plot["id"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
