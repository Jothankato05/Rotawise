from rotawise.engine import DataNotIngested, analyze
from rotawise.engine.climate import water_fit
from rotawise.engine.phenology import current_rotation_label, field_memory
from rotawise.engine.rotations import Prices, economics, zone_for
from rotawise.engine.soil import theil_sen_slope

from .conftest import season_curve


def test_cereal_season_classified(cfg):
    s = field_memory(season_curve(2020, 0.22, 0.75, 150, 130), cfg["phenology"])
    assert s[0].season_class == "cereal_like"
    assert 0 < s[0].confidence <= cfg["phenology"]["max_confidence"]


def test_legume_season_classified(cfg):
    s = field_memory(season_curve(2020, 0.22, 0.48, 180, 75), cfg["phenology"])
    assert s[0].season_class == "legume_or_short_cycle"


def test_bare_season_classified(cfg):
    s = field_memory(season_curve(2020, 0.20, 0.27, 180, 60), cfg["phenology"])
    assert s[0].season_class == "bare_or_fallow"
    assert s[0].bare_months  # bare months reported


def test_cloudy_season_is_unknown(cfg):
    obs = season_curve(2020, 0.22, 0.75, 150, 130, step=60)
    s = field_memory(obs, cfg["phenology"])
    assert s[0].season_class == "unknown"
    assert s[0].confidence == 0.0


def test_bad_values_are_ignored(cfg):
    obs = season_curve(2020, 0.22, 0.75, 150, 130) + [{"date": "2020-07-01", "ndvi": 5.0}, {"date": "2020-07-02", "ndvi": None}]
    assert field_memory(obs, cfg["phenology"])[0].season_class == "cereal_like"


def test_current_rotation_detects_cereal_run(cfg):
    obs = []
    for y in range(2020, 2024):
        obs += season_curve(y, 0.22, 0.75, 150, 130)
    cur = current_rotation_label(field_memory(obs, cfg["phenology"]))
    assert cur["id"] == "continuous_cereal"
    assert cur["cereal_run"] == 4


def test_theil_sen_robust_to_outlier():
    pts = [(2018, 0.70), (2019, 0.68), (2020, 0.10), (2021, 0.64), (2022, 0.62)]
    assert -0.03 < theil_sen_slope(pts) < -0.01


def test_economics_soybean_northern_guinea(cfg):
    e = economics(cfg["crops"]["soybean"], "northern_guinea_savanna", Prices(50000, 40000, 1.8), 0.5, cfg)
    # 55 kg N / 0.46 = 119.6 kg urea = 2.4 bags x N50,000 = N119,565
    assert e["per_ha"]["urea_bags_saved"][1] == 2.4
    assert 119_000 <= e["per_ha"]["fertilizer_saved_ngn"][1] <= 120_000
    assert e["plot"]["total_value_ngn"][1] > 0


def test_zone_by_latitude(cfg):
    assert zone_for(12.1, cfg)["id"] == "sudan_savanna"
    assert zone_for(11.0, cfg)["id"] == "northern_guinea_savanna"
    assert zone_for(8.9, cfg)["id"] == "southern_guinea_savanna"


def test_water_fit_bounds():
    assert water_fit(900, [500, 800], 0.9) == 1.0
    assert water_fit(400, [500, 800], 0.9) == 0.0
    assert 0 < water_fit(600, [500, 800], 0.9) < 1
    assert water_fit(None, [500, 800], 0.9) is None


def test_full_analysis(data_dir):
    r = analyze("101")
    assert r["field_memory"]["current"]["id"] == "continuous_cereal"
    assert r["soil"]["fatigue"]["score"] >= 60
    opts = r["rotations"]["options"]
    assert opts[0]["is_current"] and len(opts) >= 4  # current plus at least three alternatives
    assert r["rotations"]["recommended"] != opts[0]["id"]
    best = next(o for o in opts if o["id"] == r["rotations"]["recommended"])
    assert best["score"] > opts[0]["score"]
    for o in opts:  # every card carries the challenge's required explanation fields
        assert o["why"] and o["evidence"] and "information_gaps" in o and "risks_for_local_review" in o
    assert r["climate"]["projections"]["ssp245_2040s"]["rain_change_pct"] == -5.0


def test_missing_data_raises(data_dir):
    import pytest
    with pytest.raises(DataNotIngested):
        analyze("102")


def test_half_observed_season_is_unknown(cfg):
    obs = [o for o in season_curve(2020, 0.22, 0.75, 150, 130) if o["date"] >= "2020-08-01"]
    assert field_memory(obs, cfg["phenology"])[0].season_class == "unknown"


def test_rain_outlier_years_are_excluded():
    from rotawise.engine.climate import summarize
    obs = [{"year": y, "season_rain_mm": v} for y, v in zip(range(2016, 2022), [900, 950, 4200, 1000, 980, 300], strict=True)]
    s = summarize({"observed": obs})
    assert s["excluded_years"] == [2018, 2021]
    assert s["observed"]["season_rain_mm_median"] == 965


def test_hausa_messages_cover_every_key():
    from rotawise.messages import MSG
    assert set(MSG["en"]) == set(MSG["ha"])


def test_hausa_explanations_are_translated():
    from rotawise.engine import analyze
    from rotawise.messages import MSG
    r = analyze("101", lang="ha")
    english = set(MSG["en"].values())
    texts = [t for o in r["rotations"]["options"] for t in o["why"] + o["information_gaps"] + o["risks_for_local_review"]]
    texts += [d["text"] for d in r["soil"]["fatigue"]["drivers"]] + [r["rotations"]["disclaimer"], r["rotations"]["zone"]["label"]]
    assert texts and not any(t in english for t in texts)
