"""
STP (Systematic Transfer Plan) analysis.

stp_analysis(source_scheme_code, target_scheme_code, start_date, end_date,
             initial_investment, monthly_transfer)
    → dict with keys: xirr, source_final, target_final, total_final, series
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from pyxirr import xirr as _xirr

from .common import clean_float, monthly_dates, validate_positive
from .nav import get_nav


def stp_analysis(
    source_scheme_code: str,
    target_scheme_code: str,
    start_date: date,
    end_date: date,
    initial_investment: float = 100000.0,
    monthly_transfer: float = 5000.0,
) -> dict:
    """Compute STP analysis using actual transferable source value each month."""
    if source_scheme_code == target_scheme_code:
        raise ValueError("Source and target scheme codes must be different.")
    validate_positive(initial_investment, "Initial investment")
    validate_positive(monthly_transfer, "Monthly transfer")

    df_src_all = get_nav(source_scheme_code)
    df_tgt_all = get_nav(target_scheme_code)
    stp_dates = monthly_dates(start_date, end_date, "MS")

    df_src_m = df_src_all.merge(stp_dates, on="date").rename(columns={"nav": "nav_src"})
    df_tgt_m = df_tgt_all.merge(stp_dates, on="date").rename(columns={"nav": "nav_tgt"})
    df_stp = df_src_m.merge(df_tgt_m, on="date").reset_index(drop=True)

    if df_stp.empty:
        raise ValueError(
            "No overlapping dates between source and target funds for the selected period."
        )

    init_units_src = initial_investment / df_stp["nav_src"].iloc[0]
    remaining_units_src = init_units_src
    cum_units_tgt = 0.0
    rows: list[dict] = []

    for _, row in df_stp.iterrows():
        nav_src = float(row["nav_src"])
        nav_tgt = float(row["nav_tgt"])
        available_value = remaining_units_src * nav_src
        transfer_amount = min(float(monthly_transfer), available_value)
        units_out = transfer_amount / nav_src if nav_src > 0 else 0.0
        remaining_units_src = max(remaining_units_src - units_out, 0.0)
        units_in = transfer_amount / nav_tgt if nav_tgt > 0 else 0.0
        cum_units_tgt += units_in
        value_src = remaining_units_src * nav_src
        value_tgt = cum_units_tgt * nav_tgt
        rows.append(
            {
                "date": row["date"],
                "nav_src": nav_src,
                "nav_tgt": nav_tgt,
                "transfer_amount": transfer_amount,
                "remaining_units_src": remaining_units_src,
                "cum_units_tgt": cum_units_tgt,
                "value_src": value_src,
                "value_tgt": value_tgt,
                "total_value": value_src + value_tgt,
            }
        )
        if remaining_units_src <= 1e-12:
            remaining_units_src = 0.0

    df_stp = pd.DataFrame(rows)

    df_xirr_stp = pd.DataFrame(
        [
            {"date": df_stp["date"].iloc[0], "amount": initial_investment},
            {"date": df_stp["date"].iloc[-1], "amount": -df_stp["total_value"].iloc[-1]},
        ]
    )
    try:
        xirr_value = clean_float(_xirr(df_xirr_stp) * 100)
    except Exception:
        xirr_value = None

    first_remaining = df_stp["remaining_units_src"].iloc[0]
    df_stp["src_units_norm"] = (
        df_stp["remaining_units_src"] / first_remaining if first_remaining > 0 else 0.0
    )
    max_tgt_units = df_stp["cum_units_tgt"].max()
    df_stp["tgt_units_norm"] = (
        df_stp["cum_units_tgt"] / max_tgt_units if max_tgt_units > 0 else 0.0
    )

    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "value_src": clean_float(row["value_src"]),
            "value_tgt": clean_float(row["value_tgt"]),
            "total_value": clean_float(row["total_value"]),
            "src_units_norm": clean_float(row["src_units_norm"]),
            "tgt_units_norm": clean_float(row["tgt_units_norm"]),
            "transfer_amount": clean_float(row["transfer_amount"]),
        }
        for _, row in df_stp.iterrows()
    ]

    last = df_stp.iloc[-1]
    return {
        "xirr": xirr_value,
        "source_final": clean_float(last["value_src"]),
        "target_final": clean_float(last["value_tgt"]),
        "total_final": clean_float(last["total_value"]),
        "series": series,
    }
