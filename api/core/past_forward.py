"""Within-fund trailing-versus-forward return analysis.

All returns are annualised percentages.  The module contains only deterministic
calculation and narrative functions so it can be used by either UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

import numpy as np
import pandas as pd


FREQUENCIES = {
    "Daily": "D",
    "Weekly": "W-FRI",
    "Monthly": "ME",
}


@dataclass(frozen=True)
class AnalysisConfig:
    backward_years: int = 2
    forward_years: int = 3
    frequency: str = "Weekly"
    non_overlapping: bool = False
    hurdle_rate: float = 0.0


def build_observations(
    df_navs: pd.DataFrame,
    config: AnalysisConfig,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, float | None]:
    """Build complete past-to-forward CAGR observations from daily NAV data.

    The project's NAV loader fills calendar gaps forward, therefore intended
    calendar dates are always aligned to the most recently published NAV.
    Year boundaries use ``DateOffset(years=...)`` rather than 365-day shifts.
    """
    if config.frequency not in FREQUENCIES:
        raise ValueError(f"Unsupported observation frequency: {config.frequency}")
    if config.backward_years <= 0 or config.forward_years <= 0:
        raise ValueError("Backward and forward periods must be positive.")

    navs = df_navs[["date", "nav"]].copy().dropna().sort_values("date")
    navs["date"] = pd.to_datetime(navs["date"])
    navs = navs.loc[navs["nav"] > 0].drop_duplicates("date", keep="last").set_index("date")
    if navs.empty:
        return _empty_observations(), None

    first_date, last_date = navs.index.min(), navs.index.max()
    first_anchor = first_date + pd.DateOffset(years=config.backward_years)
    last_anchor = last_date - pd.DateOffset(years=config.forward_years)
    if start_date is not None:
        first_anchor = max(first_anchor, pd.Timestamp(start_date))
    if end_date is not None:
        last_anchor = min(last_anchor, pd.Timestamp(end_date))
    if first_anchor > last_anchor:
        return _empty_observations(), _current_trailing_cagr(navs, config.backward_years)

    anchors = pd.date_range(first_anchor, last_anchor, freq=FREQUENCIES[config.frequency])
    if config.non_overlapping:
        anchors = _non_overlapping_anchors(anchors, max(config.backward_years, config.forward_years))

    rows: list[dict[str, object]] = []
    for anchor in anchors:
        backward_start = anchor - pd.DateOffset(years=config.backward_years)
        forward_end = anchor + pd.DateOffset(years=config.forward_years)
        try:
            start_nav = float(navs.at[backward_start, "nav"])
            anchor_nav = float(navs.at[anchor, "nav"])
            end_nav = float(navs.at[forward_end, "nav"])
        except KeyError:
            continue
        if min(start_nav, anchor_nav, end_nav) <= 0:
            continue
        rows.append(
            {
                "as_of_date": anchor,
                "backward_start_date": backward_start,
                "forward_end_date": forward_end,
                "backward_start_nav": start_nav,
                "as_of_nav": anchor_nav,
                "forward_end_nav": end_nav,
                "trailing_cagr": 100 * ((anchor_nav / start_nav) ** (1 / config.backward_years) - 1),
                "forward_cagr": 100 * ((end_nav / anchor_nav) ** (1 / config.forward_years) - 1),
                "data_quality": "calendar-aligned NAVs",
            }
        )
    return pd.DataFrame(rows, columns=_empty_observations().columns), _current_trailing_cagr(navs, config.backward_years)


def summarize_observations(observations: pd.DataFrame, config: AnalysisConfig) -> dict[str, float | int | str | None]:
    """Return descriptive and regression statistics, with no inferential claims."""
    if observations.empty:
        return {"valid_observations": 0, "approx_independent_windows": 0}
    x = observations["trailing_cagr"].astype(float)
    y = observations["forward_cagr"].astype(float)
    result: dict[str, float | int | str | None] = {
        "valid_observations": len(observations),
        "earliest_as_of_date": observations["as_of_date"].min().strftime("%Y-%m-%d"),
        "latest_as_of_date": observations["as_of_date"].max().strftime("%Y-%m-%d"),
        "mean_trailing": float(x.mean()), "median_trailing": float(x.median()), "std_trailing": float(x.std(ddof=1)),
        "mean_forward": float(y.mean()), "median_forward": float(y.median()), "std_forward": float(y.std(ddof=1)),
        "min_forward": float(y.min()), "max_forward": float(y.max()),
        "pearson": _correlation(x, y, "pearson"),
        "spearman": _correlation(x, y, "spearman"),
        "kendall": _correlation(x, y, "kendall"),
    }
    span_days = max((observations["as_of_date"].max() - observations["as_of_date"].min()).days, 0)
    result["approx_independent_windows"] = max(1, floor(span_days / (365 * max(config.backward_years, config.forward_years))))
    if len(observations) >= 3 and x.nunique() > 1:
        slope, intercept = np.polyfit(x, y, 1)
        predicted = intercept + slope * x
        residuals = y - predicted
        total = float(((y - y.mean()) ** 2).sum())
        result.update(
            regression_intercept=float(intercept),
            regression_slope=float(slope),
            r_squared=float(1 - (residuals ** 2).sum() / total) if total else None,
            residual_standard_error=float(np.sqrt((residuals ** 2).sum() / (len(y) - 2))),
        )
    else:
        result.update(regression_intercept=None, regression_slope=None, r_squared=None, residual_standard_error=None)
    return result


def nearest_conditional_observations(observations: pd.DataFrame, target: float, hurdle_rate: float) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    """Select nearest within-fund historical analogues and describe their outcomes."""
    if observations.empty:
        return observations.copy(), {"matches": 0}
    count = len(observations)
    requested = max(10, ceil(count * 0.2))
    k = min(requested, max(10, floor(count * 0.4)), count)
    matched = observations.assign(_distance=(observations["trailing_cagr"] - target).abs()).nsmallest(k, "_distance").drop(columns="_distance")
    future = matched["forward_cagr"]
    return matched, {
        "matches": len(matched), "trailing_low": float(matched["trailing_cagr"].min()), "trailing_high": float(matched["trailing_cagr"].max()),
        "median_forward": float(future.median()), "mean_forward": float(future.mean()),
        "p10": float(future.quantile(.1)), "p25": float(future.quantile(.25)), "p75": float(future.quantile(.75)), "p90": float(future.quantile(.9)),
        "min_forward": float(future.min()), "max_forward": float(future.max()),
        "positive_count": int((future > 0).sum()), "hurdle_count": int((future > hurdle_rate).sum()),
    }


def return_zones(observations: pd.DataFrame, hurdle_rate: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide this fund's own trailing-return history into equal-count zones."""
    if observations.empty:
        return observations.copy(), pd.DataFrame()
    zoned = observations.copy()
    zoned["zone"] = pd.qcut(zoned["trailing_cagr"].rank(method="first"), 3, labels=["Low", "Middle", "High"])
    rows = []
    for zone, group in zoned.groupby("zone", observed=True):
        future = group["forward_cagr"]
        rows.append({"zone": f"{zone} trailing-return periods", "trailing_range": f"{group.trailing_cagr.min():.2f}% to {group.trailing_cagr.max():.2f}%", "observations": len(group), "median_forward": future.median(), "mean_forward": future.mean(), "p25_forward": future.quantile(.25), "p75_forward": future.quantile(.75), "positive_frequency": (future > 0).mean(), "hurdle_frequency": (future > hurdle_rate).mean()})
    return zoned, pd.DataFrame(rows)


