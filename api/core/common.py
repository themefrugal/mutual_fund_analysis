from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def clean_float(val: Any) -> float | None:
    try:
        if val is None:
            return None
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date >= end_date:
        raise ValueError("Start date must be before end date.")


def validate_positive(value: float, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} must be positive.")


def monthly_dates(start_date: date, end_date: date, freq: str) -> pd.DataFrame:
    validate_date_range(start_date, end_date)
    dates = pd.DataFrame(
        pd.date_range(start=start_date, end=end_date, freq=freq),
        columns=["date"],
    )
    if dates.empty:
        raise ValueError("No monthly dates found in the selected date range.")
    return dates


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
