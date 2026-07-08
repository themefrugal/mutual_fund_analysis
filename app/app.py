from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.core.cagr import get_cagr  # noqa: E402
from api.core.compare import (  # noqa: E402
    build_comparison_data,
    drawdown_long,
    growth_long,
    rebased_nav_long,
    rolling_cagr_long,
)
from api.core.common import validate_date_range  # noqa: E402
from api.core.funds import get_scheme_codes as core_get_scheme_codes  # noqa: E402
from api.core.nav import get_nav as core_get_nav  # noqa: E402
from api.core.rolling import rolling_sip_xirr  # noqa: E402
from api.core.sip import sip_analysis  # noqa: E402
from api.core.stp import stp_analysis  # noqa: E402
from api.core.swp import swp_analysis  # noqa: E402


st.set_page_config(page_title="Mutual Fund Analysis", layout="wide")


@st.cache_data(ttl=12 * 60 * 60)
def get_scheme_codes() -> pd.DataFrame:
    return core_get_scheme_codes()


@st.cache_data(ttl=12 * 60 * 60)
def get_nav(scheme_code: str) -> pd.DataFrame:
    return core_get_nav(scheme_code)


def show_error(exc: Exception) -> None:
    st.error(str(exc))


def as_date(value: pd.Timestamp) -> dt.date:
    return pd.Timestamp(value).date()


def get_selected_code(df_mfs: pd.DataFrame, scheme_name: str) -> str:
    matches = df_mfs.loc[df_mfs["schemeName"] == scheme_name, "schemeCode"]
    if matches.empty:
        raise ValueError(f"Could not resolve scheme code for {scheme_name}.")
    return str(matches.iloc[0]).strip()


def parse_weights(weight_text: str, expected_count: int) -> list[float]:
    try:
        weights = [float(x.strip()) for x in weight_text.split(",") if x.strip()]
    except ValueError as exc:
        raise ValueError("Weights must be comma-separated numbers.") from exc
    if len(weights) != expected_count:
        raise ValueError(f"Enter exactly {expected_count} weights.")
    if any(w < 0 for w in weights):
        raise ValueError("Weights cannot be negative.")
    if abs(sum(weights) - 100.0) > 0.01:
        raise ValueError("Weights must add up to 100.0.")
    return weights


def records_to_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def render_nav(df_navs: pd.DataFrame) -> None:
    st.write("NAV Data")
    st.dataframe(df_navs, use_container_width=True)
    nav_log_y = st.checkbox("Log Y-Axis", value=True, key="nav_log_y")
    st.plotly_chart(px.line(df_navs, x="date", y="nav", log_y=nav_log_y), use_container_width=True)


def render_cagr(df_navs: pd.DataFrame) -> None:
    frames = [get_cagr(df_navs, y) for y in range(1, 11)]
    df_cagrs = pd.concat(frames, ignore_index=True)
    if df_cagrs.empty:
        st.warning("This fund does not have enough NAV history for CAGR analysis.")
        return

    st.write("CAGR Data")
    st.dataframe(df_cagrs, use_container_width=True)
    st.plotly_chart(px.line(df_cagrs, x="date", y="cagr", color="years"), use_container_width=True)

    stats = df_cagrs.groupby("years")["cagr"].describe().reset_index()
    st.write("CAGR - Min, Median and Max")
    st.dataframe(stats, use_container_width=True)

    df_yield = df_cagrs.groupby("years")["cagr"].agg(["min", "max"]).reset_index()
    df_yield_long = pd.melt(df_yield, id_vars="years", value_vars=["min", "max"], var_name="stat", value_name="cagr")
    st.write("Equity Yield Curve (Min/Max CAGR by Holding Period)")
    st.plotly_chart(px.line(df_yield_long, x="years", y="cagr", color="stat", markers=True), use_container_width=True)

    hist_data = []
    labels = []
    for y in range(1, 11):
        values = df_cagrs.loc[df_cagrs["years"] == y, "cagr"].dropna().values
        if len(values) > 1:
            hist_data.append(values)
            labels.append(f"{y}Y")
    if hist_data:
        st.write("CAGR Distribution (Density)")
        st.plotly_chart(ff.create_distplot(hist_data, labels, show_hist=False, show_rug=False), use_container_width=True)

    valid_years = sorted(df_cagrs.loc[df_cagrs["cagr"].notna(), "years"].unique().tolist())
    if not valid_years:
        return
    sel_year = st.selectbox("Year for Histogram:", valid_years, index=0)
    df_hist = df_cagrs.loc[df_cagrs["years"] == sel_year, "cagr"].dropna()
    fig_hist = go.Figure(go.Histogram(x=df_hist, nbinsx=50))
    for val, color, label, dash in [
        (df_hist.mean(), "black", "Mean", "dash"),
        (df_hist.median(), "red", "Median", "dash"),
        (df_hist.quantile(0.25), "blue", "P25", "dot"),
        (df_hist.quantile(0.75), "blue", "P75", "dot"),
        (df_hist.min(), "black", "Min", "solid"),
        (df_hist.max(), "black", "Max", "solid"),
    ]:
        if pd.notna(val):
            fig_hist.add_vline(x=val, line_dash=dash, line_color=color, annotation_text=label)
    st.write(f"CAGR Histogram ({sel_year}Y)")
    st.plotly_chart(fig_hist, use_container_width=True)


