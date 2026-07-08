from __future__ import annotations

import pandas as pd
from pyxirr import xirr

from .common import clean_float, validate_positive


def _month_end_dates(lo: pd.Timestamp, hi: pd.Timestamp) -> list[pd.Timestamp]:
    return pd.date_range(start=lo, end=hi, freq="ME").to_list()


def rolling_sip_xirr(
    df_navs: pd.DataFrame,
    window_years: int,
    monthly_amount: float,
    step_up_pct: float,
) -> pd.DataFrame:
    if window_years <= 0:
        raise ValueError("SIP duration must be positive.")
    validate_positive(monthly_amount, "Monthly SIP amount")
    if step_up_pct < 0:
        raise ValueError("Annual step-up must be zero or positive.")

    if df_navs.empty:
        raise ValueError("NAV data is empty.")

    df = df_navs[["date", "nav"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    nav_map = {row["date"].date(): float(row["nav"]) for _, row in df.iterrows()}
    month_ends = _month_end_dates(df["date"].min(), df["date"].max())
    num_months = window_years * 12

    if len(month_ends) < num_months:
        return pd.DataFrame(columns=["startDate", "endDate", "xirr"])

    results: list[dict] = []
    for i in range(len(month_ends) - num_months + 1):
        window = month_ends[i : i + num_months]
        window_dates = [d.date() for d in window]
        navs = [nav_map.get(d) for d in window_dates]
        if any(v is None for v in navs):
            continue

        amounts = [
            monthly_amount * ((1 + step_up_pct / 100.0) ** (idx // 12))
            for idx in range(num_months)
        ]
        units = [amt / nav for amt, nav in zip(amounts, navs)]
        final_value = sum(units) * navs[-1]
        cashflows = [(d, -amt) for d, amt in zip(window_dates, amounts)]
        cashflows.append((window_dates[-1], final_value))

        try:
            xirr_value = clean_float(xirr(cashflows) * 100)
        except Exception:
            xirr_value = None

        results.append(
            {
                "startDate": pd.Timestamp(window_dates[0]),
                "endDate": pd.Timestamp(window_dates[-1]),
                "xirr": xirr_value,
            }
        )

    return pd.DataFrame(results, columns=["startDate", "endDate", "xirr"])


def rolling_sip_xirr_records(
    df_navs: pd.DataFrame,
    window_years: int,
    monthly_amount: float,
    step_up_pct: float,
) -> list[dict]:
    df = rolling_sip_xirr(df_navs, window_years, monthly_amount, step_up_pct)
    return [
        {
            "start_date": row["startDate"].strftime("%Y-%m-%d"),
            "end_date": row["endDate"].strftime("%Y-%m-%d"),
            "xirr": clean_float(row["xirr"]),
        }
        for _, row in df.iterrows()
    ]
