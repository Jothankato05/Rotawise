"""Measure field memory accuracy against labelled crop points.

Input CSV columns: lat,lon,year,crop  (one row per labelled field-season)
Sources of labels: the Jos Plateau GEOGLAM crop-type dataset, Ghana crop-type
labels (transfer test), or points the team collects from farmers.

Usage:
    python -m pipeline.validate --project YOUR_GEE_PROJECT --labels data/labels.csv

Writes data/validation.json with accuracy and a confusion matrix, which the
dashboard and the submission report as-is, even if accuracy is modest.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone

from rotawise import config
from rotawise.engine.phenology import field_memory

from .extract import write_atomic

CROP_TO_CLASS = {
    **{c: "cereal_like" for c in ("maize", "sorghum", "millet", "rice", "corn")},
    **{c: "legume_or_short_cycle" for c in ("soybean", "soya", "cowpea", "groundnut", "peanut", "bean", "beans")},
    **{c: "bare_or_fallow" for c in ("fallow", "bare", "none")},
}
CLASSES = ["cereal_like", "legume_or_short_cycle", "bare_or_fallow"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--source", default="team labels", help="describe where the labels came from")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("rotawise.validate")

    from . import ee_sources

    ee_sources.init(args.project)
    cfg = config.coefficients()["phenology"]

    pairs: list[tuple[str, str]] = []
    skipped = Counter()
    with open(args.labels, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            truth = CROP_TO_CLASS.get(row["crop"].strip().lower())
            if truth is None:
                skipped["unmapped_crop"] += 1
                continue
            y = int(row["year"])
            obs = ee_sources.hls_ndvi(float(row["lat"]), float(row["lon"]), f"{y}-01-01", f"{y + 1}-01-01")
            seasons = [s for s in field_memory(obs, cfg) if s.year == y]
            if not seasons or seasons[0].season_class == "unknown":
                skipped["too_cloudy"] += 1
                continue
            pairs.append((truth, seasons[0].season_class))
            log.info("%s,%s %s truth=%s pred=%s", row["lat"], row["lon"], y, truth, seasons[0].season_class)

    if not pairs:
        log.error("no usable labelled points")
        return 1
    matrix = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    for t, p in pairs:
        matrix[t][p] += 1
    correct = sum(matrix[c][c] for c in CLASSES)
    per_class = {
        c: round(matrix[c][c] / sum(matrix[c].values()), 3) if sum(matrix[c].values()) else None for c in CLASSES
    }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label_source": args.source,
        "n_points": len(pairs),
        "overall_accuracy": round(correct / len(pairs), 3),
        "per_class_recall": per_class,
        "confusion_matrix": matrix,
        "skipped": dict(skipped),
        "coefficients_version": config.coefficients().get("version"),
    }
    write_atomic(config.DATA_DIR / "validation.json", result)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