def generate_narrative(summary: dict[str, float | int | str | None], conditional: dict[str, float | int | None], config: AnalysisConfig, current_trailing: float | None) -> dict[str, list[str]]:
    """Pure, deterministic and deliberately non-predictive interpretation."""
    n = int(summary.get("valid_observations", 0) or 0)
    coverage = []
    if n < 12:
        coverage.append(f"Only {n} complete historical observations are available. This is insufficient for a meaningful relationship assessment.")
    elif n < 24:
        coverage.append(f"The analysis contains {n} complete observations, so it is very limited historical evidence.")
    elif n < 60:
        coverage.append(f"The analysis contains {n} complete observations. It describes this fund's history, but the estimates remain uncertain.")
    else:
        coverage.append(f"The analysis contains {n} rolling observations from {summary['earliest_as_of_date']} to {summary['latest_as_of_date']}; adjacent windows overlap substantially.")
    rho = summary.get("spearman")
    relationship = []
    if isinstance(rho, float):
        strength = "no clear" if abs(rho) < .1 else "weak" if abs(rho) < .25 else "moderate" if abs(rho) < .5 else "strong"
        direction = "persistence-like" if rho > 0 else "mean-reversion-like" if rho < 0 else "relationship"
        relationship.append(f"Spearman correlation is {rho:.2f}, indicating a {strength} {direction} historical association.")
    slope = summary.get("regression_slope")
    if isinstance(slope, float) and n >= 12:
        change = slope * 10
        relationship.append(f"A 10-percentage-point increase in trailing CAGR was historically associated with a {abs(change):.2f}-percentage-point {'increase' if change >= 0 else 'decrease'} in subsequent CAGR on the fitted line.")
    conditional_lines = []
    matches = int(conditional.get("matches", 0) or 0)
    if current_trailing is not None and matches >= 10:
        conditional_lines.append(f"The current trailing {config.backward_years}-year CAGR is {current_trailing:.2f}%. The {matches} closest historical periods ranged from {conditional['trailing_low']:.2f}% to {conditional['trailing_high']:.2f}% and had a median subsequent {config.forward_years}-year CAGR of {conditional['median_forward']:.2f}%.")
        conditional_lines.append(f"A positive subsequent return occurred in {conditional['positive_count']} of {matches} comparable historical observations; this is a historical frequency, not a forecast.")
    limitations = [f"Daily, weekly, and monthly rolling observations overlap. The approximate independent-window count is {summary.get('approx_independent_windows', 0)}, so correlations and fitted lines are descriptive diagnostics, not statistical proof."]
    conclusion = ["Overall, this is a within-fund description of historical association. It does not establish causation, guarantee future returns, or provide a forecast."]
    return {"data_coverage": coverage, "relationship": relationship, "conditional_history": conditional_lines, "limitations": limitations, "conclusion": conclusion}


