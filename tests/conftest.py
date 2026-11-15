"""Test fixtures. All NDVI and climate values here are SYNTHETIC test inputs
shaped like savanna seasons; they are never shipped as data."""

from __future__ import annotations

import json
import math
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def season_curve(year: int, base: float, peak: float, start_doy: int, length: int, step: int = 8) -> list[dict]:
    """Bell-shaped green-up between start_doy and start_doy+length, plus dry season points."""
    obs = []
    for doy in range(10, 360, step):
        d = date(year, 1, 1) + timedelta(days=doy - 1)
        if start_doy <= doy <= start_doy + length:
            x = (doy - start_doy) / length
            v = base + (peak - base) * math.sin(math.pi * x)
        else:
            v = base
        obs.append({"date": d.isoformat(), "ndvi": round(v, 3)})
    return obs


@pytest.fixture
def cfg():
    from rotawise import config
    return config.coefficients()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """A temporary data directory with one synthetic plot, wired into config."""
    d = tmp_path / "data"
    (d / "plots").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "coefficients.yaml", d / "coefficients.yaml")
    shutil.copy(ROOT / "data" / "plots.json", d / "plots.json")
    ndvi = []
    for y in range(2018, 2025):
        ndvi += season_curve(y, 0.22, 0.72 - 0.02 * (y - 2018), 150, 130)  # cereal, declining
    payload = {
        "plot_id": "101",
        "extracted_at": "2026-11-14T00:00:00+00:00",
        "sources": {"ndvi": "synthetic test data"},
        "ndvi": ndvi,
        "soil": {"nitrogen_total_g_kg": 0.6, "organic_carbon_g_kg": 6.0, "phosphorus_ppm": 8.0, "ph": 5.9},
        "terrain": {"elevation_m": 650, "slope_deg": 1.2},
        "climate": {
            "observed": [{"year": y, "season_rain_mm": 900 + 10 * (y % 3), "onset_doy": 140, "max_dry_spell_days": 9, "heat_days": 20} for y in range(2016, 2026)],
            "imerg_season_rain_mm": [{"year": y, "mm": 880 + 15 * (y % 4)} for y in range(2016, 2026)],
            "cmip6": {"models": ["test"], "historical": {"season_rain_mm": 800, "heat_days": 30}, "ssp245_2040s": {"season_rain_mm": 760, "heat_days": 45}},
        },
    }
    (d / "plots" / "101.json").write_text(json.dumps(payload))
    from rotawise import config
    monkeypatch.setattr(config, "DATA_DIR", d)
    config.clear_caches()
    yield d
    config.clear_caches()
