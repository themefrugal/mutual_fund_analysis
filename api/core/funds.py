"""
Fund catalogue helpers.

Priority:
  1. Download live NAV data from AMFI (Excel download).
  2. Fallback to the local ../data/mf_codes.txt file.
"""

from __future__ import annotations

import re
import urllib.request
import json
from io import BytesIO
from pathlib import Path
from functools import lru_cache

import pandas as pd
import requests

# Path relative to this file: api/core/funds.py → ../../data/mf_codes.txt
_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "mf_codes.txt"


def get_scheme_codes_old() -> pd.DataFrame:
    """Fetch scheme codes from mfapi.in (slower, no ISIN)."""
    with urllib.request.urlopen("https://api.mfapi.in/mf") as url:
        data = json.load(url)
    df_mfs = pd.DataFrame(data)
    return df_mfs


def download_latest_nav() -> pd.DataFrame | None:
    """Download the AMFI latest-NAV Excel file and return as DataFrame."""
    url = "https://www.amfiindia.com/api/download-excel/latest-nav"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), header=None)
        return df
    except Exception as exc:
        print(f"Error downloading NAV from AMFI: {exc}")
        return None


def get_scheme_codes_from_amfi() -> pd.DataFrame:
    """Parse AMFI latest-NAV Excel into a clean fund catalogue DataFrame."""
    df = download_latest_nav()
    if df is None:
        return pd.DataFrame(columns=["schemeCode", "schemeISIN", "schemeName"])

    list_code: list[list[str]] = []
    for idx, row in df.iterrows():
        row_values = [str(val) if pd.notna(val) else "" for val in row.values]
        if all(val == "" for val in row_values):
            continue

        scheme_name = str(row[1]) if pd.notna(row[1]) else ""
        scheme_isin = str(row[2]) if pd.notna(row[2]) else ""
        scheme_isin_reinv = str(row[3]) if pd.notna(row[3]) else ""

        is_valid_isin = scheme_isin and len(scheme_isin) > 10 and scheme_isin.startswith("INF")

        if scheme_name.startswith(("A.", "B.", "C.", "D.")) and not is_valid_isin:
            continue

        if is_valid_isin:
            isin_to_use = scheme_isin
            if not isin_to_use or len(isin_to_use) < 10:
                if scheme_isin_reinv and len(scheme_isin_reinv) > 10:
                    isin_to_use = scheme_isin_reinv

            scheme_code = str(row[0]) if pd.notna(row[0]) else f"CODE_{idx}"
            scheme_name_clean = re.sub(r"\s+", " ", scheme_name).strip()

            if isin_to_use and len(isin_to_use) > 10:
                list_code.append([scheme_code, isin_to_use, scheme_name_clean])

    df_codes = pd.DataFrame(list_code, columns=["schemeCode", "schemeISIN", "schemeName"])
    df_codes = df_codes.drop_duplicates(subset=["schemeISIN"], keep="first").reset_index(drop=True)
    return df_codes


@lru_cache(maxsize=1)
def get_scheme_codes() -> pd.DataFrame:
    """
    Return a DataFrame with columns schemeCode, schemeISIN, schemeName.

    Tries AMFI first; falls back to the local mf_codes.txt file.
    """
    df = get_scheme_codes_from_amfi()
    if not df.empty:
        return df

    # Fallback: local txt file
    list_code: list[list[str]] = []
    with open(_DATA_FILE, "r") as fp:
        for line in fp:
            words = line.strip().split(";")
            if len(words) > 5:
                list_code.append([words[i] for i in [0, 1, 3]])

    df_codes = pd.DataFrame(list_code, columns=["schemeCode", "schemeISIN", "schemeName"])
    return df_codes
