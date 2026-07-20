"""
FastAPI entry point for the Mutual Fund Analysis API.

Run with:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.core.cagr import get_all_cagrs, get_cagr_stats
from api.core.common import clean_float
from api.core.compare import cached_compare_analysis
from api.core.funds import get_scheme_codes
from api.core.nav import get_nav
from api.core.rolling import rolling_sip_xirr_records
from api.core.sip import sip_analysis
from api.core.stp import stp_analysis
from api.core.swp import swp_analysis
from api.models.schemas import (
    CAGRPoint,
    CAGRStatPoint,
    CompareRequest,
    CompareResult,
    FundItem,
    NAVPoint,
    RollingXIRRPoint,
    SIPRequest,
    SIPResult,
    STPRequest,
    STPResult,
    SWPRequest,
    SWPResult,
)

app = FastAPI(
    title="Mutual Fund Analysis API",
    description="REST API for mutual fund NAV, CAGR, SIP, SWP and STP analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_scheme_code(scheme_code: str) -> str:
    """Validate scheme_code against the fund catalogue; raise 404 if absent."""
    df_mfs = get_scheme_codes()
    scheme_code = str(scheme_code).strip()
    if scheme_code not in df_mfs["schemeCode"].astype(str).values:
        raise HTTPException(
            status_code=404,
            detail=f"scheme_code not found: {scheme_code}",
        )
    return scheme_code


def _validate_scheme_codes(scheme_codes: list[str]) -> list[str]:
    """Validate a batch against one catalogue lookup instead of one per fund."""
    df_mfs = get_scheme_codes()
    known_codes = set(df_mfs["schemeCode"].astype(str))
    resolved_codes = [str(code).strip() for code in scheme_codes]
    missing_code = next((code for code in resolved_codes if code not in known_codes), None)
    if missing_code is not None:
        raise HTTPException(status_code=404, detail=f"scheme_code not found: {missing_code}")
    return resolved_codes


@app.get("/api/funds", response_model=list[FundItem], tags=["Funds"])
def list_funds():
    """Return the complete fund catalogue with schemeCode, schemeName and schemeISIN."""
    df_mfs = get_scheme_codes()
    return df_mfs[["schemeCode", "schemeISIN", "schemeName"]].to_dict(orient="records")


@app.get("/api/nav/{scheme_code}", response_model=list[NAVPoint], tags=["NAV"])
def get_nav_history(scheme_code: str):
    """Return full NAV history for a fund (forward-filled over weekends/holidays)."""
    _resolve_scheme_code(scheme_code)
    try:
        df = get_nav(scheme_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        {"date": row["date"].strftime("%Y-%m-%d"), "nav": clean_float(row["nav"])}
        for _, row in df.iterrows()
    ]


@app.get("/api/cagr/{scheme_code}", response_model=list[CAGRPoint], tags=["CAGR"])
def get_cagr_history(scheme_code: str):
    """Return rolling CAGR time-series for holding periods of 1-10 years."""
    _resolve_scheme_code(scheme_code)
    try:
        df = get_all_cagrs(scheme_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "years": int(row["years"]),
            "cagr": clean_float(row["cagr"]),
        }
        for _, row in df.iterrows()
    ]


@app.get("/api/cagr/{scheme_code}/stats", response_model=list[CAGRStatPoint], tags=["CAGR"])
def get_cagr_statistics(scheme_code: str):
    """Return per-holding-period CAGR stats (min, P25, median, mean, P75, max)."""
    _resolve_scheme_code(scheme_code)
    try:
        return get_cagr_stats(scheme_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sip", response_model=SIPResult, tags=["SIP"])
def run_sip(req: SIPRequest):
    """Run a Systematic Investment Plan (SIP) analysis with optional annual step-up."""
    _resolve_scheme_code(req.scheme_code)
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date.")
    if req.monthly_amount <= 0:
        raise HTTPException(status_code=400, detail="monthly_amount must be positive.")
    try:
        return sip_analysis(
            scheme_code=req.scheme_code,
            start_date=req.start_date,
            end_date=req.end_date,
            monthly_amount=req.monthly_amount,
            step_up_pct=req.step_up_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class _RollingXIRRRequest(BaseModel):
    scheme_code: str
    window_years: int = 7
    monthly_amount: float = 1000.0
    step_up_pct: float = 0.0


@app.post("/api/sip/rolling-xirr", response_model=list[RollingXIRRPoint], tags=["SIP"])
def rolling_sip_xirr(req: _RollingXIRRRequest):
    """Compute rolling SIP XIRR across all windows of `window_years` length."""
    _resolve_scheme_code(req.scheme_code)
    if req.window_years <= 0:
        raise HTTPException(status_code=400, detail="window_years must be positive.")
    if req.monthly_amount <= 0:
        raise HTTPException(status_code=400, detail="monthly_amount must be positive.")
    if req.step_up_pct < 0:
        raise HTTPException(status_code=400, detail="step_up_pct must be zero or positive.")
    try:
        return rolling_sip_xirr_records(
            get_nav(req.scheme_code),
            req.window_years,
            req.monthly_amount,
            req.step_up_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/swp", response_model=SWPResult, tags=["SWP"])
def run_swp(req: SWPRequest):
    """Run a Systematic Withdrawal Plan (SWP) analysis."""
    _resolve_scheme_code(req.scheme_code)
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date.")
    if req.initial_investment <= 0:
        raise HTTPException(status_code=400, detail="initial_investment must be positive.")
    if req.monthly_withdrawal <= 0:
        raise HTTPException(status_code=400, detail="monthly_withdrawal must be positive.")
    try:
        return swp_analysis(
            scheme_code=req.scheme_code,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_investment=req.initial_investment,
            monthly_withdrawal=req.monthly_withdrawal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/stp", response_model=STPResult, tags=["STP"])
def run_stp(req: STPRequest):
    """Run a Systematic Transfer Plan (STP) analysis."""
    _resolve_scheme_code(req.source_scheme_code)
    _resolve_scheme_code(req.target_scheme_code)
    if req.source_scheme_code == req.target_scheme_code:
        raise HTTPException(status_code=400, detail="Source and target funds must be different.")
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date.")
    if req.initial_investment <= 0:
        raise HTTPException(status_code=400, detail="initial_investment must be positive.")
    if req.monthly_transfer <= 0:
        raise HTTPException(status_code=400, detail="monthly_transfer must be positive.")
    try:
        return stp_analysis(
            source_scheme_code=req.source_scheme_code,
            target_scheme_code=req.target_scheme_code,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_investment=req.initial_investment,
            monthly_transfer=req.monthly_transfer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/compare", response_model=CompareResult, tags=["Compare"])
def compare_funds(req: CompareRequest):
    """
    Compare multiple funds on cumulative returns, drawdown and rolling CAGR.

    If combo_weights is provided, a weighted combination column is also included.
    """
    scheme_codes = _validate_scheme_codes(req.scheme_codes)
    try:
        return cached_compare_analysis(
            scheme_codes=scheme_codes,
            from_date=req.from_date,
            combo_weights=req.combo_weights,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

