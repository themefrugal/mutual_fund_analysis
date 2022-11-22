# Base file for the streamlit application
# The idea is to use the R functions directly from this Python file

import pandas as pd
import urllib.request, json
import plotly_express as px
import plotly.figure_factory as ff
import streamlit as st
import numpy as np
from pyxirr import xirr

@st.cache
def get_scheme_codes():
    with urllib.request.urlopen('https://api.mfapi.in/mf') as url:
        data = json.load(url)
    df_mfs = pd.DataFrame(data)
    return df_mfs

@st.cache(allow_output_mutation=True)
def get_nav(scheme_code = '122639'):
    # scheme_code = '122639'
    mf_url = 'https://api.mfapi.in/mf/' + scheme_code
    with urllib.request.urlopen(mf_url) as url:
        data = json.load(url)

    df_navs = pd.DataFrame(data['data'])
    df_navs['date'] = pd.to_datetime(df_navs.date, format='%d-%m-%Y')
    df_navs['nav'] = df_navs['nav'].astype(float)
    df_navs = df_navs.sort_values(['date']).set_index(['date'])
    df_dates = pd.DataFrame(pd.date_range(start=df_navs.index.min(), end=df_navs.index.max()), columns=['date']).set_index(['date'])
    df_navs = df_navs.join(df_dates, how='outer').ffill().reset_index()
    return df_navs

@st.cache
def get_cagr(df_navs_orig, num_years = 1):
    df_navs = df_navs_orig.copy()
    df_navs['prev_nav'] = df_navs.nav.shift(365 * num_years)
    df_navs = df_navs.dropna()
    df_navs['returns'] = df_navs['nav'] / df_navs['prev_nav'] - 1
    df_navs['cagr'] = 100 * ((1 + df_navs['returns']) ** (1 / num_years) - 1)
    df_navs['years'] = num_years
    df_cagr = df_navs[['date', 'years', 'cagr']]
    return df_cagr
# Here is the top level outline
# Multi page
# 1. Nav Charting
# 2. CAGR Analysis
# 3. Rolling Return Analysis
# 4. SIP Analysis
# 5. STP Analysis
# 6. SWP Analysis
# 7. Comparision of SIPs and SWPs across two or more mutual funds

df_mfs = get_scheme_codes()

sel_name = st.sidebar.selectbox("Mutual Fund:", df_mfs.schemeName.unique())
st.write(sel_name)
tab_nav, tab_cagr, tab_comp, tab_sip = st.tabs(["NAV", "CAGR", "Comparative Analysis", "SIP"])
# st.write(df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0])
sel_code = df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0]

df_navs = get_nav(str(sel_code))
with tab_nav:
    fig1 = px.line(df_navs, x='date', y='nav', log_y=True)
    sub_name = ": " + sel_name if False else ""
    st.write('NAV Chart' + sub_name)
    st.plotly_chart(fig1)

with tab_cagr:
    years = [x for x in range(1, 11)]
    list_cagr = []
    for y in years:
        df_cagr = get_cagr(df_navs, y)
        list_cagr.append(df_cagr)
    df_cagrs = pd.concat(list_cagr)
    st.write('CAGR Chart' + sub_name)
    fig2 = px.line(df_cagrs, x='date', y='cagr', color='years')
    st.plotly_chart(fig2)
    dfx = df_cagrs[['date', 'years', 'cagr']].groupby('years').describe().reset_index()
    dfx.columns = [[a for (a, b) in dfx.columns][0]] + [a for a in dfx.columns.droplevel()][1:]
    st.write('CAGR - Min, Median and Max')
    st.write(dfx)

