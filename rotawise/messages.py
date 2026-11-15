"""Explanation text shown on the dashboard, in English and Hausa.

HAUSA STRINGS MUST BE CHECKED BY A NATIVE SPEAKER BEFORE ANY FARMER SEES THEM.
Every sentence the engine produces comes from a template here, so a reviewer
only has to read this one file.
"""

from __future__ import annotations

MSG: dict[str, dict[str, str]] = {
    "en": {
        # rotation cards
        "why_current": "This is what the satellite record suggests the plot has been doing: {pattern}.",
        "why_current_none": "not enough clear seasons",
        "why_cereal_run": "{n} cereal-like seasons in a row keeps drawing down nitrogen and lets Striga seed build up in the soil.",
        "why_legume": "{crop} adds nitrogen for the next cereal crop and breaks the Striga cycle.",
        "why_fatigue": "Soil fatigue on this plot is {score}/100, so a legume break is worth more here than on a rested field.",
        "why_water": "Projected 2040s season rain of about {mm} mm gives a water fit of {fit} for the weakest crop in this rotation.",
        "gap_confidence": "Season history confidence is only {pct}; confirm past crops with the farmer.",
        "gap_no_rain": "No rainfall record ingested for this plot yet.",
        "gap_legume_price": "Legume grain sale price is not yet in the model; only fertilizer saving and maize gain are counted.",
        "gap_coords": "Plot coordinates are approximate and have not been checked against a real field boundary.",
        "risk_sudan": "In the drier Sudan savanna, published nitrogen gains from legumes are small (6 to 14 kg N/ha).",
        "risk_phosphorus": "Legumes need enough phosphorus to fix nitrogen; check soil P and seed inoculation locally.",
        "risk_striga": "One season of rotation may not cut Striga where infestation is very heavy; plan two seasons.",
        "risk_seed": "Check seed availability and a buyer for the legume harvest before committing.",
        "risk_water": "{crop} may be short of water in drier years by the 2040s.",
        "risk_heat": "More very hot days are projected; heat-sensitive maize may need adapted varieties or earlier planting.",
        "risk_same_cereal": "Continuing the same cereal risks further yield decline and rising fertilizer needs.",
        "disclaimer": "Rotawise supports farmer and extension agent judgment. It does not replace on-farm advice.",
        # soil fatigue
        "drv_cereal_run": "{n} cereal-like season(s) in a row on this plot",
        "drv_trend": "Peak greenness changed by about {pct} over {n} cropped seasons",
        "drv_oc": "Soil organic carbon {v} g/kg (low below {low})",
        "drv_n": "Total nitrogen {v} g/kg (low below {low})",
        "drv_ph": "Soil pH {v} (comfortable range {lo} to {hi})",
        "gap_trend": "Fewer than 4 cropped seasons with clear imagery, so no productivity trend.",
        "gap_soil": "No soil data for this plot yet.",
        "level_high": "High",
        "level_moderate": "Moderate",
        "level_low": "Low",
        # season classes used inside sentences
        "cls_cereal_like": "cereal like",
        "cls_legume_or_short_cycle": "legume or short cycle",
        "cls_bare_or_fallow": "bare or fallow",
        "cls_unknown": "unclear",
        # zones
        "zone_sudan_savanna": "Sudan savanna (drier north)",
        "zone_northern_guinea_savanna": "Northern Guinea savanna",
        "zone_southern_guinea_savanna": "Southern Guinea savanna",
    },
    "ha": {
        "why_current": "Abin da bayanan tauraron dan adam ke nuna gonar ta yi kenan: {pattern}.",
        "why_current_none": "babu isassun damina masu haske",
        "why_cereal_run": "Damina {n} a jere ana shuka hatsi yana rage sinadarin nitrogen a kasa kuma yana barin irin Striga (makasa) ya taru.",
        "why_legume": "{crop} yana kara nitrogen ga hatsin da za a shuka gaba kuma yana katse zagayen Striga.",
        "why_fatigue": "Gajiyar kasar wannan gona ta kai {score}/100, don haka hutun da wake ko gyada ke bayarwa ya fi amfani a nan.",
        "why_water": "Ruwan damina da ake hasashe a shekarun 2040 kusan {mm} mm ne, wanda ya isa {fit} na bukatar amfanin da ya fi rauni a wannan jeri.",
        "gap_confidence": "Tabbacin tarihin damina {pct} ne kawai; a tabbatar da amfanin da aka shuka a baya tare da manomi.",
        "gap_no_rain": "Babu bayanan ruwan sama na wannan gona tukuna.",
        "gap_legume_price": "Ba a saka farashin sayar da wake ko gyada a lissafi ba tukuna; ragin taki da karin masara kawai aka kirga.",
        "gap_coords": "Wurin gonar na kusan-kusa ne, ba a duba iyakar gona ta gaskiya ba.",
        "risk_sudan": "A yankin Sudan savanna mai karancin ruwa, nitrogen da wake ko gyada ke karawa kadan ne (kilo 6 zuwa 14 a hekta).",
        "risk_phosphorus": "Wake da gyada suna bukatar isasshen phosphorus kafin su kara nitrogen; a duba kasa da maganin iri a gida.",
        "risk_striga": "Damina daya na sauya amfani bazai kawar da Striga ba inda ta yi yawa sosai; a shirya damina biyu.",
        "risk_seed": "A tabbatar da samun iri da mai sayen amfanin kafin a fara.",
        "risk_water": "{crop} zai iya rasa isasshen ruwa a shekarun fari nan da 2040.",
        "risk_heat": "Ana hasashen karin kwanakin zafi sosai; masara na iya bukatar irin da ke jure zafi ko shuka da wuri.",
        "risk_same_cereal": "Ci gaba da shuka hatsi iri daya na iya kara rage amfani da kuma kara bukatar taki.",
        "disclaimer": "Rotawise na taimaka wa manomi da jamiin gona su yanke shawara. Ba ya maye gurbin shawarar da ake bayarwa a gona.",
        "drv_cereal_run": "Damina {n} a jere da hatsi a wannan gona",
        "drv_trend": "Koren ganye a kololuwa ya canza da kusan {pct} cikin damina {n} da aka shuka",
        "drv_oc": "Sinadarin carbon a kasa {v} g/kg (ya yi kasa idan bai kai {low} ba)",
        "drv_n": "Nitrogen a kasa {v} g/kg (ya yi kasa idan bai kai {low} ba)",
        "drv_ph": "pH na kasa {v} (daidai tsakanin {lo} zuwa {hi})",
        "gap_trend": "Damina masu haske da aka shuka ba su kai 4 ba, don haka babu yanayin amfani.",
        "gap_soil": "Babu bayanan kasa na wannan gona tukuna.",
        "level_high": "Mai yawa",
        "level_moderate": "Matsakaici",
        "level_low": "Kadan",
        "cls_cereal_like": "hatsi",
        "cls_legume_or_short_cycle": "wake ko gyada",
        "cls_bare_or_fallow": "babu shuka",
        "cls_unknown": "ba a sani ba",
        "zone_sudan_savanna": "Sudan savanna (arewa mai karancin ruwa)",
        "zone_northern_guinea_savanna": "Guinea savanna ta arewa",
        "zone_southern_guinea_savanna": "Guinea savanna ta kudu",
    },
}


def m(lang: str, key: str, **kw: object) -> str:
    table = MSG.get(lang, MSG["en"])
    template = table.get(key, MSG["en"][key])
    return template.format(**kw) if kw else template
