from __future__ import annotations

import pandas as pd
from pyxirr import xirr

from api.core.common import clean_float, validate_positive


def _month_end_dates(lo: pd.Timestamp, hi: pd.Timestamp) -> list[pd.Timestamp]:
    return pd.date_range(start=lo, end=hi, freq="ME").to_list()


def rolling_sip_xirr(
    df_navs: pd.DataFrame,
    window_years: int,
    monthly_amount: float,
    step_up_pct: float,
    frequency: str = "Monthly",
) -> pd.DataFrame:
    """Annualized XIRR for monthly SIPs, sampled at monthly, Monday, or daily starts."""
    if window_years <= 0:
        raise ValueError("SIP duration must be positive.")
    validate_positive(monthly_amount, "Monthly SIP amount")
    if step_up_pct < 0:
        raise ValueError("Annual step-up must be zero or positive.")
    if frequency not in ("Monthly", "Weekly", "Daily"):
        raise ValueError("Rolling frequency must be Monthly, Weekly, or Daily.")

    if df_navs.empty:
        raise ValueError("NAV data is empty.")

    df = df_navs[["date", "nav"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    last_nav_date = df["date"].max()
    nav_map = {row["date"].date(): float(row["nav"]) for _, row in df.iterrows()}
    num_months = window_years * 12
    if frequency == "Monthly":
        month_ends = _month_end_dates(df["date"].min(), last_nav_date)
        windows = (month_ends[i : i + num_months] for i in range(len(month_ends) - num_months + 1))
    else:
        starts = pd.date_range(df["date"].min(), last_nav_date, freq="D" if frequency == "Daily" else "W-MON")
        month_offsets = [pd.DateOffset(months=idx) for idx in range(num_months)]
        windows = ([start + offset for offset in month_offsets] for start in starts)

    results: list[dict] = []
    for window in windows:
        redemption_date = window[0] + pd.DateOffset(months=num_months)
        if redemption_date > last_nav_date:
            break
        window_dates = [d.date() for d in window]
        navs = [nav_map.get(d) for d in window_dates]
        redemption_nav = nav_map.get(redemption_date.date())
        if any(v is None for v in navs) or redemption_nav is None:
            continue

        amounts = [
            monthly_amount * ((1 + step_up_pct / 100.0) ** (idx // 12))
            for idx in range(num_months)
        ]
        units = [amt / nav for amt, nav in zip(amounts, navs)]
        final_value = sum(units) * redemption_nav
        cashflows = [(d, -amt) for d, amt in zip(window_dates, amounts)]
        cashflows.append((redemption_date.date(), final_value))

        try:
            xirr_value = clean_float(xirr(cashflows) * 100)
        except Exception:
            xirr_value = None

        results.append(
            {
                "startDate": pd.Timestamp(window_dates[0]),
                "endDate": pd.Timestamp(redemption_date.date()),
                "xirr": xirr_value,
            }
        )

    return pd.DataFrame(results, columns=["startDate", "endDate", "xirr"])


def rolling_sip_xirr_records(
    df_navs: pd.DataFrame,
    window_years: int,
    monthly_amount: float,
    step_up_pct: float,
    frequency: str = "Monthly",
) -> list[dict]:
    df = rolling_sip_xirr(df_navs, window_years, monthly_amount, step_up_pct, frequency)
    return [
        {
            "start_date": row["startDate"].strftime("%Y-%m-%d"),
            "end_date": row["endDate"].strftime("%Y-%m-%d"),
            "xirr": clean_float(row["xirr"]),
        }
        for _, row in df.iterrows()
    ]