def render_comparison(df_mfs: pd.DataFrame, sel_name: str) -> None:
    check_combo = st.checkbox("Compare against a combination of MF?", value=False)
    names_comp = st.multiselect("Select Mutual Funds to Compare:", df_mfs.schemeName.unique(), max_selections=5)
    all_names = [sel_name] + [name for name in names_comp if name != sel_name]
    scheme_codes = [get_selected_code(df_mfs, name) for name in all_names]
    weights = None

    if check_combo:
        if not names_comp:
            st.warning("Select at least one comparison fund to build a weighted combo.")
            return
        default = ", ".join([str(round(100 / len(names_comp), 2))] * len(names_comp))
        wt_text = st.text_input("Weightage for comparison funds only:", value=default)
        try:
            weights = parse_weights(wt_text, len(names_comp))
            st.success("Weights add up to 100.0.")
            st.caption("The selected/base fund is excluded from the combo.")
        except ValueError as exc:
            st.error(str(exc))
            return

    try:
        comp = build_comparison_data(scheme_codes, combo_weights=weights)
    except ValueError as exc:
        st.warning(str(exc))
        return

    recovery = pd.DataFrame(comp.drawdown_recovery)
    if not recovery.empty:
        recovery = recovery.rename(
            columns={
                "name": "Fund",
                "latest_date": "LatestDate",
                "latest_nav": "LatestNAV",
                "last_seen_date": "BackToDate",
                "last_seen_nav": "NAVThen",
            }
        )
        st.write("Drawdown Recovery - Current NAV Level Last Seen On")
        st.dataframe(recovery, use_container_width=True)

    min_date = as_date(comp.nav_wide.index.min())
    max_date = as_date(comp.nav_wide.index.max())
    st.write("Cumulative Returns Comparisons")
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date:", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        log_y = st.checkbox("Log Y-Axis", value=True, key="cumr_log_y")

    try:
        df_rebased_long = rebased_nav_long(comp, from_date)
    except ValueError as exc:
        st.warning(str(exc))
        return

    st.plotly_chart(
        px.line(df_rebased_long, x="date", y="rebased_nav", color="mf", log_y=log_y),
        use_container_width=True,
    )

    st.write("Rolling CAGR Comparison")
    sel_year = st.number_input("Investment Duration (Number of Years):", value=1, min_value=1, max_value=10, step=1)
    df_cagr_all = rolling_cagr_long(comp, years=int(sel_year))
    if df_cagr_all.empty:
        st.warning("Not enough history for the selected rolling CAGR period.")
    else:
        st.plotly_chart(px.line(df_cagr_all, x="date", y="cagr", color="mf"), use_container_width=True)

    st.write("Draw Down Comparison")
    df_drawdown = drawdown_long(df_rebased_long)
    st.plotly_chart(px.line(df_drawdown, x="date", y="draw_down", color="mf"), use_container_width=True)

    st.write("Comparative Growth - Value of Rs 1000 Invested")
    sel_growth = st.number_input("Holding Period (Years):", value=5, min_value=1, max_value=10, step=1, key="growth_year")
    df_growth = growth_long(comp, holding_years=int(sel_growth))
    if not df_growth.empty:
        st.plotly_chart(px.line(df_growth, x="date", y="end_value", color="mf"), use_container_width=True)
    else:
        st.warning("Not enough history for the selected holding period.")

