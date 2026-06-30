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
from pydantic import BaseModel

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
    DrawdownRecoveryPoint,
    FundItem,
    FundSeries,
    GrowthPoint,
    NAVPoint,
    RollingCAGRPoint,
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


class _RollingXIRRRequest(BaseModel):
    scheme_code: str
    window_years: int = 7
    monthly_amount: float = 1000.0
    step_up_pct: float = 0.0


def _solve_xirr_py(cashflows: list[tuple]) -> float | None:
    if len(cashflows) < 2:
        return None
    t0 = min(d for d, _ in cashflows)

    def years(d):
        return (d - t0).days / 365.0

    def npv(r):
        return sum(cf / (1 + r) ** years(d) for d, cf in cashflows)

    def npv_prime(r):
        return sum(
            -cf * years(d) / (1 + r) ** (years(d) + 1)
            for d, cf in cashflows
            if years(d) != 0
        )

    r = 0.1
    for _ in range(100):
        f = npv(r)
        if abs(f) < 1e-7:
            return r
        fp = npv_prime(r)
        if fp == 0 or np.isnan(fp):
            return None
        dr = f / fp
        r -= dr
        if not (-0.999999 < r < 1e6):
            return None
    return None


@app.post("/api/sip/rolling-xirr", response_model=list[RollingXIRRPoint], tags=["SIP"])
def rolling_sip_xirr(req: _RollingXIRRRequest):
    """Compute rolling SIP XIRR across all windows of `window_years` length."""
    _resolve_scheme_code(req.scheme_code)
    df_navs = get_nav(req.scheme_code)
    nav_map = {row["date"].date(): float(row["nav"]) for _, row in df_navs.iterrows()}

    lo = min(nav_map)
    hi = max(nav_map)

    # Generate month-end dates
    month_ends = pd.date_range(
        start=pd.Timestamp(lo), end=pd.Timestamp(hi), freq="ME"
    ).date.tolist()

    num_months = req.window_years * 12
    results: list[RollingXIRRPoint] = []

    for i in range(len(month_ends) - num_months + 1):
        window = month_ends[i : i + num_months]
        navs = [nav_map.get(d) for d in window]
        if any(v is None for v in navs):
            continue
        amounts = [
            req.monthly_amount * ((1 + req.step_up_pct / 100) ** (idx // 12))
            for idx in range(num_months)
        ]
        units = [amt / nav for amt, nav in zip(amounts, navs)]
        final_value = sum(units) * navs[-1]
        cashflows = [(d, -amt) for d, amt in zip(window, amounts)]
        cashflows.append((window[-1], final_value))
        r = _solve_xirr_py(cashflows)
        results.append(
            RollingXIRRPoint(
                start_date=window[0].strftime("%Y-%m-%d"),
                end_date=window[-1].strftime("%Y-%m-%d"),
                xirr=_clean_float(r * 100) if r is not None else None,
            )
        )

    return results


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
    drawdown_recovery_out: list[DrawdownRecoveryPoint] = []

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

        # Drawdown recovery: earliest date when NAV was last at the current level
        latest_date = df_nav["date"].max()
        latest_nav_row = df_nav[df_nav["date"] == latest_date]
        latest_nav = float(latest_nav_row["nav"].values[0]) if not latest_nav_row.empty else None
        last_seen_date = None
        last_seen_nav = None
        if latest_nav is not None:
            earlier = df_nav[df_nav["nav"] > latest_nav]
            if not earlier.empty:
                back_row = earlier.iloc[0]
                last_seen_date = back_row["date"].strftime("%Y-%m-%d")
                last_seen_nav = _clean_float(back_row["nav"])
        drawdown_recovery_out.append(
            DrawdownRecoveryPoint(
                name=name,
                latest_date=latest_date.strftime("%Y-%m-%d"),
                latest_nav=_clean_float(latest_nav),
                last_seen_date=last_seen_date,
                last_seen_nav=last_seen_nav,
            )
        )

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

    # Comparative growth: value of ₹1000 invested N years ago (using 1Y to 10Y)
    growth_out: list[GrowthPoint] = []
    for name in all_names:
        df_single = df_nav_all[[name]].reset_index().rename(columns={name: "nav"})
        for y in range(1, 11):
            shift = 365 * y
            df_g = df_single.copy()
            df_g["prev_nav"] = df_g["nav"].shift(shift)
            df_g = df_g.dropna()
            df_g = df_g[df_g["date"] >= from_dt]
            for _, row in df_g.iterrows():
                end_val = 1000.0 * row["nav"] / row["prev_nav"]
                growth_out.append(
                    GrowthPoint(
                        date=row["date"].strftime("%Y-%m-%d"),
                        mf=f"{name}|{y}Y",
                        end_value=_clean_float(end_val),
                    )
                )

    return CompareResult(
        funds=funds_out,
        drawdown=drawdown_out,
        rolling_cagr=rolling_cagr_out,
        drawdown_recovery=drawdown_recovery_out,
        growth_series=growth_out,
    )
