"""Farmer-facing text in English and Hausa.

HAUSA STRINGS MUST BE CHECKED BY A NATIVE SPEAKER BEFORE ANY FARMER SEES THEM.
USSD screens are capped at 182 characters, so wording is kept short and the
naira sign is written as "N" because many feature phones cannot display it.
"""

from __future__ import annotations

TEXT = {
    "en": {
        "welcome": "Rotawise\n1. English\n2. Hausa",
        "choose_farm": "Choose farm:",
        "summary": "{name}: last {n} seasons {pattern}. Soil tiredness {score}/100.\n1. Best crop next\n2. Compare options\n0. Exit",
        "best": "Plant {crop} next season, then maize. Saves {b0}-{b1} bags urea/ha (N{v0}-N{v1}k). Cuts Striga up to {s}%. Confirm with your extension agent.",
        "best_none": "Keep your current plan this season and ask your extension agent for advice.",
        "compare": "Options (score/100):\n{lines}",
        "no_data": "No satellite data for this farm yet. Please try later.",
        "invalid": "Invalid choice. Please dial again.",
        "bye": "Thank you for using Rotawise.",
        "classes": {
            "cereal_like": "cereal",
            "legume_or_short_cycle": "legume",
            "bare_or_fallow": "bare",
            "unknown": "unclear",
        },
    },
    "ha": {
        "welcome": "Rotawise\n1. English\n2. Hausa",
        "choose_farm": "Zabi gona:",
        "summary": "{name}: damina {n} na karshe {pattern}. Gajiyar kasa {score}/100.\n1. Abin shuka na gaba\n2. Kwatanta zabi\n0. Fita",
        "best": "Shuka {crop} a damina mai zuwa, sannan masara. Ragin urea buhu {b0}-{b1}/hekta (N{v0}-N{v1}k). Rage Striga har {s}%. Tuntubi jamiin gona.",
        "best_none": "Ci gaba da shirin ka na yanzu, ka tuntubi jamiin gona.",
        "compare": "Zabi (maki/100):\n{lines}",
        "no_data": "Babu bayanan tauraron dan adam na wannan gona tukuna.",
        "invalid": "Zabin bai dace ba. Sake bugawa.",
        "bye": "Mun gode da amfani da Rotawise.",
        "classes": {
            "cereal_like": "hatsi",
            "legume_or_short_cycle": "wake/gyada",
            "bare_or_fallow": "babu shuka",
            "unknown": "ba a sani ba",
        },
    },
}


def t(lang: str, key: str) -> str | dict:
    return TEXT.get(lang, TEXT["en"])[key]
