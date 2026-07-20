"""
Fund catalogue helpers.

Priority:
  1. Download live NAV data from AMFI (Excel download).
  2. Fallback to the local ../data/mf_codes.txt file.
"""

from __future__ import annotations

import urllib.request
import json
import re
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from .common import ensure_columns

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


def parse_amfi_latest_nav(df: pd.DataFrame) -> pd.DataFrame:
    """Parse AMFI latest-NAV rows into schemeCode/schemeISIN/schemeName."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["schemeCode", "schemeISIN", "schemeName"])

    list_code: list[list[str]] = []
    for _, row in df.iterrows():
        values = _row_values(row)
        scheme_code = _find_scheme_code(values)
        if scheme_code is None:
            continue

        isin_to_use = _find_isin(values) or ""
        scheme_name = _find_scheme_name(values, scheme_code)
        if not scheme_name:
            continue

        list_code.append([scheme_code, isin_to_use, scheme_name])

    df_codes = pd.DataFrame(list_code, columns=["schemeCode", "schemeISIN", "schemeName"])
    if df_codes.empty:
        return pd.DataFrame(columns=["schemeCode", "schemeISIN", "schemeName"])
    df_codes = df_codes.drop_duplicates(subset=["schemeCode"], keep="first").reset_index(drop=True)
    return df_codes


def _is_valid_isin(value: str) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z]{3}[A-Z0-9]{9,}", value.strip().upper()))


def _row_values(row: pd.Series) -> list[str]:
    return [str(value).strip() for value in row.tolist() if pd.notna(value) and str(value).strip()]


def _find_scheme_code(values: list[str]) -> str | None:
    for value in values:
        if value.isdigit():
            return value
    return None


def _find_isin(values: list[str]) -> str | None:
    for value in values:
        clean = value.strip().upper()
        if _is_valid_isin(clean):
            return clean
    return None


def _find_scheme_name(values: list[str], scheme_code: str) -> str | None:
    candidates = []
    for value in values:
        clean = " ".join(value.split())
        if not _looks_like_scheme_name(clean, scheme_code):
            continue
        candidates.append(clean)
    if not candidates:
        return None
    return max(candidates, key=lambda item: (len(item.split()), len(item)))


def _looks_like_scheme_name(value: str, scheme_code: str) -> bool:
    clean = value.strip()
    upper = clean.upper()
    if not clean or clean == "-" or clean == scheme_code:
        return False
    if clean.isdigit() or _is_valid_isin(upper):
        return False
    if re.fullmatch(r"\d+(\.\d+)?", clean):
        return False
    if re.fullmatch(r"\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}", clean):
        return False
    if upper in {"N.A.", "NA", "NAN", "SCHEME NAME"}:
        return False
    if upper.startswith(("OPEN ENDED SCHEMES", "CLOSE ENDED SCHEMES", "INTERVAL FUND")):
        return False
    if not re.search(r"[A-Za-z]", clean):
        return False
    return " " in clean or len(clean) >= 15


def get_scheme_codes_from_amfi() -> pd.DataFrame:
    """Download and parse AMFI latest-NAV data."""
    return parse_amfi_latest_nav(download_latest_nav())


def _load_local_scheme_codes() -> pd.DataFrame:
    list_code: list[list[str]] = []
    with open(_DATA_FILE, "r") as fp:
        for line in fp:
            words = line.strip().split(";")
            if len(words) > 5 and words[0].strip().isdigit():
                scheme_code = words[0].strip()
                isin = _find_isin([words[1], words[2]]) or ""
                scheme_name = _find_scheme_name(words, scheme_code)
                if scheme_name:
                    list_code.append([scheme_code, isin, scheme_name])
    df = pd.DataFrame(list_code, columns=["schemeCode", "schemeISIN", "schemeName"])
    ensure_columns(df, ["schemeCode", "schemeISIN", "schemeName"])
    return df


_SCHEME_CODES_CACHE_TTL_SECONDS = 12 * 60 * 60
_scheme_codes_cache: tuple[float, pd.DataFrame] | None = None


def get_scheme_codes() -> pd.DataFrame:
    """
    Return a DataFrame with columns schemeCode, schemeISIN, schemeName.

    Tries AMFI first; falls back to the local mf_codes.txt file.
    Caches a non-empty result so AMFI is only hit once per process.
    """
    global _scheme_codes_cache
    now = time.time()
    if (
        _scheme_codes_cache is not None
        and now - _scheme_codes_cache[0] < _SCHEME_CODES_CACHE_TTL_SECONDS
        and not _scheme_codes_cache[1].empty
    ):
        return _scheme_codes_cache[1].copy()

    df = get_scheme_codes_from_amfi()
    if not df.empty:
        _scheme_codes_cache = (now, df.copy())
        return df

    # Fallback: local txt file (not cached — always fresh if AMFI keeps failing)
    # Cache the local fallback too, so an unavailable AMFI endpoint does not
    # cause every request to retry the download before reading disk.
    df = _load_local_scheme_codes()
    _scheme_codes_cache = (now, df.copy())
    return df
