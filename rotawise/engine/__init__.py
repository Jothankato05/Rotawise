"""Rotawise engine: field memory, soil fatigue, climate and rotation comparison."""

from __future__ import annotations

from typing import Any

from .. import config
from . import climate as climate_mod
from .phenology import current_rotation_label, field_memory
from .rotations import Prices, compare
from .soil import fatigue_score


class PlotNotFound(LookupError):
    pass


class DataNotIngested(LookupError):
    pass


def default_prices() -> Prices:
    e = config.coefficients()["economics"]
    return Prices(
        urea_ngn_per_bag=float(e["urea_price_ngn_per_bag"]),
        maize_ngn_per_bag=float(e["maize_price_ngn_per_bag"]),
        baseline_maize_t_ha=float(e["baseline_maize_yield_t_ha"]),
    )


def analyze(plot_id: str, prices: Prices | None = None, lang: str = "en") -> dict[str, Any]:
    meta = config.plot_meta(plot_id)
    if meta is None:
        raise PlotNotFound(plot_id)
    data = config.load_plot_observations(plot_id)
    if data is None:
        raise DataNotIngested(plot_id)

    cfg = config.coefficients()
    seasons = field_memory(data.get("ndvi") or [], cfg["phenology"])
    current = current_rotation_label(seasons)
    memory = {"seasons": [s.to_dict() for s in seasons], "current": current}
    fatigue = fatigue_score(seasons, data.get("soil"), current["cereal_run"], cfg, lang)
    clim = climate_mod.summarize(data.get("climate"))
    rot = compare(meta, memory, fatigue, clim, cfg, prices or default_prices(), lang)

    return {
        "plot": meta,
        "extracted_at": data.get("extracted_at"),
        "data_sources": data.get("sources", {}),
        "field_memory": memory,
        "soil": {"properties": data.get("soil"), "terrain": data.get("terrain"), "fatigue": fatigue},
        "climate": clim,
        "rotations": rot,
        "coefficients_version": cfg.get("version"),
    }
