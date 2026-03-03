"""
CAGR computation helpers.

get_cagr(df_navs, num_years)  → DataFrame [date, years, cagr]
get_cagr_stats(scheme_code)   → list of dicts with per-year statistics
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .nav import get_nav


def get_cagr(df_navs_orig: pd.DataFrame, num_years: int = 1) -> pd.DataFrame:
    """
    Compute rolling CAGR for *num_years* using a simple 365-day shift.

    Parameters
    ----------
    df_navs_orig : DataFrame
        Must have columns [date, nav].
    num_years : int
        Holding period in years (1–10).

    Returns
    -------
    DataFrame with columns [date, years, cagr].
    """
    df_navs = df_navs_orig.copy()
    df_navs["prev_nav"] = df_navs["nav"].shift(365 * num_years)
    df_navs = df_navs.dropna(subset=["prev_nav"])
    df_navs["returns"] = df_navs["nav"] / df_navs["prev_nav"] - 1
    df_navs["cagr"] = 100.0 * ((1 + df_navs["returns"]) ** (1.0 / num_years) - 1)
    df_navs["years"] = num_years
    return df_navs[["date", "years", "cagr"]].reset_index(drop=True)


def get_all_cagrs(scheme_code: str) -> pd.DataFrame:
    """
    Fetch NAV for *scheme_code* and compute rolling CAGR for years 1–10.

    Returns a concatenated DataFrame with columns [date, years, cagr].
    """
    df_navs = get_nav(scheme_code)
    frames = [get_cagr(df_navs, y) for y in range(1, 11)]
    return pd.concat(frames, ignore_index=True)


def get_cagr_stats(scheme_code: str) -> list[dict]:
    """
    Return per-holding-period CAGR statistics.

    Returns
    -------
    List of dicts, one per year 1–10:
        {years, min, p25, median, mean, p75, max}
    All values are floats (or None when insufficient data).
    """
    df_cagrs = get_all_cagrs(scheme_code)
    results: list[dict] = []

    for y in range(1, 11):
        series = df_cagrs.loc[df_cagrs["years"] == y, "cagr"].dropna()
        if series.empty:
            results.append(
                dict(years=y, min=None, p25=None, median=None, mean=None, p75=None, max=None)
            )
        else:
            results.append(
                dict(
                    years=y,
                    min=_clean(series.min()),
                    p25=_clean(series.quantile(0.25)),
                    median=_clean(series.median()),
                    mean=_clean(series.mean()),
                    p75=_clean(series.quantile(0.75)),
                    max=_clean(series.max()),
                )
            )
    return results


def _clean(val: float) -> float | None:
    """Return None if val is NaN/inf, else the float."""
    if val is None:
        return None
    try:
        if np.isnan(val) or np.isinf(val):
            return None
    except (TypeError, ValueError):
        return None
    return float(val)
