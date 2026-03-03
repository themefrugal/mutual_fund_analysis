"""
SWP (Systematic Withdrawal Plan) analysis.

swp_analysis(scheme_code, start_date, end_date, initial_investment, monthly_withdrawal)
    → dict with keys: xirr, series
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from pyxirr import xirr as _xirr

from .nav import get_nav


def _to_none_if_nan(val):
    """Return None if val is NaN/inf, else the Python float."""
    try:
        if val is None or np.isnan(val) or np.isinf(val):
            return None
    except (TypeError, ValueError):
        pass
    return float(val)


def swp_analysis(
    scheme_code: str,
    start_date: date,
    end_date: date,
    initial_investment: float = 100000.0,
    monthly_withdrawal: float = 5000.0,
) -> dict:
    """
    Compute SWP analysis.

    Logic mirrors the tab_swp block in app.py:
    - A lump-sum investment buys units at the first available month-end NAV.
    - Each month a fixed amount is redeemed (units sold = withdrawal / NAV).
    - XIRR = initial outflow + monthly inflows + remaining corpus at end.

    Returns
    -------
    {
        "xirr": float | None,
        "series": [
            {
                "date": "YYYY-MM-DD",
                "inv_value": float,
                "cur_value": float,
                "cum_amount": float,
                "total": float,
            },
            ...
        ]
    }
    The series is at monthly frequency (one row per withdrawal date).
    """
    df_navs = get_nav(scheme_code)

    monthly_dates = pd.DataFrame(
        pd.date_range(start=start_date, end=end_date, freq="M"),
        columns=["date"],
    )

    if monthly_dates.empty:
        raise ValueError("No monthly dates found in the given date range.")

    df_cf = df_navs.merge(monthly_dates, on="date")
    if df_cf.empty:
        raise ValueError(
            "No NAV data available for the selected fund in the given date range."
        )

    df_cf = df_cf.reset_index(drop=True)

    # Use the NAV on the first date to determine initial units
    init_nav = df_cf.iloc[0]["nav"]
    init_units = initial_investment / init_nav

    df_cf["inv_value"] = initial_investment
    df_cf["amount"] = monthly_withdrawal
    df_cf["units"] = df_cf["amount"] / df_cf["nav"]
    df_cf["cum_units"] = df_cf["units"].cumsum()
    df_cf["cur_units"] = (init_units - df_cf["cum_units"]).clip(lower=0)
    df_cf["cur_value"] = df_cf["cur_units"] * df_cf["nav"]
    df_cf["cum_amount"] = df_cf["amount"].cumsum()
    df_cf["total"] = df_cf["cur_value"] + df_cf["cum_amount"]

    # XIRR: initial investment out, monthly withdrawals in, remaining corpus in at end
    df_investment = df_cf[["date", "inv_value"]].head(1).copy()
    df_investment.columns = ["date", "amount"]

    df_redemption = df_cf[["date", "amount"]].copy()
    df_remaining = df_cf.iloc[[-1]][["date", "cur_value"]].copy()
    df_remaining.columns = ["date", "amount"]

    df_redemption = pd.concat([df_redemption, df_remaining], ignore_index=True)
    df_redemption["amount"] = -df_redemption["amount"]  # inflows for investor

    df_irr = pd.concat([df_investment, df_redemption], ignore_index=True)

    try:
        xirr_value = _xirr(df_irr[["date", "amount"]]) * 100
        xirr_value = _to_none_if_nan(xirr_value)
    except Exception:
        xirr_value = None

    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "inv_value": _to_none_if_nan(row["inv_value"]),
            "cur_value": _to_none_if_nan(row["cur_value"]),
            "cum_amount": _to_none_if_nan(row["cum_amount"]),
            "total": _to_none_if_nan(row["total"]),
        }
        for _, row in df_cf.iterrows()
    ]

    return {"xirr": xirr_value, "series": series}