with tab_comp:
    # Comparisons with other mutual funds
    names_comp = st.multiselect("Select Mutual Funds for Comparison:", df_mfs.schemeName.unique())
    all_names = [sel_name] + names_comp
    codes_comp = [df_mfs[df_mfs['schemeName'] == x].schemeCode.to_list()[0] for x in all_names]

    list_navs = []
    list_cagrs = []
    for name in all_names:
        code = df_mfs[df_mfs['schemeName'] == name].schemeCode.to_list()[0]
        df_nav_comp = get_nav(str(code))
        years = [x for x in range(1, 11)]
        list_cagr = []
        for y in years:
            df_cagr = get_cagr(df_nav_comp, y)
            list_cagr.append(df_cagr)
        df_cagrs_comp = pd.concat(list_cagr)

        df_nav_comp = df_nav_comp.set_index('date')
        df_nav_comp = df_nav_comp.rename(columns={'nav': name})
        list_navs.append(df_nav_comp)

        df_cagrs_comp = df_cagrs_comp.set_index(['date', 'years'])
        df_cagrs_comp = df_cagrs_comp.rename(columns={'cagr': name})
        list_cagrs.append(df_cagrs_comp)

    df_nav_all = pd.concat(list_navs, axis=1).dropna()
    df_cagr_all = pd.concat(list_cagrs, axis=1).dropna()

    df_navs_date = df_nav_all.reset_index()
    min_date = df_navs_date['date'].min()
    max_date = df_navs_date['date'].max()
    st.write('Cumulative Returns Comparisons')
    from_date = st.date_input('From Date:', value=min_date, min_value=min_date, max_value=max_date)
    df_nav_all = df_navs_date[df_navs_date['date'] >= np.datetime64(from_date)].set_index('date')

    df_rebased = df_nav_all.div(df_nav_all.iloc[0]).reset_index()
    df_rebased_long = pd.melt(df_rebased, id_vars='date', value_vars=all_names, var_name='mf', value_name='nav')

    fig3 = px.line(df_rebased_long, x='date', y='nav', log_y=True, color='mf')
    fig3.update_layout(legend=dict(yanchor="bottom", y=0, xanchor="left", x=0.5))
    st.plotly_chart(fig3)

    df_cagr_wide = df_cagr_all.reset_index()
    df_cagr_long = pd.melt(df_cagr_wide, id_vars=['date', 'years'], value_vars=all_names, var_name='mf', value_name='cagr')

    st.write("Rolling CAGR Comparison")
    sel_year = st.number_input('Investment Duration (Number of Years):', value=1, min_value=1, max_value=10, step=1)
    df_cagr_plot = df_cagr_long[df_cagr_long['years'] == sel_year]
    fig4 = px.line(df_cagr_plot, x='date', y='cagr', color='mf')
    fig4.update_layout(legend=dict(yanchor="bottom", y=-0.5, xanchor="left", x=0))
    st.plotly_chart(fig4)

    st.write('Draw Down Comparison')
    df_rebased_long['cum_max'] = df_rebased_long.groupby('mf').nav.cummax()
    df_rebased_long['draw_down'] = (df_rebased_long['nav'] - df_rebased_long['cum_max']) / df_rebased_long['cum_max']
    fig5 = px.line(df_rebased_long, x="date", y="draw_down", color="mf")
    fig5.update_layout(legend=dict(yanchor="bottom", y=-0.5, xanchor="left", x=0))
    st.plotly_chart(fig5)

with tab_sip:
    start_date = pd.to_datetime('2006-05-01')
    end_date = pd.to_datetime('2020-04-01')
    df_dates = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq='M'))
    df_dates.columns = ['date']

    df_cf = df_navs.merge(df_dates, on='date')
    df_cf['amount'] = 1000
    df_cf['units'] = df_cf['amount'] / df_cf['nav']

    df_investment = df_cf[['date', 'amount']]
    df_redemption = pd.DataFrame(
        [{'date': df_cf.iloc[-1:].date.values[0],
          'amount': -df_cf['units'].sum() * df_cf.iloc[-1:].nav.values[0]}])
    df_irr = pd.concat([df_investment, df_redemption]).reset_index(drop=True)

    xirr_value = xirr(df_irr[['date', 'amount']]) * 100
    st.write(xirr_value)
    st.write(df_irr)
