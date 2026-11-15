"""Rotawise HTTP API (versioned under /api/v1) plus the static dashboard."""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Form, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .. import __version__, config, ussd
from ..engine import DataNotIngested, PlotNotFound, Prices, analyze, default_prices
from .middleware import ObservabilityMiddleware, TokenBucket, configure_logging

configure_logging()

app = FastAPI(
    title="Rotawise API",
    version=__version__,
    description="Crop rotation decision support from NASA Earth observations.",
    docs_url="/api/docs",
    openapi_url="/api/v1/openapi.json",
)

origins = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    ObservabilityMiddleware,
    limiter=TokenBucket(int(os.environ.get("RATE_LIMIT_PER_MIN", "120")), int(os.environ.get("RATE_LIMIT_BURST", "40"))),
)


def _data_version(plot_id: str) -> float:
    """File mtime: part of the cache key, so new pipeline output invalidates it."""
    p = config.DATA_DIR / "plots" / f"{plot_id}.json"
    return p.stat().st_mtime if p.is_file() else 0.0


@lru_cache(maxsize=512)
def _cached_analysis(plot_id: str, version: float, urea: float, maize: float, yld: float, lang: str) -> dict[str, Any]:
    return analyze(plot_id, Prices(urea, maize, yld), lang)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/ready")
def ready() -> dict[str, Any]:
    """Readiness: configuration loads and at least the plot index is readable."""
    try:
        n = len(config.plots_index())
        config.coefficients()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"not ready: {exc}") from exc
    ingested = sum(1 for p in config.plots_index() if _data_version(p["id"]))
    return {"status": "ready", "plots": n, "plots_with_data": ingested}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/plots")
def list_plots(response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "public, max-age=60"
    plots = [{**p, "has_data": bool(_data_version(p["id"]))} for p in config.plots_index()]
    return {"plots": plots}


@app.get("/api/v1/plots/{plot_id}/advice")
def advice(
    plot_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,32}$")],
    response: Response,
    urea_price: Annotated[float | None, Query(gt=0, le=1_000_000)] = None,
    maize_price: Annotated[float | None, Query(gt=0, le=1_000_000)] = None,
    baseline_yield: Annotated[float | None, Query(gt=0, le=15)] = None,
    lang: Literal["en", "ha"] = "en",
) -> dict[str, Any]:
    if config.plot_meta(plot_id) is None:
        raise HTTPException(404, "Unknown plot")
    d = default_prices()
    try:
        result = _cached_analysis(
            plot_id, _data_version(plot_id),
            urea_price or d.urea_ngn_per_bag, maize_price or d.maize_ngn_per_bag,
            baseline_yield or d.baseline_maize_t_ha, lang,
        )
    except PlotNotFound as exc:
        raise HTTPException(404, "Unknown plot") from exc
    except DataNotIngested as exc:
        raise HTTPException(409, "No satellite data ingested for this plot yet. Run the pipeline.") from exc
    response.headers["Cache-Control"] = "public, max-age=300"
    return result


@app.get("/api/v1/validation")
def validation() -> dict[str, Any]:
    v = config.load_validation()
    return {"available": v is not None, "result": v}


@app.post("/api/v1/ussd", response_class=PlainTextResponse)
def ussd_callback(
    request: Request,
    sessionId: Annotated[str, Form(max_length=128)] = "",  # noqa: N803 - Africa's Talking field names
    text: Annotated[str, Form(max_length=200)] = "",
    phoneNumber: Annotated[str, Form(max_length=32)] = "",  # noqa: N803 - accepted but never stored or logged
    serviceCode: Annotated[str, Form(max_length=32)] = "",  # noqa: N803
) -> str:
    token = os.environ.get("USSD_CALLBACK_TOKEN")
    if token and not hmac.compare_digest(request.query_params.get("token", ""), token):
        raise HTTPException(403, "Forbidden")
    return ussd.handle(text)


web_dir = config.WEB_DIR
if web_dir.is_dir():
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
