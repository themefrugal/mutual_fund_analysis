"""Presentation helpers for the Streamlit application only."""

from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st


PALETTE = ["#2563eb", "#0f766e", "#9333ea", "#d97706", "#db2777", "#475569", "#0891b2", "#65a30d", "#b45309", "#a855f7"]
PAGES = {
    "Home / NAV History": ("NAV history", "Explore the fund’s historical net asset value."),
    "CAGR Charts": ("Rolling returns", "Understand how returns vary across investment horizons."),
    "Past vs Forward Returns": ("Past vs forward returns", "Explore the historical relationship between trailing and subsequent returns."),
    "Comparative Analysis": ("Fund comparison", "Compare growth, rolling returns and drawdowns across funds."),
    "SIP": ("Systematic investment", "Explore regular investments, annual step-ups and rolling SIP outcomes."),
    "SWP": ("Systematic withdrawal", "Explore withdrawals and the value of the remaining corpus over time."),
    "STP": ("Systematic transfer", "Follow transfers between funds and the combined portfolio over time."),
}
LABELS = {
    "date": "Date", "nav": "NAV (₹)", "cagr": "CAGR (%)", "years": "Holding period (years)",
    "stat": "Statistic", "min": "Minimum", "max": "Maximum", "mf": "Fund",
    "rebased_nav": "Growth multiple", "draw_down": "Drawdown", "end_value": "Investment value (₹)",
    "component": "", "amount": "Amount (₹)", "value": "Value (₹)", "proportion": "Normalised value",
    "invested_amount": "Amount invested", "current_value": "Current value", "cum_units": "Accumulated units",
    "inv_value": "Initial investment", "cur_value": "Remaining corpus", "cum_amount": "Total withdrawn",
    "total": "Corpus + withdrawals", "value_src": "Source fund", "value_tgt": "Target fund",
    "total_value": "Total portfolio", "src_units_norm": "Source units", "tgt_units_norm": "Target units",
    "xirr": "XIRR (%)", "startDate": "SIP start date", "count": "Occurrences", "combo": "Weighted combination",
}


def apply_style() -> None:
    css = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand() -> None:
    st.markdown('<div class="mf-brand"><span class="mf-mark">M</span><div>Mutual Fund Analysis'
                '<small>RESEARCH WORKSPACE</small></div></div>', unsafe_allow_html=True)


def welcome() -> None:
    st.write("<br>", unsafe_allow_html=True)
    st.markdown('<div class="mf-eyebrow">INDIAN MUTUAL FUNDS</div>', unsafe_allow_html=True)
    st.title("A workbench to analyze the Indian mutual fund landscape.")
    st.markdown("Explore fund history, compare performance and understand investment scenarios in one research workspace.")
    st.info("Choose a mutual fund in the sidebar to begin. On a small screen, open the sidebar using the top-left control.")
    for column, number, title, description in zip(
        st.columns(3), ["01", "02", "03"],
        ["Understand returns", "Compare funds", "Explore scenarios"],
        ["NAV history, rolling CAGR and past vs forward returns.",
         "Growth, drawdowns and weighted fund combinations.",
         "Systematic investment, withdrawal and transfer plans."],
    ):
        with column.container(border=True, key=f"mf-panel-welcome-{number}"):
            st.caption(number)
            st.subheader(title)
            st.write(description)
    st.caption("Historical data · Interactive analysis · Indian mutual funds")


def page_header(page: str, fund: str, dates) -> None:
    title, description = PAGES[page]
    st.markdown('<div class="mf-eyebrow">FUND RESEARCH</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)
    coverage = f"{dates.min():%d %b %Y} – {dates.max():%d %b %Y}"
    st.markdown(f'<div class="mf-context"><div><span class="mf-eyebrow">SELECTED FUND</span>'
                f'<div class="mf-fund">{escape(fund)}</div></div>'
                f'<div class="mf-coverage">NAV history<br><strong>{coverage}</strong></div></div>',
                unsafe_allow_html=True)


def section(title: str, description: str | None = None) -> None:
    st.subheader(title)
    if description:
        st.caption(description)


def data_table(frame, *, width="stretch", column_config=None) -> None:
    """Use readable display labels while leaving data and exports untouched."""
    labels = {}
    for column in frame.columns:
        if isinstance(column, str):
            label = LABELS.get(column, column.replace("_", " ").capitalize())
            labels[column] = label.replace("cagr", "CAGR").replace("xirr", "XIRR").replace("nav", "NAV")
    labels.update(column_config or {})
    st.dataframe(frame, width=width, column_config=labels)


def plot_chart(fig: go.Figure, *, width="stretch", colors=None) -> None:
    """Style figures without changing their data, scales or interactive controls."""
    fig.update_layout(
        template="plotly_white", paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", size=12, color="#475569"),
        colorway=PALETTE, margin=dict(l=24, r=24, t=30, b=32),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, xanchor="left", title_text=""),
        hoverlabel=dict(bgcolor="#ffffff", font_size=13),
    )
    for axis in list(fig.select_xaxes()) + list(fig.select_yaxes()):
        original = axis.title.text
        if original in LABELS:
            axis.title.text = LABELS[original]
        axis.update(gridcolor="#edf1f5", zerolinecolor="#cbd5e1", automargin=True)
        if original == "draw_down":
            axis.update(tickformat=".0%")
        elif original in {"cagr", "xirr"}:
            axis.update(ticksuffix="%")
    for index, trace in enumerate(fig.data):
        original = trace.name
        trace.name = LABELS.get(original, original)
        color = (colors or {}).get(original, PALETTE[index % len(PALETTE)])
        # Preserve fitted-line styling and per-point colour encodings.
        if trace.type in {"scatter", "scattergl", "box", "histogram"} and original != "Linear fit":
            if trace.type in {"scatter", "scattergl"} and trace.mode and "lines" in trace.mode:
                trace.line.color = color
                trace.line.width = 2.2
            if trace.marker.color is None or isinstance(trace.marker.color, str):
                trace.marker.color = color
        if trace.hovertemplate:
            for raw, label in LABELS.items():
                trace.hovertemplate = trace.hovertemplate.replace(f"{raw}=", f"{label}=")
    st.plotly_chart(fig, width=width, theme=None)