def render_sip(sel_code: str, df_navs: pd.DataFrame) -> None:
    min_date = as_date(df_navs["date"].min())
    max_date = as_date(df_navs["date"].max())
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start Date:", max(min_date, dt.date(2006, 5, 1)), min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date:", min(max_date, dt.date(2022, 4, 1)), min_value=min_date, max_value=max_date)
    with col3:
        monthly_amount = st.number_input("Monthly SIP Amount:", value=1000, min_value=100, step=100)
    step_up_pct = st.number_input("Annual Step-up (%):", value=5.0, min_value=0.0, step=1.0)

    try:
        validate_date_range(start_date, end_date)
        result = sip_analysis(sel_code, start_date, end_date, float(monthly_amount), float(step_up_pct))
    except Exception as exc:
        show_error(exc)
        return

    st.metric("XIRR (%)", f"{result['xirr']:.2f}%" if result["xirr"] is not None else "N/A")
    df_series = records_to_df(result["series"])
    if df_series.empty:
        st.warning("No SIP series could be generated.")
        return
    df_long = pd.melt(df_series[["date", "invested_amount", "current_value"]], id_vars="date", var_name="component", value_name="amount")
    st.write("Invested Amount vs Current Value")
    st.plotly_chart(px.line(df_long, x="date", y="amount", color="component"), use_container_width=True)

    st.write("Unit Accumulation - Normalized")
    df_norm = df_series.copy()
    df_norm["invested_amount"] = df_norm["invested_amount"] / df_norm["invested_amount"].iloc[-1]
    df_norm["cum_units"] = df_norm["cum_units"] / df_norm["cum_units"].iloc[-1]
    df_norm_long = pd.melt(df_norm[["date", "invested_amount", "cum_units"]], id_vars="date", var_name="component", value_name="proportion")
    st.plotly_chart(px.line(df_norm_long, x="date", y="proportion", color="component"), use_container_width=True)

    st.write("---")
    st.write("Rolling SIP XIRR Distribution")
    col1, col2, col3 = st.columns(3)
    with col1:
        window_years = st.number_input("SIP Duration (years):", value=7, min_value=1, max_value=20, step=1)
    with col2:
        roll_amount = st.number_input("Rolling Monthly SIP Amount:", value=1000, min_value=100, step=100)
    with col3:
        roll_step_up = st.number_input("Rolling Annual Step-up (%):", value=0.0, min_value=0.0, step=1.0)
    try:
        df_roll = rolling_sip_xirr(df_navs, int(window_years), float(roll_amount), float(roll_step_up)).dropna(subset=["xirr"])
    except Exception as exc:
        show_error(exc)
        return
    if df_roll.empty:
        st.warning("No valid rolling windows found for this duration and date range.")
        return
    st.plotly_chart(px.histogram(df_roll, x="xirr", nbins=40, labels={"xirr": "XIRR (%)"}), use_container_width=True)
    st.plotly_chart(px.line(df_roll, x="startDate", y="xirr", labels={"startDate": "SIP Start Date", "xirr": "XIRR (%)"}), use_container_width=True)
    st.dataframe(df_roll[["startDate", "endDate", "xirr"]].describe(), use_container_width=True)