def scatter_metric_matrices(
    df_navs: pd.DataFrame,
    frequency: str,
    non_overlapping: bool,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    """Calculate comparable matrices from each individual trailing/forward scatter.

    Rows are trailing horizons 1–5 years and columns are forward horizons
    1–10 years. Every cell comes from a separately constructed observation set.
    """
    rows = [f"{years}Y" for years in range(1, 6)]
    columns = [f"{years}Y" for years in range(1, 11)]
    names = ["Pearson correlation", "Spearman correlation", "R-squared", "Regression slope", "Regression intercept", "Fitted line equation", "Observation count", "Residual standard error"]
    matrices = {name: pd.DataFrame(index=rows, columns=columns, dtype=object) for name in names}
    for backward_years in range(1, 6):
        for forward_years in range(1, 11):
            config = AnalysisConfig(backward_years, forward_years, frequency, non_overlapping)
            observations, _ = build_observations(df_navs, config, start_date, end_date)
            summary = summarize_observations(observations, config)
            row, column = f"{backward_years}Y", f"{forward_years}Y"
            matrices["Pearson correlation"].at[row, column] = _format_metric(summary.get("pearson"), ".3f")
            matrices["Spearman correlation"].at[row, column] = _format_metric(summary.get("spearman"), ".3f")
            matrices["R-squared"].at[row, column] = _format_metric(summary.get("r_squared"), ".3f")
            matrices["Regression slope"].at[row, column] = _format_metric(summary.get("regression_slope"), ".3f")
            matrices["Regression intercept"].at[row, column] = _format_metric(summary.get("regression_intercept"), ".2f")
            matrices["Observation count"].at[row, column] = summary.get("valid_observations", 0)
            matrices["Residual standard error"].at[row, column] = _format_metric(summary.get("residual_standard_error"), ".2f")
            slope, intercept = summary.get("regression_slope"), summary.get("regression_intercept")
            matrices["Fitted line equation"].at[row, column] = (
                f"y = {intercept:.2f} + {slope:.3f}x"
                if isinstance(slope, float) and isinstance(intercept, float) else "—"
            )
    return matrices


def _empty_observations() -> pd.DataFrame:
    return pd.DataFrame(columns=["as_of_date", "backward_start_date", "forward_end_date", "backward_start_nav", "as_of_nav", "forward_end_nav", "trailing_cagr", "forward_cagr", "data_quality"])


def _current_trailing_cagr(navs: pd.DataFrame, years: int) -> float | None:
    end = navs.index.max()
    start = end - pd.DateOffset(years=years)
    if start not in navs.index:
        return None
    return float(100 * ((navs.at[end, "nav"] / navs.at[start, "nav"]) ** (1 / years) - 1))


def _non_overlapping_anchors(anchors: pd.DatetimeIndex, years: int) -> pd.DatetimeIndex:
    kept = []
    next_allowed: pd.Timestamp | None = None
    for anchor in anchors:
        if next_allowed is None or anchor >= next_allowed:
            kept.append(anchor)
            next_allowed = anchor + pd.DateOffset(years=years)
    return pd.DatetimeIndex(kept)


def _correlation(x: pd.Series, y: pd.Series, method: str) -> float | None:
    if x.nunique() < 2 or y.nunique() < 2:
        return None
    value = x.corr(y, method=method)
    return None if pd.isna(value) else float(value)


def _format_metric(value: object, format_spec: str) -> str:
    return f"{value:{format_spec}}" if isinstance(value, (float, np.floating)) else "—"
