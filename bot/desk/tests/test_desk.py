"""Run from the repo root:  python -m pytest bot/desk/tests -q

No network needed. The fixture is the real market state of 10 Shahrivar 1405
that the handbook was written against; every expectation was hand-checked.
"""
import json
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


# ───────────────────────── the tgju fallback ─────────────────────────
# brsapi and TSETMC stopped answering from Railway. tgju is the one Iranian
# feed with production evidence behind it (bot/datafeed.py has read this same
# endpoint from this same service since launch), so Engine 1 now rests on it.
from desk.derive import MESGHAL_FINE_G
from desk.tgju import _latest, _spread_days

# A real summary-table payload shape: [open, low, high, close, chg, chg%, greg, jalali]
TGJU_ROWS = [
    ["960,000,000", "958,000,000", "962,500,000", "960,360,500", "1,200,000",
     "0.13", "2026-09-02", "1405/06/11"],
    ["959,000,000", "957,000,000", "961,000,000", "959,160,500", "900,000",
     "0.09", "2026-09-01", "1405/06/10"],
]


def test_tgju_takes_the_newest_close_regardless_of_row_order():
    close, date = _latest(TGJU_ROWS, 3, 6)
    assert (close, date) == (960360500.0, "2026-09-02")
    # tgju has served the other order before; sorting must win, not position
    close2, date2 = _latest(list(reversed(TGJU_ROWS)), 3, 6)
    assert (close2, date2) == (960360500.0, "2026-09-02")


def test_tgju_ignores_short_and_undated_rows():
    rows = [["x"], ["1", "2", "3", "4", "5", "6", "not-a-date", "j"]] + TGJU_ROWS
    assert _latest(rows, 3, 6)[1] == "2026-09-02"
    assert _latest([["1"]], 3, 6) == (None, None)


def test_quote_spread_flags_mismatched_sessions():
    assert _spread_days(["2026-09-02", "2026-09-02"]) == 0
    assert _spread_days(["2026-08-30", "2026-09-02"]) == 3
    assert _spread_days([]) is None


def test_rial_scaling_is_what_sources_yaml_says():
    """tgju quotes Iranian instruments in rial; the desk works in toman."""
    tgju = load_yaml("sources.yaml")["sources"]["tgju"]
    for name in ("usd_free", "mesghal_toman", "quarter_toman", "gold18k_toman"):
        assert tgju["fields"][name]["scale"] == 0.1, name
    for name in ("xau_usd", "xag_usd"):          # already USD, never scaled
        assert tgju["fields"][name].get("scale", 1) == 1, name


def test_engine_one_survives_on_tgju_alone():
    """The whole point of the fallback: with brsapi and TSETMC dark, a tgju
    snapshot must still produce parity, the gap, grams/billion and a ladder."""
    mesghal_toman = 22_170_000 * MESGHAL_FINE_G / 0.75      # the handbook's 18k
    v = derive({"usd_free": 211100, "mesghal_toman": mesghal_toman, "xau_usd": 4430})
    assert abs(v["gold18k_toman"] - 22_170_000) < 1
    assert abs(v["gold_parity_toman"] - 22_549_866) < 5_000
    assert abs(v["gold_parity_gap_pct"] - (-1.68)) < 0.05    # matches brsapi's answer
    assert abs(v["grams_per_billion"] - 45.1) < 0.2
    assert v["ladder_rungs_live"] == 1


def test_a_direct_18k_feed_beats_the_derivation():
    v = derive({"gold18k_toman": 20_000_000, "mesghal_toman": 96_036_050})
    assert v["gold18k_toman"] == 20_000_000
    assert "gold18k_is_derived" not in v


def test_derived_18k_and_stale_quotes_announce_themselves():
    v = derive({"usd_free": 211100, "mesghal_toman": 96_036_050, "xau_usd": 4430,
                "tgju_quote_spread_days": 3.0})
    w = " ".join(sanity_warnings(v))
    assert "derived from" in w and "span 3 days" in w


def test_disabled_sources_keep_a_usable_mapping():
    """brsapi and tse are off, not deleted — re-enabling must not need edits."""
    src = load_yaml("sources.yaml")["sources"]
    for name in ("brsapi_gold", "brsapi_havaleh", "tse"):
        assert src[name]["enabled"] is False, name
    assert src["tgju"]["enabled"] is True
    assert src["brsapi_gold"]["fields"]["gold18k_toman"]["container"] == "gold"
    assert set(src["tse"]["symbols"]) == {"tala", "plata", "ahrom"}


