<p><img src="assets/logo.svg" alt="Rotawise logo" width="72"></p>

# Rotawise

Field memory from NASA satellites. Rotawise rebuilds each Nigerian smallholder plot's season history from ten years of NASA Harmonized Landsat Sentinel imagery, scores how tired the soil is, compares at least three crop rotations (including the farmer's current one) against NASA rainfall and climate projections, prices the result in naira, and delivers the advice in Hausa or English over USSD on any phone.

Built for the 2026 NASA Space Apps Challenge, **Field Shift: Adapting Farms with NASA Data**, Abuja Local Event. Open source under Apache 2.0.

## How it works

```
NASA HLS (L30 + S30) ─┐
MODIS MOD13Q1 ────────┤                     ┌─ Field memory: cereal-like / legume-like / bare, per season, with confidence
GPM IMERG monthly ────┤   pipeline/extract  │
NASA POWER daily ─────┼──► data/plots/*.json ┼─ Soil fatigue 0-100 with drivers
NEX-GDDP-CMIP6 ───────┤                     │
iSDAsoil, SRTM ───────┘                     └─ Rotation cards: why, evidence, naira benefits, gaps, risks
                                                      │
                               FastAPI /api/v1 ───────┼── Web dashboard (extension officers)
                                                      └── USSD /api/v1/ussd (farmers, Africa's Talking)
```

All agronomy numbers and thresholds live in `data/coefficients.yaml`, each next to its published source. The classifier never names a crop: 30 m pixels on 0.3 to 0.5 ha intercropped plots cannot reliably do that, so it reports a season type with a confidence score and asks for farmer confirmation.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                                              # 27 tests
uvicorn rotawise.api.main:app --reload --no-access-log
# open http://localhost:8000  (API docs at /api/docs)
```

Farms show "no data yet" until the pipeline has run for them.

## Getting real NASA data in

**Quick route, no accounts needed:** `python -m pipeline.pc_extract`. It picks a real cropland point in each LGA from ESA WorldCover, reads NASA HLS NDVI from Microsoft Planetary Computer, NASA POWER daily climate, NASA NEX-GDDP-CMIP6 projections from the NCCS THREDDS server, and SoilGrids soil properties, then writes `data/plots/<id>.json`.

**Earth Engine route** (adds MODIS, IMERG, iSDAsoil and SRTM):

1. Install the pipeline extras: `pip install -r requirements-pipeline.txt`
2. Sign in to Earth Engine: `earthengine authenticate` and note your registered Cloud project ID.
3. Put real field coordinates in `data/plots.json` (centre of a cultivated field, checked on satellite view) and set `coords_verified` to `true`.
4. Extract:
   ```bash
   python -m pipeline.extract --project YOUR_GEE_PROJECT            # all plots
   python -m pipeline.extract --project YOUR_GEE_PROJECT --plot 101 # one plot
   python -m pipeline.extract --power-only                          # climate only, no Earth Engine
   ```
   Output goes to `data/plots/<id>.json`. Re-runs skip finished plots unless `--force`.
5. Measure accuracy (required for honesty in the submission): prepare `data/labels.csv` with `lat,lon,year,crop` rows (Jos Plateau GEOGLAM labels, Ghana crop-type labels, or points confirmed with farmers), then
   ```bash
   python -m pipeline.validate --project YOUR_GEE_PROJECT --labels data/labels.csv --source "Jos Plateau GEOGLAM"
   ```
   This writes `data/validation.json`. Report the number as it comes out.
6. Commit `data/plots/*.json` and `data/validation.json`, then redeploy.

If a dataset ID fails, check it in the Earth Engine catalog; IDs are listed at the top of `pipeline/ee_sources.py`.

## Deploy

**Render (free):** push to GitHub, then New > Blueprint and select this repo. `render.yaml` builds the Docker image, sets the health check and generates the USSD token.

**Any Docker host:**
```bash
docker build -t rotawise . && docker run -p 8000:8000 --env-file .env rotawise
```

**Vercel (live now):** https://rotawise-five.vercel.app. Run `scripts/build_vercel.sh`, set `TRUST_PROXY=1` in the project settings, then `vercel deploy --prod`. The dashboard is served from `public/` by the CDN and the API runs from `app.py`.

## USSD (Africa's Talking)

1. Create a sandbox app at africastalking.com and a USSD channel on the shared code.
2. Set the callback URL to `https://YOUR_HOST/api/v1/ussd?token=YOUR_USSD_CALLBACK_TOKEN`.
3. Test in the Africa's Talking simulator, or in the phone panel on the dashboard.

The handler is stateless (the full menu path arrives in `text`), so any instance answers any step. Phone numbers are accepted but never stored or logged.

## Production notes

Covered in this build: versioned API (`/api/v1`), input validation, per-client token-bucket rate limiting, response caching keyed on data version (new pipeline output invalidates it), gzip, strict security headers and CSP, request IDs, structured JSON logs without personal data, Prometheus metrics at `/metrics`, liveness and readiness probes, non-root Docker image with health check, Gunicorn worker supervision, retries with exponential backoff and jitter in the pipeline, atomic data writes, CI with lint, tests and a container smoke test, and a privacy policy (`web/privacy.html`).

Next steps for scale: move the rate limiter to Redis or the API gateway, put the service behind a CDN for static assets, run Earth Engine extraction as a scheduled job with a service account, add SLO alerting on p99 latency and error rate, and multi-region hosting once farmer traffic exists.

## Team

Jothan Kato (lead), Adamilo Aaron Daniel, Umar Faruq Oladoja, Miracle Mathew, Sadiq Bashir Abdullahi, Ndazibari Charles Joshua.

## References

See `data/coefficients.yaml` (`sources`) for every agronomic figure, and `docs/SUBMISSION.md` for the full reference list used in the NASA submission.

## Use of AI tools

Parts of the code, dashboard, slides and documentation were drafted with Claude (Anthropic) as a coding assistant, then reviewed, tested and edited by the team, as declared in our Space Apps submission. No generated content uses NASA branding.
