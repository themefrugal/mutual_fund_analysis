from __future__ import annotations

import math

import numpy as np
import pandas as pd
from pyxirr import xirr

from .common import clean_float, validate_positive


def rolling_sip_xirr(
    df_navs: pd.DataFrame,
    window_years: int,
    monthly_amount: float,
    step_up_pct: float,
    frequency: str = "Monthly",
) -> pd.DataFrame:
    """Annualized XIRR for monthly SIPs redeemed after the full window duration."""
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
    df["day"] = df["date"].to_numpy(dtype="datetime64[D]")
    df = df.drop_duplicates("day", keep="last")
    nav_days = df["day"].to_numpy(dtype="datetime64[D]").astype(np.int64)
    first_day, last_day = int(nav_days.min()), int(nav_days.max())
    nav_by_day = np.full(last_day - first_day + 1, np.nan)
    present_by_day = np.zeros(len(nav_by_day), dtype=bool)
    nav_by_day[nav_days - first_day] = df["nav"].to_numpy(dtype=float)
    present_by_day[nav_days - first_day] = True

    num_months = window_years * 12
    payment_indices = np.arange(num_months)
    schedule_indices = np.arange(num_months + 1)
    month_amounts = monthly_amount * (1 + step_up_pct / 100.0) ** (payment_indices // 12)
    if frequency == "Monthly":
        month_ends = pd.date_range(
            start=pd.Timestamp(first_day, unit="D"), end=pd.Timestamp(last_day, unit="D"), freq="ME"
        ).to_numpy(dtype="datetime64[D]")
        start_count = max(0, len(month_ends) - num_months + 1)
    else:
        starts = pd.date_range(
            start=pd.Timestamp(first_day, unit="D"),
            end=pd.Timestamp(last_day, unit="D"),
            freq="D" if frequency == "Daily" else "W-MON",
        ).to_numpy(dtype="datetime64[D]")
        month_offsets = schedule_indices.astype("timedelta64[M]")
        start_count = len(starts)

    start_dates: list[np.datetime64] = []
    end_dates: list[np.datetime64] = []
    returns: list[float | None] = []
    for lo in range(0, start_count, 256):
        hi = min(lo + 256, start_count)
        if frequency == "Monthly":
            payment_dates = month_ends[np.arange(lo, hi)[:, None] + payment_indices]
            batch_starts = month_ends[lo:hi]
            start_months = batch_starts.astype("datetime64[M]")
            maturity_months = start_months + np.timedelta64(num_months, "M")
            maturity_first_days = maturity_months.astype("datetime64[D]")
            maturity_month_lengths = (
                (maturity_months + np.timedelta64(1, "M")).astype("datetime64[D]") - maturity_first_days
            ).astype(int)
            start_days = (batch_starts - start_months.astype("datetime64[D]")).astype(int) + 1
            maturity_dates = maturity_first_days + (
                np.minimum(start_days, maturity_month_lengths) - 1
            ).astype("timedelta64[D]")
            schedule_dates = np.column_stack((payment_dates, maturity_dates))
            schedule_dates = schedule_dates[schedule_dates[:, -1].astype(np.int64) <= last_day]
            if not len(schedule_dates):
                break
        else:
            batch_starts = starts[lo:hi]
            months = batch_starts.astype("datetime64[M]")[:, None] + month_offsets
            month_first_days = months.astype("datetime64[D]")
            days_in_month = ((months + np.timedelta64(1, "M")).astype("datetime64[D]") - month_first_days).astype(int)
            start_days = (batch_starts - batch_starts.astype("datetime64[M]").astype("datetime64[D]")).astype(int) + 1
            schedule_dates = month_first_days + (np.minimum(start_days[:, None], days_in_month) - 1).astype("timedelta64[D]")
            schedule_dates = schedule_dates[schedule_dates[:, -1].astype(np.int64) <= last_day]
            if not len(schedule_dates):
                break

        day_indices = schedule_dates.astype(np.int64) - first_day
        available = present_by_day[day_indices].all(axis=1)
        if not available.any():
            continue
        schedule_dates = schedule_dates[available]
        navs = nav_by_day[day_indices[available]]
        with np.errstate(divide="ignore", invalid="ignore"):
            final_values = (month_amounts / navs[:, :-1]).sum(axis=1) * navs[:, -1]
        cashflows = np.column_stack((np.broadcast_to(-month_amounts, navs[:, :-1].shape), final_values))

        for dates, amounts in zip(schedule_dates, cashflows):
            try:
                xirr_value = xirr(dates, amounts) * 100
                if not math.isfinite(xirr_value):
                    xirr_value = None
            except Exception:
                xirr_value = None
            start_dates.append(dates[0])
            end_dates.append(dates[-1])
            returns.append(xirr_value)

    return pd.DataFrame({"startDate": pd.to_datetime(start_dates), "endDate": pd.to_datetime(end_dates), "xirr": returns})


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
            "start_date": start,
            "end_date": end,
            "xirr": clean_float(value),
        }
        for start, end, value in zip(
            df["startDate"].dt.strftime("%Y-%m-%d"),
            df["endDate"].dt.strftime("%Y-%m-%d"),
            df["xirr"],
        )
    ]
