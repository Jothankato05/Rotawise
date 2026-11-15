// Rotawise dashboard. Plain ES module, no build step.
// All API text is inserted with escapeHtml or textContent to prevent XSS.

const API = "/api/v1";
const state = { plots: [], selected: null, lang: "en", prices: {}, map: null };

const CLASS_LABEL = {
  en: { cereal_like: "Cereal-like", legume_or_short_cycle: "Legume / short", bare_or_fallow: "Bare / fallow", unknown: "Unclear" },
  ha: { cereal_like: "Hatsi", legume_or_short_cycle: "Wake / gyada", bare_or_fallow: "Babu shuka", unknown: "Ba a sani ba" },
};

// Interface text. HAUSA MUST BE CHECKED BY A NATIVE SPEAKER (see rotawise/messages.py).
const UI = {
  en: {
    tag: "Field memory from NASA satellites", prices: "Market prices", urea: "Urea, ₦ per 50 kg bag", maize: "Maize, ₦ per 100 kg bag",
    yield: "Baseline maize yield, t/ha", update: "Update", farms: "Pilot farms", farmsNote: "Each pilot point is a cropland block confirmed on ESA WorldCover.",
    gibs: "NASA MODIS true colour (GIBS)", pick: "Pick a farm",
    pickBody: "Rotawise reads every NASA Harmonized Landsat Sentinel image of each plot since 2020 to rebuild its season history, scores how tired the soil is, and compares crop rotations against NASA climate records and projections.",
    dialHint: "Dial *384*7726# to start", reply: "Reply", send: "Send", dial: "Dial", anyPhone: "Works on any phone",
    ussdBody: "Farmers get the same advice over USSD in English or Hausa, with no smartphone and no data bundle. This simulator calls the live Rotawise USSD endpoint in the Africa's Talking format.",
    ussdNote: "Short code shown is a placeholder until a code is leased.", privacy: "Privacy policy",
    farm: "Farm", ready: "data ready", noData: "no data yet", unverified: "unverified", reading: (l) => `Reading ${l} from orbit…`,
    noSat: "No satellite data yet", noSatBody: "This farm has not been through the NASA data pipeline yet.", loadFail: "Could not load this farm",
    memory: "Field memory", memorySub: (n) => `${n} seasons of NASA HLS imagery (Landsat and Sentinel 2, 30 m), cloud-masked NDVI. The bar under each year shows confidence; grey years had too few clear images.`,
    clearImages: "clear images", peak: "peak NDVI", noSeasons: "No clear seasons found.",
    lgCereal: "Cereal-like", lgLegume: "Legume or short cycle", lgBare: "Bare or fallow", lgCloud: "Too cloudy",
    run: (n) => `${n} cereal-like seasons in a row.`, bare: (y, ms) => `In ${y} the field looked bare in ${ms}.`, confirm: "Confirm past crops with the farmer before acting.",
    soil: "Soil fatigue", notEnough: "Not enough data yet.", pressure: (l) => `${l} pressure. From the season history, the greenness trend and SoilGrids soil properties.`,
    rain: "Rain and heat", noRain: "No rainfall record ingested yet.", rainSub: (src) => `May to October rainfall per year, ${src}.`, leftOut: (ys) => ` Left out as likely data errors: ${ys}.`,
    typRain: "Typical season rain", onset: "Typical rain onset", drySpell: "Longest dry spell", days: "days", rain2040: "Rain by 2040s (SSP2-4.5)", heat2040: "Days above 35 °C, 2040s",
    options: "Rotation options", ureaSaved: "bags urea saved/ha", fertHa: "fertilizer/ha", maizeHa: "extra maize/ha", lessStriga: "less Striga",
    current: "current", recommended: "recommended", score: "Composite score", evidence: "Evidence", gaps: "Information gaps", risks: "Risks for local review",
    pricesUsed: (z, u, m) => `${z}. Prices: urea ${u}/bag, maize ${m}/bag. Change them under Market prices.`, to: "to",
    ended: "[session ended]", netErr: "Network error. Dial again.", apiErr: "Could not reach the API",
    footA: "Open source (Apache 2.0). Built for the 2026 NASA Space Apps Challenge, Field Shift. Data: NASA HLS, NASA POWER, NASA NEX-GDDP-CMIP6; ESA WorldCover (CC BY 4.0); ISRIC SoilGrids (CC BY 4.0). Map © OpenStreetMap contributors.",
    footB: "Rotawise supports farmer judgment and does not replace on-farm advice.", evidenceNote: "",
    months: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
  },
  ha: {
    tag: "Tarihin gona daga tauraron dan adam na NASA", prices: "Farashin kasuwa", urea: "Urea, ₦ a buhu kilo 50", maize: "Masara, ₦ a buhu kilo 100",
    yield: "Amfanin masara na yanzu, tan a hekta", update: "Sabunta", farms: "Gonakin gwaji", farmsNote: "Kowace gona ta gwaji fili ne na noma da aka tabbatar a taswirar ESA WorldCover.",
    gibs: "Hoton MODIS na NASA (GIBS)", pick: "Zabi gona",
    pickBody: "Rotawise na karanta kowane hoton NASA Harmonized Landsat Sentinel na gona tun 2020 don gano tarihin damina, ya auna gajiyar kasa, sannan ya kwatanta jerin amfanin gona da bayanan yanayi da hasashen NASA.",
    dialHint: "Buga *384*7726# don farawa", reply: "Amsa", send: "Aika", dial: "Buga", anyPhone: "Yana aiki a kowace waya",
    ussdBody: "Manoma na samun shawarar a USSD da Turanci ko Hausa, ba sai da wayar zamani ko data ba. Wannan gwajin yana kiran USSD na Rotawise kai tsaye.",
    ussdNote: "Lambar da ke nan ta wucin gadi ce har sai an samu lamba.", privacy: "Dokar sirri",
    farm: "Gona", ready: "bayanai sun shirya", noData: "babu bayanai tukuna", unverified: "ba a tabbatar ba", reading: (l) => `Ana karanta ${l} daga sararin samaniya…`,
    noSat: "Babu bayanan tauraron dan adam tukuna", noSatBody: "Ba a sarrafa bayanan NASA na wannan gona ba tukuna.", loadFail: "An kasa bude wannan gona",
    memory: "Tarihin gona", memorySub: (n) => `Damina ${n} na hotunan NASA HLS (Landsat da Sentinel 2, mita 30), NDVI ba tare da gajimare ba. Layin karkashin kowace shekara yana nuna tabbaci; shekarun toka basu da isassun hotuna masu haske.`,
    clearImages: "hotuna masu haske", peak: "NDVI mafi girma", noSeasons: "Ba a sami damina mai haske ba.",
    lgCereal: "Hatsi", lgLegume: "Wake ko gyada", lgBare: "Babu shuka", lgCloud: "Gajimare ya yi yawa",
    run: (n) => `Damina ${n} a jere da hatsi.`, bare: (y, ms) => `A ${y} gonar ba ta da shuka a watannin ${ms}.`, confirm: "A tabbatar da amfanin da aka shuka a baya tare da manomi kafin a dauki mataki.",
    soil: "Gajiyar kasa", notEnough: "Babu isassun bayanai tukuna.", pressure: (l) => `Matsi: ${l}. Daga tarihin damina, yanayin koren ganye da bayanan kasa na SoilGrids.`,
    rain: "Ruwan sama da zafi", noRain: "Babu bayanan ruwan sama tukuna.", rainSub: (src) => `Ruwan sama daga Mayu zuwa Oktoba a kowace shekara, ${src}.`, leftOut: (ys) => ` An cire su saboda kuskuren bayanai: ${ys}.`,
    typRain: "Ruwan damina na yau da kullum", onset: "Lokacin fara ruwa", drySpell: "Rani mafi tsawo cikin damina", days: "kwanaki", rain2040: "Ruwa nan da 2040 (SSP2-4.5)", heat2040: "Kwanaki sama da 35 °C, 2040",
    options: "Zabin jerin amfanin gona", ureaSaved: "buhun urea da aka tara/hekta", fertHa: "taki/hekta", maizeHa: "karin masara/hekta", lessStriga: "ragin Striga",
    current: "na yanzu", recommended: "shawararmu", score: "Maki gaba daya", evidence: "Hujjoji", gaps: "Bayanan da suka rage", risks: "Hadurran da jamiin gona zai duba",
    pricesUsed: (z, u, m) => `${z}. Farashi: urea ${u}/buhu, masara ${m}/buhu. A canza su a Farashin kasuwa.`, to: "zuwa",
    ended: "[zaman ya kare]", netErr: "Matsalar sadarwa. Sake bugawa.", apiErr: "An kasa kaiwa ga API",
    footA: "Bude ga kowa (Apache 2.0). An gina shi don gasar NASA Space Apps 2026, Field Shift. Bayanai: NASA HLS, NASA POWER, NASA NEX-GDDP-CMIP6; ESA WorldCover (CC BY 4.0); ISRIC SoilGrids (CC BY 4.0). Taswira © OpenStreetMap.",
    footB: "Rotawise na taimaka wa manomi ya yanke shawara, ba ya maye gurbin shawarar da ake bayarwa a gona.", evidenceNote: " (a Turanci, kamar yadda aka wallafa)",
    months: ["Jan","Fab","Mar","Afr","Mayu","Yun","Yul","Agu","Sat","Okt","Nuw","Dis"],
  },
};
const tt = (k) => (UI[state.lang] || UI.en)[k];

