"""USSD menu, stateless, in the Africa's Talking callback format.

Africa's Talking sends the whole path the user has typed so far in `text`,
separated by "*" (for example "2*1*1"). Because the state is in the request,
the handler needs no session store and any instance can answer any step,
which keeps it safe to scale horizontally. Replies start with "CON " to keep
the session open or "END " to close it.
"""

from __future__ import annotations

from . import config
from .engine import DataNotIngested, PlotNotFound, analyze
from .i18n import t

MAX_LEN = 182


def _fit(s: str) -> str:
    return s if len(s) <= MAX_LEN else s[: MAX_LEN - 1] + "."


def con(s: str) -> str:
    return "CON " + _fit(s)


def end(s: str) -> str:
    return "END " + _fit(s)


def _farm_menu(lang: str) -> str:
    lines = [str(t(lang, "choose_farm"))]
    for i, p in enumerate(config.plots_index()[:8], start=1):
        lines.append(f"{i}. {p['lga']} ({p['id']})")
    return "\n".join(lines)


def _resolve_plot(choice: str) -> str | None:
    plots = config.plots_index()
    if choice.isdigit() and 1 <= int(choice) <= min(8, len(plots)):
        return plots[int(choice) - 1]["id"]
    return choice if config.plot_meta(choice) else None


def handle(text: str) -> str:
    parts = [p.strip() for p in (text or "").split("*")] if text else []
    if len(parts) > 6 or any(len(p) > 12 for p in parts):
        return end(str(t("en", "invalid")))
    if not parts:
        return con(str(t("en", "welcome")))

    lang = {"1": "en", "2": "ha"}.get(parts[0])
    if lang is None:
        return end(str(t("en", "invalid")))
    if len(parts) == 1:
        return con(_farm_menu(lang))

    plot_id = _resolve_plot(parts[1])
    if plot_id is None:
        return end(str(t(lang, "invalid")))
    try:
        result = analyze(plot_id, lang=lang)
    except (PlotNotFound, DataNotIngested):
        return end(str(t(lang, "no_data")))

    classes = t(lang, "classes")
    seasons = [s for s in result["field_memory"]["seasons"] if s["season_class"] != "unknown"][-4:]
    pattern = ", ".join(classes[s["season_class"]] for s in seasons) or classes["unknown"]
    score = result["soil"]["fatigue"]["score"]
    options = result["rotations"]["options"]

    if len(parts) == 2:
        return con(str(t(lang, "summary")).format(
            name=result["plot"]["lga"], n=len(seasons), pattern=pattern, score="?" if score is None else score,
        ))

    choice = parts[2]
    if choice == "0":
        return end(str(t(lang, "bye")))
    if choice == "1":
        best = next((o for o in options if o["id"] == result["rotations"]["recommended"]), None)
        econ = best and best["benefits"]["economics"]
        if not best or not econ:
            return end(str(t(lang, "best_none")))
        legume_label = next(
            (lbl for c, lbl in zip(best["sequence"], best["sequence_labels"], strict=True) if config.coefficients()["crops"][c]["type"] == "legume"),
            best["sequence_labels"][-1],
        )
        per_ha = econ["per_ha"]
        return end(str(t(lang, "best")).format(
            crop=legume_label.upper(),
            b0=per_ha["urea_bags_saved"][0], b1=per_ha["urea_bags_saved"][1],
            v0=round(per_ha["fertilizer_saved_ngn"][0] / 1000), v1=round(per_ha["fertilizer_saved_ngn"][1] / 1000),
            s=best["benefits"]["striga_reduction_pct"][1],
        ))
    if choice == "2":
        lines = []
        for o in options[:4]:
            name = "-".join(o["sequence_labels"])
            mark = "*" if o["is_current"] else ""
            lines.append(f"{name}{mark} {o['score']}")
        return end(str(t(lang, "compare")).format(lines="\n".join(lines)))
    return end(str(t(lang, "invalid")))
