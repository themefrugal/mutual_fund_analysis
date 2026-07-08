"""
SWP (Systematic Withdrawal Plan) analysis.

swp_analysis(scheme_code, start_date, end_date, initial_investment, monthly_withdrawal)
    → dict with keys: xirr, series
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from pyxirr import xirr as _xirr

from .common import clean_float, monthly_dates, validate_positive
from .nav import get_nav


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
    validate_positive(initial_investment, "Initial investment")
    validate_positive(monthly_withdrawal, "Monthly withdrawal")

    df_navs = get_nav(scheme_code)
    swp_dates = monthly_dates(start_date, end_date, "ME")
    df_cf = df_navs.merge(swp_dates, on="date")
    if df_cf.empty:
        raise ValueError(
            "No NAV data available for the selected fund in the given date range."
        )

    df_cf = df_cf.reset_index(drop=True)

    remaining_units = initial_investment / df_cf.iloc[0]["nav"]
    rows: list[dict] = []
    cum_amount = 0.0
    depleted_on = None
    for _, row in df_cf.iterrows():
        nav = float(row["nav"])
        available_value = remaining_units * nav
        actual_withdrawal = min(float(monthly_withdrawal), available_value)
        units_out = actual_withdrawal / nav if nav > 0 else 0.0
        remaining_units = max(remaining_units - units_out, 0.0)
        cum_amount += actual_withdrawal
        cur_value = remaining_units * nav
        if depleted_on is None and remaining_units <= 1e-12:
            depleted_on = row["date"]
        rows.append(
            {
                "date": row["date"],
                "nav": nav,
                "inv_value": float(initial_investment),
                "amount": actual_withdrawal,
                "cur_units": remaining_units,
                "cur_value": cur_value,
                "cum_amount": cum_amount,
                "total": cur_value + cum_amount,
            }
        )
        if remaining_units <= 1e-12:
            remaining_units = 0.0

    df_cf = pd.DataFrame(rows)

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
        xirr_value = clean_float(_xirr(df_irr[["date", "amount"]]) * 100)
    except Exception:
        xirr_value = None

    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "inv_value": clean_float(row["inv_value"]),
            "cur_value": clean_float(row["cur_value"]),
            "cum_amount": clean_float(row["cum_amount"]),
            "total": clean_float(row["total"]),
            "withdrawal": clean_float(row["amount"]),
        }
        for _, row in df_cf.iterrows()
    ]

    return {
        "xirr": xirr_value,
        "series": series,
        "depleted_on": depleted_on.strftime("%Y-%m-%d") if depleted_on is not None else None,
    }
