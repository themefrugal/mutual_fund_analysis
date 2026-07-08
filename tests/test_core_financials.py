from __future__ import annotations

import datetime as dt

import pandas as pd

from api.core.funds import parse_amfi_latest_nav
from api.core.compare import build_comparison_data, drawdown_long, growth_long, rebased_nav_long, rolling_cagr_long
from api.core.rolling import rolling_sip_xirr
from api.core.sip import sip_analysis
from api.core.stp import stp_analysis
from api.core.swp import swp_analysis


def nav_frame(start: str, end: str, nav: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.date_range(start=start, end=end, freq="D"), "nav": nav})


def test_parse_amfi_latest_nav_uses_scheme_name_column():
    raw = pd.DataFrame(
        [
            ["Scheme Code", "ISIN Div Payout/ ISIN Growth", "ISIN Div Reinvestment", "Scheme Name"],
            ["119551", "INF209KA12Z1", "INF209KA13Z9", "Aditya Birla Sun Life Banking Fund"],
            ["Open Ended Schemes(Debt Scheme)", None, None, None],
        ]
    )

    parsed = parse_amfi_latest_nav(raw)

    assert parsed.to_dict(orient="records") == [
        {
            "schemeCode": "119551",
            "schemeISIN": "INF209KA12Z1",
            "schemeName": "Aditya Birla Sun Life Banking Fund",
        }
    ]


def test_parse_amfi_latest_nav_handles_name_before_isin_columns():
    raw = pd.DataFrame(
        [
            ["119551", "Aditya Birla Sun Life Banking Fund", "INF209KA12Z1", "INF209KA13Z9"],
            ["119552", "INF00XX01150", "INF00XX01184", "-"],
        ]
    )

    parsed = parse_amfi_latest_nav(raw)

    assert parsed.to_dict(orient="records") == [
        {
            "schemeCode": "119551",
            "schemeISIN": "INF209KA12Z1",
            "schemeName": "Aditya Birla Sun Life Banking Fund",
        }
    ]


def test_sip_step_up_affects_units_and_invested_amount(monkeypatch):
    monkeypatch.setattr("api.core.sip.get_nav", lambda scheme_code: nav_frame("2020-01-01", "2021-12-31", 10.0))

    result = sip_analysis(
        "123",
        dt.date(2020, 1, 1),
        dt.date(2021, 12, 31),
        monthly_amount=1000.0,
        step_up_pct=20.0,
    )

    last = result["series"][-1]
    assert round(last["invested_amount"], 2) == 26400.0
    assert round(last["cum_units"], 2) == 2640.0
    assert round(last["current_value"], 2) == 26400.0


def test_swp_caps_withdrawals_at_available_corpus(monkeypatch):
    monkeypatch.setattr("api.core.swp.get_nav", lambda scheme_code: nav_frame("2020-01-01", "2020-06-30", 10.0))

    result = swp_analysis(
        "123",
        dt.date(2020, 1, 1),
        dt.date(2020, 6, 30),
        initial_investment=1000.0,
        monthly_withdrawal=600.0,
    )

    assert result["depleted_on"] is not None
    assert result["series"][-1]["cur_value"] == 0.0
    assert result["series"][-1]["cum_amount"] == 1000.0


def test_stp_partial_transfer_does_not_create_extra_target_value(monkeypatch):
    source_nav = nav_frame("2020-01-01", "2020-03-31", 10.0)
    target_nav = nav_frame("2020-01-01", "2020-03-31", 10.0)

    def fake_get_nav(code: str) -> pd.DataFrame:
        return source_nav if code == "source" else target_nav

    monkeypatch.setattr("api.core.stp.get_nav", fake_get_nav)

    result = stp_analysis(
        "source",
        "target",
        dt.date(2020, 1, 1),
        dt.date(2020, 3, 31),
        initial_investment=1000.0,
        monthly_transfer=600.0,
    )

    assert [row["transfer_amount"] for row in result["series"]] == [600.0, 400.0, 0.0]
    assert result["source_final"] == 0.0
    assert result["target_final"] == 1000.0
    assert result["total_final"] == 1000.0


def test_rolling_sip_returns_empty_when_history_is_too_short():
    df_nav = nav_frame("2020-01-01", "2020-12-31", 10.0)

    result = rolling_sip_xirr(df_nav, window_years=2, monthly_amount=1000.0, step_up_pct=0.0)

    assert result.empty


def test_compare_core_builds_combo_and_shared_frames(monkeypatch):
    df_mfs = pd.DataFrame(
        {
            "schemeCode": ["a", "b"],
            "schemeISIN": ["INF000000001", "INF000000002"],
            "schemeName": ["Fund A", "Fund B"],
        }
    )
    nav_a = pd.DataFrame({"date": pd.date_range("2020-01-01", "2021-12-31", freq="D"), "nav": 10.0})
    nav_b = pd.DataFrame({"date": pd.date_range("2020-01-01", "2021-12-31", freq="D"), "nav": 20.0})

    monkeypatch.setattr("api.core.compare.get_scheme_codes", lambda: df_mfs)
    monkeypatch.setattr("api.core.compare.get_nav", lambda code: nav_a if code == "a" else nav_b)

    comp = build_comparison_data(["a", "b"], combo_weights=[100.0])
    rebased = rebased_nav_long(comp, dt.date(2020, 1, 1))
    drawdown = drawdown_long(rebased)
    cagr = rolling_cagr_long(comp, years=1)
    growth = growth_long(comp, holding_years=1)

    assert comp.plot_names == ["Fund A", "Fund B", "combo"]
    assert comp.nav_wide["combo"].iloc[0] == 20.0
    assert set(rebased["mf"]) == {"Fund A", "Fund B", "combo"}
    assert drawdown["draw_down"].max() == 0.0
    assert set(cagr["mf"]) == {"Fund A", "Fund B", "combo"}
    assert set(growth["mf"]) == {"Fund A", "Fund B", "combo"}
