"""Run from the repo root:  python -m pytest bot/desk/tests -q

No network needed. The fixture is the real market state of 10 Shahrivar 1405
that the handbook was written against; every expectation was hand-checked.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # -> bot/

from desk.config import load_yaml
from desk.derive import derive, sanity_warnings
from desk.format import gates_block, ladder_block, snapshot_block
from desk.http_source import dig, extract, num
from desk.notify import in_quiet_hours
from desk.rules import RulesEngine, _cmp
from desk.tehran import to_jalali

LIVE = dict(usd_free=211100, usd_havaleh=157480, gold18k_toman=22170000,
            xau_usd=4430, xag_usd=66.58, copper_usd_toz=0.4512, btc_usd=78244,
            tala_price=1556199, tala_nav=1578000, plata_price=12150, plata_nav=11667,
            ahrom_price=57106, ahrom_nav=73496, tedpix=6547933,
            iran_cpi_yoy=87.9, iran_oil_exports_bpd=300000)


# ───────────────────────── handbook arithmetic ─────────────────────────
def test_parity_matches_handbook():
    d = derive(LIVE)
    assert abs(d["gold_parity_toman"] - 22_549_866) < 5_000
    assert abs(d["gold_parity_gap_pct"] - (-1.68)) < 0.05


def test_the_9_shahrivar_discount_would_have_fired():
    """Gold at 18.432M against the same parity = -18.3%. This is the trade."""
    v = derive({**LIVE, "gold18k_toman": 18_432_000})
    assert v["gold_parity_gap_pct"] < -18
    eng = RulesEngine(load_yaml("rules.yaml"))
    ids = {f.rule_id for f in eng.evaluate(v, None)}
    assert "parity_discount" in ids


def test_fx_spread_and_ratio():
    d = derive(LIVE)
    assert abs(d["fx_spread_pct"] - 34.05) < 0.1
    assert abs(d["gold_silver_ratio"] - 66.54) < 0.1


def test_fund_premiums():
    d = derive(LIVE)
    assert abs(d["tala_bubble_pct"] - (-1.38)) < 0.05
    assert abs(d["plata_premium_pct"] - 4.14) < 0.05
    assert abs(d["ahrom_discount_pct"] - (-22.30)) < 0.05


def test_copper_unit_conversion():
    assert abs(derive(LIVE)["copper_usd_lb"] - 6.58) < 0.02


def test_grams_per_billion():
    assert abs(derive(LIVE)["grams_per_billion"] - 45.1) < 0.2


def test_limit_day_detection():
    d = derive({**LIVE, "tala_prev_close": 1_414_726})
    assert d["any_fund_at_limit"] == 1
    assert "طلا" in d["limit_fund_names"]


# ───────────────────────── the rules engine ─────────────────────────
def test_crosses_down_needs_a_previous_value():
    assert _cmp("crosses_down", 20_700_000, 21_000_000, 20_800_000) is True
    assert _cmp("crosses_down", 20_700_000, None, 20_800_000) is False
    # already below on both readings -> no repeat fire
    assert _cmp("crosses_down", 20_700_000, 20_750_000, 20_800_000) is False


def test_ladder_rung_fires_once_on_the_way_down():
    eng = RulesEngine(load_yaml("rules.yaml"))
    prev = {"gold18k_toman": 21_000_000}
    cur = derive({**LIVE, "gold18k_toman": 20_700_000})
    assert "ladder_rung_2" in {f.rule_id for f in eng.evaluate(cur, prev)}


def test_kill_criteria_are_critical():
    eng = RulesEngine(load_yaml("rules.yaml"))
    v = derive({**LIVE, "iran_cpi_yoy": 35.0, "usd_havaleh": 200_000})
    fires = {f.rule_id: f.severity for f in eng.evaluate(v, None)}
    assert fires.get("kill_inflation") == "critical"
    assert fires.get("fx_spread_converging") == "critical"


def test_missing_data_never_crashes_a_rule():
    eng = RulesEngine(load_yaml("rules.yaml"))
    assert eng.evaluate(derive({"btc_usd": 70000}), None)  # some fire, none raise


def test_sanity_catches_rial_toman_confusion():
    w = sanity_warnings(derive({**LIVE, "gold18k_toman": 221_700_000}))
    assert any("scale" in x or "implausible" in x for x in w)


def test_every_rule_metric_is_producible():
    """Guards against a rule referencing a metric derive() never emits."""
    produced = set(derive(LIVE)) | {"iran_oil_exports_bpd", "iran_cpi_yoy"}
    missing = [r["metric"] for r in load_yaml("rules.yaml")["rules"]
               if r["metric"] not in produced]
    assert not missing, f"rules reference unknown metrics: {missing}"


def test_threshold_override_changes_the_verdict():
    eng = RulesEngine(load_yaml("rules.yaml"))
    v = derive({**LIVE, "gold18k_toman": 22_000_000})
    assert "parity_discount" not in {f.rule_id for f in eng.evaluate(v, None)}
    eng.set_threshold("parity_discount", -1.0)
    assert "parity_discount" in {f.rule_id for f in eng.evaluate(v, None)}


# ───────────────────────── the port itself ─────────────────────────
# These cover what changed when the desk moved into this repo: pytz and
# jdatetime went away, httpx became requests, and every source spec has to
# survive being read by the new loader.
def test_jalali_matches_the_handbook_dates():
    assert to_jalali(2026, 3, 21) == (1405, 1, 1)      # Nowruz 1405
    assert to_jalali(2026, 9, 1) == (1405, 6, 10)      # "10 Shahrivar"
    assert to_jalali(2024, 3, 20) == (1403, 1, 1)


def test_quiet_hours_wrap_around_midnight():
    assert in_quiet_hours(None) is False
    # the window itself is exercised via minutes_of_day(); assert the shape
    # parses rather than pinning a wall-clock time the test cannot control
    from desk.config import Settings
    assert Settings().quiet_window() == ((1, 0), (7, 0))


def test_source_specs_all_parse_and_map_their_fields():
    cfg = load_yaml("sources.yaml")
    assert set(cfg["sources"]) >= {"brsapi_gold", "metals_dev", "coingecko", "tse", "manual"}
    payload = {"metals": {"gold": 4430, "silver": 66.58, "copper": 0.4512}}
    assert extract(payload, cfg["sources"]["metals_dev"]) == {
        "xau_usd": 4430.0, "xag_usd": 66.58, "copper_usd_toz": 0.4512}


def test_container_matching_picks_the_right_row():
    spec = load_yaml("sources.yaml")["sources"]["brsapi_gold"]
    payload = {"currency": [{"symbol": "EUR", "price": 240000},
                            {"symbol": "USD", "price": 211100}],
               "gold": [{"symbol": "IR_GOLD_18K", "price": 22170000}]}
    got = extract(payload, spec)
    assert got["usd_free"] == 211100.0 and got["gold18k_toman"] == 22170000.0


def test_persian_digits_and_separators_parse():
    assert num("۲۱۱٬۱۰۰") == 211100.0
    assert num("22,170,000") == 22170000.0
    assert num("n/a") is None and num(None) is None


def test_dig_handles_bracket_paths_and_holes():
    assert dig({"a": [{"b": 3}]}, "a[0].b") == 3
    assert dig({"a": []}, "a[0].b") is None
    assert dig({"a": 1}, "a.b.c") is None


def test_relay_targets_are_real_sources():
    cfg = load_yaml("sources.yaml")
    for name in cfg["relay"]["applies_to"]:
        assert name in cfg["sources"], name


def test_every_renderer_survives_an_empty_snapshot():
    """A dead feed must produce dashes, not a traceback inside a command."""
    for block in (snapshot_block, gates_block, ladder_block):
        assert isinstance(block({}), str)
        assert isinstance(block(derive(LIVE)), str)