function applyStatic() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = tt(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = tt(el.dataset.i18nPh); });
  if (!state.selected) {
    const d = document.querySelector("#detail .empty");
    if (d) d.innerHTML = `<h2>${escapeHtml(tt("pick"))}</h2><p>${escapeHtml(tt("pickBody"))}</p>`;
  }
  if (!ussd.open && !ussd.session) screen.textContent = tt("dialHint");
}

const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ngn = (v) => "₦" + Math.round(v).toLocaleString("en-NG");
const range = (r, f = (x) => x) => (r[0] === r[1] ? f(r[0]) : `${f(r[0])} ${tt("to")} ${f(r[1])}`);

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
  renderFarms();
  initMap();
}

function renderFarms() {
  const ul = document.getElementById("farmList");
  ul.innerHTML = "";
  for (const p of state.plots) {
    const li = document.createElement("li");
    li.innerHTML = `<button class="farm" type="button" data-id="${escapeHtml(p.id)}">
      <strong>${escapeHtml(p.lga)}, ${escapeHtml(p.state)}</strong>
      <span>${escapeHtml(tt("farm"))} ${escapeHtml(p.id)}
        <em class="pill ${p.has_data ? "ok" : ""}">${escapeHtml(p.has_data ? tt("ready") : tt("noData"))}</em>
        ${p.coords_verified ? "" : `<em class="pill">${escapeHtml(tt("unverified"))}</em>`}</span></button>`;
    li.querySelector("button").addEventListener("click", () => select(p.id));
    if (li.querySelector("button").dataset.id === state.selected) li.querySelector("button").setAttribute("aria-current", "true");
    ul.appendChild(li);
  }
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
  detail.innerHTML = `<div class="panel"><p>${escapeHtml(tt("reading")(p?.lga ?? ""))}</p></div>`;
  const q = new URLSearchParams({ lang: state.lang, ...state.prices });
  try {
    const r = await getJSON(`${API}/plots/${encodeURIComponent(id)}/advice?${q}`);
    detail.innerHTML = renderMemory(r) + renderSoil(r) + renderClimate(r) + renderOptions(r);
  } catch (err) {
    detail.innerHTML = err.status === 409
      ? `<div class="panel warn"><h3>${escapeHtml(tt("noSat"))}</h3><p>${escapeHtml(tt("noSatBody"))}</p></div>`
      : `<div class="panel warn"><h3>${escapeHtml(tt("loadFail"))}</h3><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderMemory(r) {
  const seasons = r.field_memory.seasons;
  const labels = CLASS_LABEL[state.lang];
  const chips = seasons.map((s) => `
    <div class="season c-${escapeHtml(s.season_class)}" title="${escapeHtml(labels[s.season_class])}, ${s.n_obs} ${escapeHtml(tt("clearImages"))}, ${escapeHtml(tt("peak"))} ${s.peak ?? "n/a"}">
      <b>${s.year}</b>${escapeHtml(labels[s.season_class])}
      <span class="conf" aria-label="confidence ${Math.round(s.confidence * 100)}%"><i style="width:${Math.round(s.confidence * 100)}%"></i></span>
    </div>`).join("");
  const last = seasons.filter((s) => s.season_class !== "unknown").slice(-1)[0];
  const bare = last && last.bare_months.length ? tt("bare")(last.year, last.bare_months.map((m) => tt("months")[m - 1]).join(", ")) : "";
  const cur = r.field_memory.current;
  return `<div class="panel">
    <h3>${escapeHtml(tt("memory"))}</h3>
    <p class="sub">${escapeHtml(tt("memorySub")(seasons.length))}</p>
    <div class="timeline">${chips || `<p>${escapeHtml(tt("noSeasons"))}</p>`}</div>
    <div class="legend"><span><i class="c-cereal_like"></i>${tt("lgCereal")}</span><span><i class="c-legume_or_short_cycle"></i>${tt("lgLegume")}</span><span><i class="c-bare_or_fallow"></i>${tt("lgBare")}</span><span><i class="c-unknown"></i>${tt("lgCloud")}</span></div>
    <p>${cur.cereal_run >= 2 ? `<strong>${escapeHtml(tt("run")(cur.cereal_run))}</strong> ` : ""}${escapeHtml(bare)} ${escapeHtml(tt("confirm"))}</p>
  </div>`;
}

function renderSoil(r) {
  const f = r.soil.fatigue;
  if (f.score == null) return `<div class="panel"><h3>${escapeHtml(tt("soil"))}</h3><p>${escapeHtml(tt("notEnough"))}</p></div>`;
  const drivers = f.drivers.map((d) => `<li>${escapeHtml(d.text)} <span class="fine">(+${d.contribution})</span></li>`).join("");
  const gaps = f.information_gaps.map((g) => `<li>${escapeHtml(g)}</li>`).join("");
  return `<div class="panel">
    <h3>${escapeHtml(tt("soil"))}</h3>
    <div class="gauge"><div class="num">${f.score}<span class="fine">/100</span></div><div class="bar"><i style="left:calc(${f.score}% - 2px)"></i></div></div>
    <p class="sub">${escapeHtml(tt("pressure")(f.level_label || f.level))}</p>
    <ul class="drivers">${drivers}</ul>${gaps ? `<ul class="fine">${gaps}</ul>` : ""}
  </div>`;
}

function renderClimate(r) {
  const c = r.climate;
  if (!c.available) return `<div class="panel"><h3>${escapeHtml(tt("rain"))}</h3><p>${escapeHtml(tt("noRain"))}</p></div>`;
  const s = c.series.filter((x) => x.mm != null);
  const max = Math.max(...s.map((x) => x.mm), 1);
  const w = 100 / Math.max(s.length, 1);
  const bars = s.map((x, i) => `<rect x="${i * w + w * 0.15}" y="${100 - (x.mm / max) * 90}" width="${w * 0.7}" height="${(x.mm / max) * 90}" fill="#3f7d4e" rx="2"><title>${x.year}: ${Math.round(x.mm)} mm</title></rect>`).join("");
  const p = c.projections.ssp245_2040s;
  const o = c.observed;
  return `<div class="panel rain">
    <h3>${escapeHtml(tt("rain"))}</h3>
    <p class="sub">${escapeHtml(tt("rainSub")(c.rain_source))}${c.excluded_years && c.excluded_years.length ? escapeHtml(tt("leftOut")(c.excluded_years.join(", "))) : ""}</p>
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Seasonal rainfall by year">${bars}</svg>
    <div class="kv">
      <div><b>${o.season_rain_mm_median ?? "n/a"} mm</b><span>${escapeHtml(tt("typRain"))}</span></div>
      <div><b>${o.onset_doy_median ? dayToDate(o.onset_doy_median) : "n/a"}</b><span>${escapeHtml(tt("onset"))}</span></div>
      <div><b>${o.max_dry_spell_days_median ?? "n/a"} ${escapeHtml(tt("days"))}</b><span>${escapeHtml(tt("drySpell"))}</span></div>
      ${p ? `<div><b>${p.rain_change_pct > 0 ? "+" : ""}${p.rain_change_pct}%</b><span>${escapeHtml(tt("rain2040"))}</span></div>
      <div><b>${p.heat_days} ${escapeHtml(tt("days"))}</b><span>${escapeHtml(tt("heat2040"))}</span></div>` : ""}
    </div>
  </div>`;
}

function dayToDate(doy) {
  const d = new Date(Date.UTC(2023, 0, doy));
  return `${d.getUTCDate()} ${tt("months")[d.getUTCMonth()]}`;
}

function renderOptions(r) {
  const rot = r.rotations;
  const cards = rot.options.map((o) => {
    const e = o.benefits.economics;
    const best = o.id === rot.recommended;
    const money = e ? `<div class="money">
        <span><b>${range(e.per_ha.urea_bags_saved)}</b> ${escapeHtml(tt("ureaSaved"))}</span>
        <span><b>${range(e.per_ha.fertilizer_saved_ngn, ngn)}</b> ${escapeHtml(tt("fertHa"))}</span>
        ${e.per_ha.extra_maize_value_ngn ? `<span><b>${range(e.per_ha.extra_maize_value_ngn, ngn)}</b> ${escapeHtml(tt("maizeHa"))}</span>` : ""}
        <span><b>${range(o.benefits.striga_reduction_pct)}%</b> ${escapeHtml(tt("lessStriga"))}</span></div>` : "";
    const list = (xs) => xs.map((x) => `<li>${escapeHtml(typeof x === "string" ? x : x.text)}</li>`).join("");
    return `<article class="opt ${best ? "best" : ""} ${o.is_current ? "current" : ""}">
      <header><h4>${o.sequence_labels.map(escapeHtml).join(" → ")}
        ${o.is_current ? `<span class="badge">${escapeHtml(tt("current"))}</span>` : ""}${best ? `<span class="badge best">${escapeHtml(tt("recommended"))}</span>` : ""}</h4>
        <span class="score" title="${escapeHtml(tt("score"))}">${o.score}</span></header>
      ${money}
      <ul>${list(o.why)}</ul>
      <details><summary>${escapeHtml(tt("evidence") + tt("evidenceNote"))}</summary><ul class="fine">${list(o.evidence)}</ul></details>
      <details><summary>${escapeHtml(tt("gaps"))}</summary><ul>${list(o.information_gaps)}</ul></details>
      <details><summary>${escapeHtml(tt("risks"))}</summary><ul>${list(o.risks_for_local_review)}</ul></details>
    </article>`;
  }).join("");
  return `<div class="panel">
    <h3>${escapeHtml(tt("options"))}</h3>
    <p class="sub">${escapeHtml(tt("pricesUsed")(rot.zone.label, ngn(rot.prices_used.urea_ngn_per_bag), ngn(rot.prices_used.maize_ngn_per_bag)))}</p>
    <div class="options">${cards}</div>
    <p class="fine">${escapeHtml(rot.disclaimer)}</p>
  </div>`;
}

// ---------- controls ----------
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  state.lang = b.dataset.lang;
  document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  applyStatic();
  renderFarms();
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
    screen.textContent = txt.replace(/^(CON|END) /, "") + (ussd.open ? "" : `\n\n${tt("ended")}`);
  } catch {
    screen.textContent = tt("netErr");
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
  document.getElementById("farmList").innerHTML = `<li class="warn">${escapeHtml(tt("apiErr"))}: ${escapeHtml(err.message)}</li>`;
});
