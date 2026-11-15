"""Configuration and data loading.

Paths come from environment variables so the same image runs locally,
in CI and in production without code changes.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ROTAWISE_DATA_DIR", ROOT / "data"))
WEB_DIR = Path(os.environ.get("ROTAWISE_WEB_DIR", ROOT / "web"))


@lru_cache(maxsize=1)
def coefficients() -> dict[str, Any]:
    with open(DATA_DIR / "coefficients.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def plots_index() -> list[dict[str, Any]]:
    with open(DATA_DIR / "plots.json", encoding="utf-8") as fh:
        return json.load(fh)["plots"]


def plot_meta(plot_id: str) -> dict[str, Any] | None:
    return next((p for p in plots_index() if p["id"] == plot_id), None)


def load_plot_observations(plot_id: str) -> dict[str, Any] | None:
    """Return extracted NASA data for a plot, or None if not ingested yet.

    plot_id is validated against the index before touching the filesystem,
    so user input can never be used to build an arbitrary path.
    """
    if plot_meta(plot_id) is None:
        return None
    path = DATA_DIR / "plots" / f"{plot_id}.json"
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_validation() -> dict[str, Any] | None:
    path = DATA_DIR / "validation.json"
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def clear_caches() -> None:
    coefficients.cache_clear()
    plots_index.cache_clear()
