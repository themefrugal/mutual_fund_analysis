from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .cagr import get_cagr
from .common import clean_float
from .funds import get_scheme_codes
from .nav import get_nav


@dataclass
class ComparisonData:
    nav_wide: pd.DataFrame
    fund_names: list[str]
    plot_names: list[str]
    drawdown_recovery: list[dict]


def validate_combo_weights(weights: list[float] | None, expected_count: int) -> None:
    if weights is None:
        return
    if len(weights) != expected_count:
        raise ValueError("combo_weights length must match comparison funds.")
    if any(weight < 0 for weight in weights):
        raise ValueError("combo_weights cannot contain negative values.")
    if abs(sum(weights) - 100.0) > 0.01:
        raise ValueError("combo_weights must sum to 100.0.")


def build_comparison_data(
    scheme_codes: list[str],
    combo_weights: list[float] | None = None,
) -> ComparisonData:
    if not scheme_codes:
        raise ValueError("Select at least one fund for comparison.")
    if combo_weights is not None and len(scheme_codes) < 2:
        raise ValueError("Select at least one comparison fund to build a weighted combo.")
    validate_combo_weights(combo_weights, max(len(scheme_codes) - 1, 0))

    df_mfs = get_scheme_codes()
    list_navs: list[pd.DataFrame] = []
    fund_names: list[str] = []
    recovery: list[dict] = []

    for code in scheme_codes:
        scheme_code = str(code).strip()
        df_nav = get_nav(scheme_code)
        name = _resolve_fund_name(df_mfs, scheme_code)
        name = _unique_name(name, fund_names)
        fund_names.append(name)
        list_navs.append(df_nav.set_index("date").rename(columns={"nav": name})[[name]])
        recovery.append(drawdown_recovery(df_nav, name))

    df_nav_all = pd.concat(list_navs, axis=1)
    plot_names = list(fund_names)

    if combo_weights is not None:
        wt_cols = []
        combo_fund_names = fund_names[1:]
        for name, weight in zip(combo_fund_names, combo_weights):
            col = f"{name}_wt"
            df_nav_all[col] = df_nav_all[name] * weight / 100.0
            wt_cols.append(col)
        df_nav_all["combo"] = df_nav_all[wt_cols].sum(axis=1)
        plot_names.append("combo")

    df_nav_all = df_nav_all[plot_names].dropna()
    if df_nav_all.empty:
        raise ValueError("No overlapping date range found for the selected funds.")

    return ComparisonData(
        nav_wide=df_nav_all,
        fund_names=fund_names,
        plot_names=plot_names,
        drawdown_recovery=recovery,
    )


def drawdown_recovery(df_nav: pd.DataFrame, name: str) -> dict:
    latest = df_nav.iloc[-1]
    earlier = df_nav.loc[df_nav["nav"] > latest["nav"]]
    last_seen_date = None
    last_seen_nav = None
    if not earlier.empty:
        row = earlier.iloc[0]
        last_seen_date = row["date"].strftime("%Y-%m-%d")
        last_seen_nav = clean_float(row["nav"])
    return {
        "name": name,
        "latest_date": latest["date"].strftime("%Y-%m-%d"),
        "latest_nav": clean_float(latest["nav"]),
        "last_seen_date": last_seen_date,
        "last_seen_nav": last_seen_nav,
    }


def rebased_nav_long(data: ComparisonData, from_date: date) -> pd.DataFrame:
    df_filtered = data.nav_wide.loc[data.nav_wide.index >= pd.Timestamp(from_date), data.plot_names]
    if df_filtered.empty:
        raise ValueError("No data available for the selected funds after from_date.")
    df_rebased = df_filtered.div(df_filtered.iloc[0]).reset_index()
    return df_rebased.melt(
        id_vars="date",
        value_vars=data.plot_names,
        var_name="mf",
        value_name="rebased_nav",
    )


