"""
FastAPI entry point for the Mutual Fund Analysis API.

Run with:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.core.cagr import get_all_cagrs, get_cagr, get_cagr_stats
from api.core.funds import get_scheme_codes
from api.core.nav import get_nav
from api.core.sip import sip_analysis
from api.core.stp import stp_analysis
from api.core.swp import swp_analysis
from api.models.schemas import (
    CAGRPoint,
    CAGRStatPoint,
    CompareRequest,
    CompareResult,
    DrawdownPoint,
    FundItem,
    FundSeries,
    NAVPoint,
    RollingCAGRPoint,
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


def _clean_float(val) -> float | None:
    """Convert val to float, return None for NaN/inf/None."""
    try:
        if val is None:
            return None
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _resolve_scheme_code(scheme_code: str) -> str:
    """Validate scheme_code against the fund catalogue; raise 404 if absent."""
    df_mfs = get_scheme_codes()
    if scheme_code not in df_mfs["schemeCode"].values:
        raise HTTPException(
            status_code=404,
            detail=f"scheme_code not found: {scheme_code}",
        )
    return scheme_code


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
        {"date": row["date"].strftime("%Y-%m-%d"), "nav": _clean_float(row["nav"])}
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
            "cagr": _clean_float(row["cagr"]),
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

    If combo_weights is provided (one weight per scheme_code, summing to 100),
    a weighted combination column is also computed and included in the response.
    """
    for code in req.scheme_codes:
        _resolve_scheme_code(code)

    if req.combo_weights is not None:
        if len(req.combo_weights) != len(req.scheme_codes):
            raise HTTPException(
                status_code=400,
                detail="combo_weights length must match scheme_codes length.",
            )
        total_wt = sum(req.combo_weights)
        if abs(total_wt - 100.0) > 0.01:
            raise HTTPException(
                status_code=400,
                detail="combo_weights must sum to 100.0.",
            )

    df_mfs = get_scheme_codes()
    list_navs: list[pd.DataFrame] = []
    fund_names: list[str] = []

    for code in req.scheme_codes:
        try:
            df_nav = get_nav(code)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        matches = df_mfs.loc[df_mfs["schemeCode"] == code, "schemeName"]
        name = matches.iloc[0] if not matches.empty else code
        fund_names.append(name)
        df_nav_indexed = df_nav.set_index("date").rename(columns={"nav": name})
        list_navs.append(df_nav_indexed)

    df_nav_all = pd.concat(list_navs, axis=1)
    all_names = list(fund_names)

    if req.combo_weights is not None:
        for i, name in enumerate(fund_names):
            df_nav_all[name + "_wt"] = df_nav_all[name] * req.combo_weights[i] / 100.0
        wt_cols = [n + "_wt" for n in fund_names]
        df_nav_all["combo"] = df_nav_all[wt_cols].sum(axis=1)
        all_names = all_names + ["combo"]

    df_nav_all = df_nav_all[all_names].dropna()

    if df_nav_all.empty:
        raise HTTPException(
            status_code=400,
            detail="No overlapping date range found for the selected funds.",
        )

    from_dt = pd.Timestamp(req.from_date)
    df_nav_filtered = df_nav_all[df_nav_all.index >= from_dt]

    if df_nav_filtered.empty:
        raise HTTPException(
            status_code=400,
            detail="No data available for the selected funds after from_date.",
        )

    df_rebased = df_nav_filtered.div(df_nav_filtered.iloc[0])

    funds_out: list[FundSeries] = []
    for name in all_names:
        series_data = [
            {"date": idx.strftime("%Y-%m-%d"), "rebased_nav": _clean_float(val)}
            for idx, val in df_rebased[name].items()
        ]
        funds_out.append(FundSeries(name=name, series=series_data))

    df_rebased_reset = df_rebased.reset_index()
    df_rebased_long = df_rebased_reset.melt(
        id_vars="date", value_vars=all_names, var_name="mf", value_name="nav"
    )
    df_rebased_long["cum_max"] = df_rebased_long.groupby("mf")["nav"].cummax()
    df_rebased_long["draw_down"] = (
        df_rebased_long["nav"] - df_rebased_long["cum_max"]
    ) / df_rebased_long["cum_max"]

    drawdown_out: list[DrawdownPoint] = [
        DrawdownPoint(
            date=row["date"].strftime("%Y-%m-%d"),
            mf=row["mf"],
            draw_down=_clean_float(row["draw_down"]),
        )
        for _, row in df_rebased_long.iterrows()
    ]

    rolling_cagr_out: list[RollingCAGRPoint] = []
    for name in all_names:
        df_single = df_nav_all[[name]].reset_index().rename(columns={name: "nav"})
        for y in range(1, 11):
            df_cagr_y = get_cagr(df_single, y)
            df_cagr_y = df_cagr_y[df_cagr_y["date"] >= from_dt]
            for _, row in df_cagr_y.iterrows():
                rolling_cagr_out.append(
                    RollingCAGRPoint(
                        date=row["date"].strftime("%Y-%m-%d"),
                        years=int(row["years"]),
                        mf=name,
                        cagr=_clean_float(row["cagr"]),
                    )
                )

    return CompareResult(
        funds=funds_out,
        drawdown=drawdown_out,
        rolling_cagr=rolling_cagr_out,
    )
