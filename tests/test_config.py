from datetime import date, time

import pytest

from codomo_alerts import catalog
from codomo_alerts.config import MIN_INTERVAL, ConfigError, build, load


def test_defaults_watch_everything():
    cfg = build({}, {})
    assert cfg.search.cities == []
    assert cfg.search.interest is True
    assert cfg.schedule.preset == "normal"
    assert cfg.dashboard.port == 8080
    assert cfg.base_url == "https://codomo.eu"
    assert cfg.data_dir.name == "codomo-alerts"
    assert cfg.search.summary() == "All cities in the Netherlands"


def test_names_slugs_and_aliases():
    s = build({"search": {"cities": ["Den Haag", "eindhoven", "'s-Hertogenbosch", "capelle-aan-den-ijssel"]}}, {}).search
    assert s.cities == ["The Hague", "Eindhoven", "Den Bosch", "Capelle aan den IJssel"]
    assert build({"search": {"cities": "den-haag"}}, {}).search.cities == ["The Hague"]


def test_bedrooms_ranges():
    assert catalog.bedrooms("2+")[:3] == [2, 3, 4]
    assert catalog.bedrooms("studio-1") == [0, 1]
    assert catalog.bedrooms("2 bedrooms") == [2]
    assert catalog.bedrooms("loft") == [0]
    s = build({"search": {"bedrooms": ["studio", "2-3"]}}, {}).search
    assert s.bedrooms == [0, 2, 3]


def test_contract_words():
    assert build({"search": {"contract": "long"}}, {}).search.contracts == ["indefinite", "2y", "1y"]
    assert build({"search": {"contract": ["short stay"]}}, {}).search.contracts == ["short"]
    assert catalog.contract_ok("6m", ["short"]) and catalog.contract_ok("3m", ["short"])
    assert not catalog.contract_ok("indefinite", ["short"]) and not catalog.contract_ok(None, ["long"])
    assert catalog.contract_ok(None, [])


def test_furnishing_and_persons():
    s = build({"search": {"furnishing": ["gestoffeerd", "Fully furnished"], "persons": "couple"}}, {}).search
    assert s.furnishing == ["semi-furnished", "fully-furnished"] and s.persons == 2


def test_env_wins_over_file():
    raw = {"search": {"cities": ["Rotterdam"], "price_max": 2000}}
    env = {"CODOMO_CITIES": "Amsterdam, Utrecht", "CODOMO_PRICE_MAX": "€1,600", "CODOMO_INTEREST": "no"}
    s = build(raw, env).search
    assert s.cities == ["Amsterdam", "Utrecht"]
    assert s.price_max == 1600
    assert s.interest is False


def test_an_old_lottery_setting_still_works_with_a_warning():
    cfg = build({"search": {"lottery": False}}, {})
    assert cfg.search.interest is False and "interest" in cfg.warnings[0]


def test_notify_urls_split_on_space_not_comma():
    env = {"CODOMO_NOTIFY": "tgram://a/b  mailto://u:p@x.com?to=a@x.com,b@x.com"}
    assert build({}, env).notify.urls == ["tgram://a/b", "mailto://u:p@x.com?to=a@x.com,b@x.com"]


def test_notify_file(tmp_path):
    secret = tmp_path / "urls"
    secret.write_text("ntfy://topic\n")
    assert build({}, {"CODOMO_NOTIFY_FILE": str(secret)}).notify.urls == ["ntfy://topic"]


@pytest.mark.parametrize("raw, message", [
    ({"search": {"cities": ["Atlantis"]}}, "unknown value 'Atlantis'"),
    ({"search": {"bedrooms": ["12"]}}, "bedrooms"),
    ({"search": {"occupants": ["couple"]}}, "persons"),
    ({"search": {"persons": "many"}}, "persons"),
    ({"search": {"price_min": 2000, "price_max": 1000}}, "higher than"),
    ({"search": {"cities": ["Utrecht"], "exclude_cities": ["Utrecht"]}}, "both"),
    ({"search": {"move_in_before": "next week"}}, "YYYY-MM-DD"),
    ({"schedule": {"preset": "turbo"}}, "preset"),
    ({"general": {"base_url": "http://example.com"}}, "https"),
    ({"notify": {"quiet_hours": "late"}}, "range"),
    ({"search": "Eindhoven"}, "table"),
])
def test_errors_are_readable(raw, message):
    with pytest.raises(ConfigError, match=message):
        build(raw, {})


def test_too_fast_is_slowed_down_with_a_warning():
    cfg = build({"schedule": {"hot_seconds": 5}}, {})
    assert cfg.schedule.hot == MIN_INTERVAL
    assert cfg.warnings


def test_presets():
    cfg = build({"schedule": {"preset": "relaxed", "interest_seconds": 900}}, {})
    assert (cfg.schedule.hot, cfg.schedule.day, cfg.schedule.night) == (300, 600, 1800)
    assert cfg.schedule.interest == 900


def test_quiet_hours_and_dates():
    cfg = build({"notify": {"quiet_hours": "23:00-07:30"}, "search": {"move_in_before": "2027-02-01"}}, {})
    assert cfg.notify.quiet_hours == (time(23, 0), time(7, 30))
    assert cfg.search.move_in_before == date(2027, 2, 1)


def test_summary_reads_well():
    s = build({"search": {"cities": ["Eindhoven", "Rotterdam"], "bedrooms": ["studio"],
                          "price_max": 1500, "contract": "long", "persons": 2}}, {}).search
    assert s.summary() == "Eindhoven, Rotterdam · Studio · up to €1,500 · Long stay · for 2 people"
    assert "2+ bedrooms" in build({"search": {"bedrooms": "2+"}}, {}).search.summary()


def test_fingerprint_ignores_interest_toggle():
    a = build({"search": {"cities": ["Eindhoven"], "interest": True}}, {}).search
    b = build({"search": {"cities": ["Eindhoven"], "interest": False}}, {}).search
    c = build({"search": {"cities": ["Utrecht"]}}, {}).search
    assert a.fingerprint() == b.fingerprint() != c.fingerprint()


def test_load_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.toml").write_text('[search]\ncities = ["Leiden"]\n')
    cfg = load(env={})
    assert cfg.search.cities == ["Leiden"]
    assert cfg.source.name == "config.toml"


def test_missing_and_broken_files(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load(str(tmp_path / "nope.toml"), env={})
    bad = tmp_path / "bad.toml"
    bad.write_text("[search\n")
    with pytest.raises(ConfigError):
        load(str(bad), env={})
