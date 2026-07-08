"""
SIP (Systematic Investment Plan) analysis.

sip_analysis(scheme_code, start_date, end_date, monthly_amount, step_up_pct)
    → dict with keys: xirr, series
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from pyxirr import xirr as _xirr

from .common import clean_float, monthly_dates, validate_positive
from .nav import get_nav


def sip_analysis(
    scheme_code: str,
    start_date: date,
    end_date: date,
    monthly_amount: float = 1000.0,
    step_up_pct: float = 5.0,
) -> dict:
    """
    Compute SIP (with optional annual step-up) analysis.

    Logic mirrors the tab_sip block in app.py:
    - Monthly investment on month-end dates (pandas freq='M').
    - Units purchased = amount / NAV on that date.
    - Step-up: every 12 months the monthly amount increases by step_up_pct %.
    - XIRR is computed from the investment cash-flows + final redemption.

    Returns
    -------
    {
        "xirr": float | None,
        "series": [
            {
                "date": "YYYY-MM-DD",
                "invested_amount": float,
                "current_value": float,
                "cum_units": float,
            },
            ...
        ]
    }
    The series is at daily frequency (forward-filled between SIP dates).
    """
    validate_positive(monthly_amount, "Monthly SIP amount")
    if step_up_pct < 0:
        raise ValueError("Annual step-up must be zero or positive.")

    df_navs = get_nav(scheme_code)

    sip_dates = monthly_dates(start_date, end_date, "ME")

    # Merge with available NAVs
    df_cf = df_navs.merge(sip_dates, on="date")
    if df_cf.empty:
        raise ValueError(
            "No NAV data available for the selected fund in the given date range."
        )

    # Apply step-up: every 12 months the base amount grows by step_up_pct %
    df_cf = df_cf.reset_index(drop=True)
    multiplier = (1.0 + step_up_pct / 100.0) ** (df_cf.index // 12)
    df_cf["amount"] = monthly_amount * multiplier

    df_cf["units"] = df_cf["amount"] / df_cf["nav"]
    df_cf["cum_units"] = df_cf["units"].cumsum()
    df_cf["inv_amount"] = df_cf["amount"].cumsum()

    # XIRR cash-flows: outflows = monthly investments, inflow = final redemption
    final_nav = df_cf.iloc[-1]["nav"]
    final_units = df_cf["units"].sum()
    final_value = final_units * final_nav

    df_investment = df_cf[["date", "amount"]].copy()
    df_redemption = pd.DataFrame(
        [{"date": df_cf.iloc[-1]["date"], "amount": -final_value}]
    )
    df_irr = pd.concat([df_investment, df_redemption], ignore_index=True)

    try:
        xirr_value = clean_float(_xirr(df_irr[["date", "amount"]]) * 100)
    except Exception:
        xirr_value = None

    # Build daily series (forward-fill cum_units and inv_amount between SIP dates)
    daily_dates = pd.DataFrame(
        pd.date_range(start=df_cf["date"].min(), end=df_cf["date"].max(), freq="D"),
        columns=["date"],
    )
    daily_navs = df_navs.merge(daily_dates, on="date")

    # Drop nav column from df_cf before merge to avoid collision
    df_cf_slim = df_cf.drop(columns=["nav"])
    df_daily = df_cf_slim.merge(daily_navs, on="date", how="right").sort_values("date")
    df_daily = df_daily.ffill()
    df_daily["current_value"] = df_daily["cum_units"] * df_daily["nav"]

    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "invested_amount": clean_float(row["inv_amount"]),
            "current_value": clean_float(row["current_value"]),
            "cum_units": clean_float(row["cum_units"]),
        }
        for _, row in df_daily.iterrows()
    ]

    return {"xirr": xirr_value, "series": series}