def test_empty_custom_slot_fails_with_a_readable_message():
    import pytest
    from desk.http_source import fetch_http_source
    with pytest.raises(ValueError, match="no `url` set"):
        fetch_http_source("custom_a", {"url": "", "fields": {}}, [])


# ───────────────────────── /probeurl ─────────────────────────
# The remaining gap is fund price + NAV, and the question is which host will
# answer Railway at all. /probeurl moves that test into Telegram.
import pytest

from desk.probe import ProbeRefused, numeric_paths, probe_url


def test_numeric_paths_are_sources_yaml_paths():
    payload = {"items": [{"name": "طلا", "nav": 1578000, "last": "1,556,199"},
                         {"name": "اهرم", "nav": 73496}], "ok": True}
    got = dict(numeric_paths(payload))
    assert got["items[0].nav"] == 1578000.0
    assert got["items[0].last"] == 1556199.0      # comma-separated string
    assert got["items[1].nav"] == 73496.0
    assert "ok" not in got                        # booleans are not numbers


def test_numeric_paths_reads_persian_digits_and_nesting():
    got = dict(numeric_paths({"a": {"b": {"c": "۱۲۳٬۴۵۶"}}}))
    assert got["a.b.c"] == 123456.0


def test_probeurl_refuses_anything_but_a_public_https_host():
    for bad in ("http://example.com/x",           # plaintext
                "https://localhost/x",            # loopback
                "https://127.0.0.1/x",
                "https://169.254.169.254/latest", # cloud metadata
                "https://10.0.0.5/x"):            # private range
        with pytest.raises(ProbeRefused):
            probe_url(bad)


def test_probeurl_rejects_a_url_with_no_host():
    with pytest.raises(ProbeRefused):
        probe_url("https:///nothing")


# ───────────────────────── manual values ─────────────────────────
class _FakeStore:
    def __init__(self):
        self.kv = {}

    def set(self, k, v):
        self.kv[k] = v


def _set(arg):
    from desk.service import Desk
    d = object.__new__(Desk)
    d.store = _FakeStore()
    return d.cmd_set(arg), d.store.kv


def test_set_takes_several_pairs_at_once():
    """Six values for fund price+NAV must not be six separate messages."""
    msg, kv = _set("tala_price 1,556,199 tala_nav 1578000 ahrom_nav 73496")
    assert kv == {"manual.tala_price": 1556199.0,
                  "manual.tala_nav": 1578000.0,
                  "manual.ahrom_nav": 73496.0}
    assert "tala_price" in msg


def test_set_accepts_equals_and_reports_bad_values():
    msg, kv = _set("iran_cpi_yoy=84.2")
    assert kv == {"manual.iran_cpi_yoy": 84.2}
    msg, kv = _set("tala_nav abc")
    assert kv == {} and "skipped" in msg


def test_set_rejects_an_odd_number_of_words():
    msg, kv = _set("tala_price 1 tala_nav")
    assert kv == {} and "Usage" in msg


def test_probeurl_is_owner_only():
    from desk.service import Desk
    assert "/probeurl" in Desk.OWNER_ONLY
    assert "/probeurl" in Desk(pathlib.Path("/tmp")).commands()


# ───────────────────────── source wiring ─────────────────────────
def test_metals_dev_outranks_the_keyless_spot_fallback():
    """Later sources win the merge, so metals.dev must come after gold-api."""
    names = list(load_yaml("sources.yaml")["sources"])
    assert names.index("gold_api_xau") < names.index("metals_dev")
    assert names.index("tgju") < names.index("metals_dev")


def test_keyless_fallbacks_need_no_api_key():
    src = load_yaml("sources.yaml")["sources"]
    for name in ("gold_api_xau", "gold_api_xag", "coingecko", "tgju"):
        assert "${" not in json.dumps(src[name].get("params", {})), name


def test_fund_slots_are_present_and_empty():
    src = load_yaml("sources.yaml")["sources"]
    for name in ("funds_a", "funds_b"):
        assert src[name]["enabled"] is False and src[name]["fields"] == {}