def render_swp(sel_code: str, df_navs: pd.DataFrame) -> None:
    min_date = as_date(df_navs["date"].min())
    max_date = as_date(df_navs["date"].max())
    col1, col2 = st.columns(2)
    with col1:
        inv_amount = st.number_input("Amount Invested:", value=100000, min_value=1000, step=10000)
        start_date = st.date_input("Start Date:", max(min_date, dt.date(2005, 4, 1)), min_value=min_date, max_value=max_date, key="st_date_swp")
    with col2:
        red_amount = st.number_input("Monthly Withdrawn:", value=1000, min_value=100, step=100)
        end_date = st.date_input("End Date:", min(max_date, dt.date(2022, 4, 1)), min_value=min_date, max_value=max_date, key="end_date_swp")
    try:
        result = swp_analysis(sel_code, start_date, end_date, float(inv_amount), float(red_amount))
    except Exception as exc:
        show_error(exc)
        return
    st.metric("XIRR (%)", f"{result['xirr']:.2f}%" if result["xirr"] is not None else "N/A")
    if result.get("depleted_on"):
        st.warning(f"Corpus depleted on {result['depleted_on']}; later withdrawals are capped at available value.")
    df_series = records_to_df(result["series"])
    df_long = pd.melt(df_series[["date", "inv_value", "cur_value", "cum_amount", "total"]], id_vars="date", var_name="component", value_name="amount")
    st.plotly_chart(px.line(df_long, x="date", y="amount", color="component"), use_container_width=True)


def render_stp(df_mfs: pd.DataFrame, sel_name: str, sel_code: str) -> None:
    st.write(f"Target Fund: **{sel_name}**")
    source_name = st.selectbox("Source Fund (transfer FROM):", df_mfs.schemeName.unique(), key="stp_source")
    col1, col2 = st.columns(2)
    with col1:
        inv_amount = st.number_input("Amount Invested in Source:", value=100000, min_value=1000, step=10000, key="stp_inv")
        start_date = st.date_input("Start Date:", dt.date(2010, 1, 1), key="stp_start")
    with col2:
        transfer = st.number_input("Monthly Transfer Amount:", value=5000, min_value=100, step=500, key="stp_transfer")
        end_date = st.date_input("End Date:", dt.date(2022, 1, 1), key="stp_end")
    try:
        source_code = get_selected_code(df_mfs, source_name)
        result = stp_analysis(source_code, sel_code, start_date, end_date, float(inv_amount), float(transfer))
    except Exception as exc:
        show_error(exc)
        return
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("XIRR (%)", f"{result['xirr']:.2f}%" if result["xirr"] is not None else "N/A")
    m2.metric("Final Source Value", f"{result['source_final']:,.0f}")
    m3.metric("Final Target Value", f"{result['target_final']:,.0f}")
    m4.metric("Total Portfolio Value", f"{result['total_final']:,.0f}")

    df_series = records_to_df(result["series"])
    df_val_long = pd.melt(df_series[["date", "value_src", "value_tgt", "total_value"]], id_vars="date", var_name="component", value_name="value")
    st.write("Portfolio Value Over Time")
    st.plotly_chart(px.line(df_val_long, x="date", y="value", color="component"), use_container_width=True)
    df_units_long = pd.melt(df_series[["date", "src_units_norm", "tgt_units_norm"]], id_vars="date", var_name="component", value_name="proportion")
    st.write("Units Tracker (Normalised)")
    st.plotly_chart(px.line(df_units_long, x="date", y="proportion", color="component"), use_container_width=True)


df_mfs = get_scheme_codes()
if df_mfs.empty:
    st.error("No mutual fund catalogue data is available.")
    st.stop()

scheme_names = sorted(df_mfs.schemeName.dropna().unique().tolist())
sel_name = st.sidebar.selectbox("Select a Mutual Fund:", scheme_names, index=None, placeholder="Choose a fund")
st.sidebar.write(
    "Visualize historical NAV, rolling CAGR, SIP, SWP, STP, and comparative performance for Indian mutual funds."
)

if not sel_name:
    st.stop()

try:
    sel_code = get_selected_code(df_mfs, sel_name)
    df_navs = get_nav(sel_code)
except Exception as exc:
    show_error(exc)
    st.stop()

st.title(sel_name)
page = st.radio(
    "Analysis",
    ["Home / NAV History", "CAGR Charts", "Comparative Analysis", "SIP", "SWP", "STP"],
    horizontal=True,
)

if page == "Home / NAV History":
    render_nav(df_navs)
elif page == "CAGR Charts":
    render_cagr(df_navs)
elif page == "Comparative Analysis":
    render_comparison(df_mfs, sel_name)
elif page == "SIP":
    render_sip(sel_code, df_navs)
elif page == "SWP":
    render_swp(sel_code, df_navs)
elif page == "STP":
    render_stp(df_mfs, sel_name, sel_code)

