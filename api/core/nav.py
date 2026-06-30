"""
NAV fetching and processing.

get_nav(scheme_code) → pd.DataFrame with columns [date, nav]
  - date is a datetime64 index-compatible column
  - forward-filled over every calendar day to avoid gaps
"""

from __future__ import annotations

import urllib.request
import json
from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=256)
def get_nav(scheme_code: str) -> pd.DataFrame:
    """
    Fetch NAV history for *scheme_code* from mfapi.in and return a
    DataFrame with columns [date, nav] sorted ascending, with all
    calendar days filled forward.

    Raises:
        ValueError: if the scheme_code is not found or the API returns
                    no data rows.
    """
    mf_url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        with urllib.request.urlopen(mf_url) as url:
            data = json.load(url)
    except Exception as exc:
        raise ValueError(f"Could not fetch NAV for scheme_code={scheme_code}: {exc}") from exc

    raw = data.get("data", [])
    if not raw:
        raise ValueError(f"No NAV data returned for scheme_code={scheme_code}")

    df_navs = pd.DataFrame(raw)
    df_navs["date"] = pd.to_datetime(df_navs["date"], format="%d-%m-%Y")
    df_navs["nav"] = df_navs["nav"].astype(float)
    df_navs = df_navs.sort_values("date").set_index("date")

    # Expand to every calendar day and forward-fill gaps (weekends/holidays)
    all_dates = pd.DataFrame(
        pd.date_range(start=df_navs.index.min(), end=df_navs.index.max()),
        columns=["date"],
    ).set_index("date")

    df_navs = df_navs.join(all_dates, how="outer").ffill().reset_index()
    return df_navs
