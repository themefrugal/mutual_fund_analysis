"""
STP (Systematic Transfer Plan) analysis.

stp_analysis(source_scheme_code, target_scheme_code, start_date, end_date,
             initial_investment, monthly_transfer)
    → dict with keys: xirr, source_final, target_final, total_final, series
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


def stp_analysis(
    source_scheme_code: str,
    target_scheme_code: str,
    start_date: date,
    end_date: date,
    initial_investment: float = 100000.0,
    monthly_transfer: float = 5000.0,
) -> dict:
    """
    Compute STP analysis.

    Logic mirrors the tab_stp block in app.py:
    - A lump-sum buys units in the *source* fund at the first month-start date.
    - Each month, `monthly_transfer` worth of units are redeemed from source
      and simultaneously invested in the *target* fund (month-start dates, freq='MS').
    - Transfer stops when source fund runs out of units.
    - XIRR = initial outflow vs combined portfolio value at end.

    Returns
    -------
    {
        "xirr": float | None,
        "source_final": float,
        "target_final": float,
        "total_final": float,
        "series": [
            {
                "date": "YYYY-MM-DD",
                "value_src": float,
                "value_tgt": float,
                "total_value": float,
                "src_units_norm": float,
                "tgt_units_norm": float,
            },
            ...
        ]
    }
    """
    if source_scheme_code == target_scheme_code:
        raise ValueError("Source and target scheme codes must be different.")

    df_src_all = get_nav(source_scheme_code)
    df_tgt_all = get_nav(target_scheme_code)

    # Month-start dates (freq='MS') — same as the Streamlit app
    stp_dates = pd.DataFrame(
        pd.date_range(start=start_date, end=end_date, freq="MS"),
        columns=["date"],
    )

    if stp_dates.empty:
        raise ValueError("No monthly dates found in the given date range.")

    df_src_m = df_src_all.merge(stp_dates, on="date").rename(columns={"nav": "nav_src"})
    df_tgt_m = df_tgt_all.merge(stp_dates, on="date").rename(columns={"nav": "nav_tgt"})
    df_stp = df_src_m.merge(df_tgt_m, on="date").reset_index(drop=True)

    if df_stp.empty:
        raise ValueError(
            "No overlapping dates between source and target funds for the selected period."
        )

    # --- Source fund (SWP side) ---
    init_units_src = initial_investment / df_stp["nav_src"].iloc[0]
    df_stp["units_out"] = monthly_transfer / df_stp["nav_src"]
    df_stp["cum_units_out"] = df_stp["units_out"].cumsum().clip(upper=init_units_src)
    df_stp["remaining_units_src"] = (init_units_src - df_stp["cum_units_out"]).clip(lower=0)
    df_stp["value_src"] = df_stp["remaining_units_src"] * df_stp["nav_src"]

    # --- Target fund (SIP side) — only while source still has units ---
    prev_remaining = df_stp["remaining_units_src"].shift(1, fill_value=init_units_src)
    df_stp["active"] = prev_remaining > 0
    df_stp["units_in"] = (monthly_transfer / df_stp["nav_tgt"]).where(df_stp["active"], 0)
    df_stp["cum_units_tgt"] = df_stp["units_in"].cumsum()
    df_stp["value_tgt"] = df_stp["cum_units_tgt"] * df_stp["nav_tgt"]

    # --- Combined ---
    df_stp["total_value"] = df_stp["value_src"] + df_stp["value_tgt"]

    # --- XIRR ---
    df_xirr_stp = pd.DataFrame(
        [
            {"date": df_stp["date"].iloc[0], "amount": initial_investment},
            {"date": df_stp["date"].iloc[-1], "amount": -df_stp["total_value"].iloc[-1]},
        ]
    )
    try:
        xirr_value = _xirr(df_xirr_stp) * 100
        xirr_value = _to_none_if_nan(xirr_value)
    except Exception:
        xirr_value = None

    # --- Normalised unit columns ---
    df_stp["src_units_norm"] = (
        df_stp["remaining_units_src"] / df_stp["remaining_units_src"].iloc[0]
    )
    max_tgt_units = df_stp["cum_units_tgt"].max()
    if max_tgt_units and max_tgt_units > 0:
        df_stp["tgt_units_norm"] = df_stp["cum_units_tgt"] / max_tgt_units
    else:
        df_stp["tgt_units_norm"] = 0.0

    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "value_src": _to_none_if_nan(row["value_src"]),
            "value_tgt": _to_none_if_nan(row["value_tgt"]),
            "total_value": _to_none_if_nan(row["total_value"]),
            "src_units_norm": _to_none_if_nan(row["src_units_norm"]),
            "tgt_units_norm": _to_none_if_nan(row["tgt_units_norm"]),
        }
        for _, row in df_stp.iterrows()
    ]

    last = df_stp.iloc[-1]
    return {
        "xirr": xirr_value,
        "source_final": _to_none_if_nan(last["value_src"]),
        "target_final": _to_none_if_nan(last["value_tgt"]),
        "total_final": _to_none_if_nan(last["total_value"]),
        "series": series,
    }