def drawdown_long(rebased_long: pd.DataFrame) -> pd.DataFrame:
    df = rebased_long.rename(columns={"rebased_nav": "nav"}).copy()
    df["cum_max"] = df.groupby("mf")["nav"].cummax()
    df["draw_down"] = (df["nav"] - df["cum_max"]) / df["cum_max"]
    return df[["date", "mf", "draw_down"]]


def rolling_cagr_long(
    data: ComparisonData,
    from_date: date | None = None,
    years: int | None = None,
) -> pd.DataFrame:
    selected_years = [years] if years is not None else list(range(1, 11))
    frames = []
    from_ts = pd.Timestamp(from_date) if from_date is not None else None
    for name in data.plot_names:
        df_single = data.nav_wide[[name]].reset_index().rename(columns={name: "nav"})
        for y in selected_years:
            df_cagr = get_cagr(df_single, int(y))
            if from_ts is not None:
                df_cagr = df_cagr[df_cagr["date"] >= from_ts]
            if not df_cagr.empty:
                df_cagr["mf"] = name
                frames.append(df_cagr)
    if not frames:
        return pd.DataFrame(columns=["date", "years", "cagr", "mf"])
    return pd.concat(frames, ignore_index=True)


def growth_long(
    data: ComparisonData,
    from_date: date | None = None,
    holding_years: int | None = None,
) -> pd.DataFrame:
    selected_years = [holding_years] if holding_years is not None else list(range(1, 11))
    frames = []
    from_ts = pd.Timestamp(from_date) if from_date is not None else None
    for name in data.plot_names:
        df_single = data.nav_wide[[name]].reset_index().rename(columns={name: "nav"})
        for y in selected_years:
            df_g = df_single.copy()
            df_g["prev_nav"] = df_g["nav"].shift(365 * int(y))
            df_g = df_g.dropna()
            if from_ts is not None:
                df_g = df_g[df_g["date"] >= from_ts]
            if not df_g.empty:
                df_g["end_value"] = 1000.0 * df_g["nav"] / df_g["prev_nav"]
                df_g["mf"] = f"{name}|{y}Y" if holding_years is None else name
                frames.append(df_g[["date", "mf", "end_value"]])
    if not frames:
        return pd.DataFrame(columns=["date", "mf", "end_value"])
    return pd.concat(frames, ignore_index=True)


def compare_analysis(
    scheme_codes: list[str],
    from_date: date,
    combo_weights: list[float] | None = None,
) -> dict:
    data = build_comparison_data(scheme_codes, combo_weights)
    rebased = rebased_nav_long(data, from_date)
    drawdown = drawdown_long(rebased)
    rolling_cagr = rolling_cagr_long(data, from_date=from_date)
    growth = growth_long(data, from_date=from_date)

    return {
        "funds": [
            {
                "name": name,
                "series": [
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "rebased_nav": clean_float(row["rebased_nav"]),
                    }
                    for _, row in rebased.loc[rebased["mf"] == name].iterrows()
                ],
            }
            for name in data.plot_names
        ],
        "drawdown": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "mf": row["mf"],
                "draw_down": clean_float(row["draw_down"]),
            }
            for _, row in drawdown.iterrows()
        ],
        "rolling_cagr": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "years": int(row["years"]),
                "mf": row["mf"],
                "cagr": clean_float(row["cagr"]),
            }
            for _, row in rolling_cagr.iterrows()
        ],
        "drawdown_recovery": data.drawdown_recovery,
        "growth_series": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "mf": row["mf"],
                "end_value": clean_float(row["end_value"]),
            }
            for _, row in growth.iterrows()
        ],
    }


def _resolve_fund_name(df_mfs: pd.DataFrame, scheme_code: str) -> str:
    matches = df_mfs.loc[df_mfs["schemeCode"].astype(str) == scheme_code, "schemeName"]
    return str(matches.iloc[0]) if not matches.empty else scheme_code


def _unique_name(name: str, existing: list[str]) -> str:
    if name not in existing:
        return name
    counter = 2
    candidate = f"{name} ({counter})"
    while candidate in existing:
        counter += 1
        candidate = f"{name} ({counter})"
    return candidate
