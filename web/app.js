// Rotawise dashboard. Plain ES module, no build step.
// All API text is inserted with escapeHtml or textContent to prevent XSS.

const API = "/api/v1";
const state = { plots: [], selected: null, lang: "en", prices: {}, map: null };

const CLASS_LABEL = {
  en: { cereal_like: "Cereal-like", legume_or_short_cycle: "Legume / short", bare_or_fallow: "Bare / fallow", unknown: "Unclear" },
  ha: { cereal_like: "Hatsi", legume_or_short_cycle: "Wake / gyada", bare_or_fallow: "Babu shuka", unknown: "Ba a sani ba" },
};
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ngn = (v) => "₦" + Math.round(v).toLocaleString("en-NG");
const range = (r, f = (x) => x) => (r[0] === r[1] ? f(r[0]) : `${f(r[0])} to ${f(r[1])}`);

async function getJSON(url, opts) {
  const res = await fetch(url, { ...opts, headers: { Accept: "application/json", ...(opts?.headers || {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(body.detail || res.statusText), { status: res.status });
  return body;
}

// ---------- farms + map ----------
async function loadPlots() {
  const { plots } = await getJSON(`${API}/plots`);
  state.plots = plots;
  const ul = document.getElementById("farmList");
  ul.innerHTML = "";
  for (const p of plots) {
    const li = document.createElement("li");
    li.innerHTML = `<button class="farm" type="button" data-id="${escapeHtml(p.id)}">
      <strong>${escapeHtml(p.lga)}, ${escapeHtml(p.state)}</strong>
      <span>Farm ${escapeHtml(p.id)}
        <em class="pill ${p.has_data ? "ok" : ""}">${p.has_data ? "data ready" : "no data yet"}</em>
        ${p.coords_verified ? "" : '<em class="pill">unverified</em>'}</span></button>`;
    li.querySelector("button").addEventListener("click", () => select(p.id));
    ul.appendChild(li);
  }
  initMap();
}

function initMap() {
  if (!window.maplibregl) return;
  const map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {
        osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" },
        gibs: {
          type: "raster", tileSize: 256, maxzoom: 9,
          tiles: ["https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2025-11-20/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"],
          attribution: "NASA GIBS / MODIS Terra",
        },
      },
      layers: [
        { id: "osm", type: "raster", source: "osm" },
        { id: "gibs", type: "raster", source: "gibs", layout: { visibility: "none" } },
      ],
    },
    center: [7.8, 10.3], zoom: 5.6,
  });
  state.map = map;
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
  map.on("load", () => {
    map.addSource("plots", {
      type: "geojson",
      data: { type: "FeatureCollection", features: state.plots.map((p) => ({ type: "Feature", properties: { id: p.id, lga: p.lga }, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) },
    });
    map.addLayer({ id: "plots", type: "circle", source: "plots", paint: { "circle-radius": 8, "circle-color": "#7a4e2d", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
    map.on("click", "plots", (e) => select(e.features[0].properties.id));
    map.on("mouseenter", "plots", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "plots", () => (map.getCanvas().style.cursor = ""));
  });
  document.getElementById("gibsToggle").addEventListener("change", (e) => {
    map.setLayoutProperty("gibs", "visibility", e.target.checked ? "visible" : "none");
  });
}

// ---------- detail ----------
async function select(id) {
  state.selected = id;
  document.querySelectorAll(".farm").forEach((b) => b.setAttribute("aria-current", String(b.dataset.id === id)));
  const p = state.plots.find((x) => x.id === id);
  if (state.map && p) state.map.flyTo({ center: [p.lon, p.lat], zoom: 12, speed: 1.4 });
  const detail = document.getElementById("detail");
  detail.innerHTML = `<div class="panel"><p>Reading ${escapeHtml(p?.lga)} from orbit…</p></div>`;
  const q = new URLSearchParams({ lang: state.lang, ...state.prices });
  try {
    const r = await getJSON(`${API}/plots/${encodeURIComponent(id)}/advice?${q}`);
    detail.innerHTML = renderMemory(r) + renderSoil(r) + renderClimate(r) + renderOptions(r);
  } catch (err) {
    detail.innerHTML = err.status === 409
      ? `<div class="panel warn"><h3>No satellite data yet</h3><p>This farm has not been through the NASA data pipeline. Run <code>python -m pipeline.extract --project YOUR_PROJECT --plot ${escapeHtml(id)}</code>.</p></div>`
      : `<div class="panel warn"><h3>Could not load this farm</h3><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderMemory(r) {
  const seasons = r.field_memory.seasons;
  const labels = CLASS_LABEL[state.lang];
  const chips = seasons.map((s) => `
    <div class="season c-${escapeHtml(s.season_class)}" title="${escapeHtml(labels[s.season_class])}, ${s.n_obs} clear images, peak NDVI ${s.peak ?? "n/a"}">
      <b>${s.year}</b>${escapeHtml(labels[s.season_class])}
      <span class="conf" aria-label="confidence ${Math.round(s.confidence * 100)}%"><i style="width:${Math.round(s.confidence * 100)}%"></i></span>
    </div>`).join("");
  const last = seasons.filter((s) => s.season_class !== "unknown").slice(-1)[0];
  const bare = last && last.bare_months.length ? `In ${last.year} the field looked bare in ${last.bare_months.map((m) => MONTHS[m - 1]).join(", ")}.` : "";
  const cur = r.field_memory.current;
  return `<div class="panel">
    <h3>Field memory</h3>
    <p class="sub">${seasons.length} seasons of NASA HLS imagery, plot-mean NDVI. Bar under each year shows confidence.</p>
    <div class="timeline">${chips || "<p>No clear seasons found.</p>"}</div>
    <div class="legend"><span><i class="c-cereal_like"></i>Cereal-like</span><span><i class="c-legume_or_short_cycle"></i>Legume or short cycle</span><span><i class="c-bare_or_fallow"></i>Bare or fallow</span><span><i class="c-unknown"></i>Too cloudy</span></div>
    <p>${cur.cereal_run >= 2 ? `<strong>${cur.cereal_run} cereal-like seasons in a row.</strong> ` : ""}${escapeHtml(bare)} Confirm past crops with the farmer before acting.</p>
  </div>`;
}

function renderSoil(r) {
  const f = r.soil.fatigue;
  if (f.score == null) return `<div class="panel"><h3>Soil fatigue</h3><p>Not enough data yet.</p></div>`;
  const drivers = f.drivers.map((d) => `<li>${escapeHtml(d.text)} <span class="fine">(+${d.contribution})</span></li>`).join("");
  const gaps = f.information_gaps.map((g) => `<li>${escapeHtml(g)}</li>`).join("");
  return `<div class="panel">
    <h3>Soil fatigue</h3>
    <div class="gauge"><div class="num">${f.score}<span class="fine">/100</span></div><div class="bar"><i style="left:calc(${f.score}% - 2px)"></i></div></div>
    <p class="sub">${escapeHtml(f.level)} pressure. From the season history, the greenness trend and iSDAsoil 0 to 20 cm.</p>
    <ul class="drivers">${drivers}</ul>${gaps ? `<ul class="fine">${gaps}</ul>` : ""}
  </div>`;
}

function renderClimate(r) {
  const c = r.climate;
  if (!c.available) return `<div class="panel"><h3>Climate</h3><p>No rainfall record ingested yet.</p></div>`;
  const s = c.series.filter((x) => x.mm != null);
  const max = Math.max(...s.map((x) => x.mm), 1);
  const w = 100 / Math.max(s.length, 1);
  const bars = s.map((x, i) => `<rect x="${i * w + w * 0.15}" y="${100 - (x.mm / max) * 90}" width="${w * 0.7}" height="${(x.mm / max) * 90}" fill="#3f7d4e" rx="2"><title>${x.year}: ${Math.round(x.mm)} mm</title></rect>`).join("");
  const p = c.projections.ssp245_2040s;
  const o = c.observed;
  return `<div class="panel rain">
    <h3>Rain and heat</h3>
    <p class="sub">May to October rainfall per year, ${escapeHtml(c.rain_source)}.</p>
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Seasonal rainfall by year">${bars}</svg>
    <div class="kv">
      <div><b>${o.season_rain_mm_median ?? "n/a"} mm</b><span>Typical season rain</span></div>
      <div><b>${o.onset_doy_median ? dayToDate(o.onset_doy_median) : "n/a"}</b><span>Typical rain onset</span></div>
      <div><b>${o.max_dry_spell_days_median ?? "n/a"} days</b><span>Longest dry spell</span></div>
      ${p ? `<div><b>${p.rain_change_pct > 0 ? "+" : ""}${p.rain_change_pct}%</b><span>Rain by 2040s (SSP2-4.5)</span></div>
      <div><b>${p.heat_days} days</b><span>Days above 35 °C, 2040s</span></div>` : ""}
    </div>
  </div>`;
}

function dayToDate(doy) {
  const d = new Date(Date.UTC(2023, 0, doy));
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

function renderOptions(r) {
  const rot = r.rotations;
  const cards = rot.options.map((o) => {
    const e = o.benefits.economics;
    const best = o.id === rot.recommended;
    const money = e ? `<div class="money">
        <span><b>${range(e.per_ha.urea_bags_saved)}</b> bags urea saved/ha</span>
        <span><b>${range(e.per_ha.fertilizer_saved_ngn, ngn)}</b> fertilizer/ha</span>
        ${e.per_ha.extra_maize_value_ngn ? `<span><b>${range(e.per_ha.extra_maize_value_ngn, ngn)}</b> extra maize/ha</span>` : ""}
        <span><b>${range(o.benefits.striga_reduction_pct)}%</b> less Striga</span></div>` : "";
    const list = (xs) => xs.map((x) => `<li>${escapeHtml(typeof x === "string" ? x : x.text)}</li>`).join("");
    return `<article class="opt ${best ? "best" : ""} ${o.is_current ? "current" : ""}">
      <header><h4>${o.sequence_labels.map(escapeHtml).join(" → ")}
        ${o.is_current ? '<span class="badge">current</span>' : ""}${best ? '<span class="badge best">recommended</span>' : ""}</h4>
        <span class="score" title="Composite score">${o.score}</span></header>
      ${money}
      <ul>${list(o.why)}</ul>
      <details><summary>Evidence</summary><ul class="fine">${list(o.evidence)}</ul></details>
      <details><summary>Information gaps</summary><ul>${list(o.information_gaps)}</ul></details>
      <details><summary>Risks for local review</summary><ul>${list(o.risks_for_local_review)}</ul></details>
    </article>`;
  }).join("");
  return `<div class="panel">
    <h3>Rotation options</h3>
    <p class="sub">${escapeHtml(rot.zone.label)}. Prices: urea ${ngn(rot.prices_used.urea_ngn_per_bag)}/bag, maize ${ngn(rot.prices_used.maize_ngn_per_bag)}/bag. Change them under Market prices.</p>
    <div class="options">${cards}</div>
    <p class="fine">${escapeHtml(rot.disclaimer)}</p>
  </div>`;
}

// ---------- controls ----------
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  state.lang = b.dataset.lang;
  document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  if (state.selected) select(state.selected);
}));

document.getElementById("priceForm").addEventListener("submit", (e) => {
  e.preventDefault();
  state.prices = Object.fromEntries([...new FormData(e.target)].filter(([, v]) => v !== ""));
  if (state.selected) select(state.selected);
});

// ---------- USSD simulator ----------
const ussd = { path: [], session: null, open: false };
const screen = document.getElementById("ussdScreen");

async function ussdSend() {
  const body = new URLSearchParams({ sessionId: ussd.session, serviceCode: "*384*7726#", phoneNumber: "+2340000000000", text: ussd.path.join("*") });
  try {
    const res = await fetch(`${API}/ussd`, { method: "POST", body });
    const txt = await res.text();
    ussd.open = txt.startsWith("CON ");
    screen.textContent = txt.replace(/^(CON|END) /, "") + (ussd.open ? "" : "\n\n[session ended]");
  } catch {
    screen.textContent = "Network error. Dial again.";
    ussd.open = false;
  }
}

document.getElementById("ussdDial").addEventListener("click", () => {
  ussd.path = [];
  ussd.session = crypto.randomUUID();
  ussdSend();
});
document.getElementById("ussdForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("ussdInput");
  const v = input.value.trim();
  input.value = "";
  if (!ussd.open || !v) return;
  ussd.path.push(v);
  ussdSend();
});

loadPlots().catch((err) => {
  document.getElementById("farmList").innerHTML = `<li class="warn">Could not reach the API: ${escapeHtml(err.message)}</li>`;
});
