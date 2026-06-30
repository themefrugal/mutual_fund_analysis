from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SIPRequest(BaseModel):
    scheme_code: str
    start_date: date
    end_date: date
    monthly_amount: float = 1000.0
    step_up_pct: float = 5.0


class SWPRequest(BaseModel):
    scheme_code: str
    start_date: date
    end_date: date
    initial_investment: float = 100000.0
    monthly_withdrawal: float = 5000.0


class STPRequest(BaseModel):
    source_scheme_code: str
    target_scheme_code: str
    start_date: date
    end_date: date
    initial_investment: float = 100000.0
    monthly_transfer: float = 5000.0


class CompareRequest(BaseModel):
    scheme_codes: list[str]
    from_date: date
    combo_weights: Optional[list[float]] = None  # weights for a weighted combo column

    @field_validator("scheme_codes")
    @classmethod
    def at_least_one_code(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("scheme_codes must contain at least one code")
        return v


# ---------------------------------------------------------------------------
# Response models — funds list
# ---------------------------------------------------------------------------

class FundItem(BaseModel):
    schemeCode: str
    schemeName: str
    schemeISIN: str


# ---------------------------------------------------------------------------
# Response models — NAV
# ---------------------------------------------------------------------------

class NAVPoint(BaseModel):
    date: str          # "YYYY-MM-DD"
    nav: Optional[float]


# ---------------------------------------------------------------------------
# Response models — CAGR
# ---------------------------------------------------------------------------

class CAGRPoint(BaseModel):
    date: str
    years: int
    cagr: Optional[float]


class CAGRStatPoint(BaseModel):
    years: int
    min: Optional[float]
    p25: Optional[float]
    median: Optional[float]
    mean: Optional[float]
    p75: Optional[float]
    max: Optional[float]


# ---------------------------------------------------------------------------
# Response models — SIP
# ---------------------------------------------------------------------------

class SIPSeriesPoint(BaseModel):
    date: str
    invested_amount: Optional[float]
    current_value: Optional[float]
    cum_units: Optional[float]


class SIPResult(BaseModel):
    xirr: Optional[float]
    series: list[SIPSeriesPoint]


# ---------------------------------------------------------------------------
# Response models — SWP
# ---------------------------------------------------------------------------

class SWPSeriesPoint(BaseModel):
    date: str
    inv_value: Optional[float]
    cur_value: Optional[float]
    cum_amount: Optional[float]
    total: Optional[float]


class SWPResult(BaseModel):
    xirr: Optional[float]
    series: list[SWPSeriesPoint]


# ---------------------------------------------------------------------------
# Response models — STP
# ---------------------------------------------------------------------------

class STPSeriesPoint(BaseModel):
    date: str
    value_src: Optional[float]
    value_tgt: Optional[float]
    total_value: Optional[float]
    src_units_norm: Optional[float]
    tgt_units_norm: Optional[float]


class STPResult(BaseModel):
    xirr: Optional[float]
    source_final: Optional[float]
    target_final: Optional[float]
    total_final: Optional[float]
    series: list[STPSeriesPoint]


# ---------------------------------------------------------------------------
# Response models — Compare
# ---------------------------------------------------------------------------

class FundSeries(BaseModel):
    name: str
    series: list[dict]          # [{date, rebased_nav}]


class DrawdownPoint(BaseModel):
    date: str
    mf: str
    draw_down: Optional[float]


class RollingCAGRPoint(BaseModel):
    date: str
    years: int
    mf: str
    cagr: Optional[float]


class CompareResult(BaseModel):
    funds: list[FundSeries]
    drawdown: list[DrawdownPoint]
    rolling_cagr: list[RollingCAGRPoint]
