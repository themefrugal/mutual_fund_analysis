# Base file for the streamlit application
# The idea is to use the R functions directly from this Python file
# Need a complete listing of to-do and pending activities

# NAV History from AMFI can be downloaded from
# https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?mf=64&frmdt=01-Feb-2023&todt=21-Feb-2023

import pandas as pd
import urllib.request, json
import plotly_express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import streamlit as st
import numpy as np
from pyxirr import xirr
import datetime
import requests
from io import BytesIO
import re

@st.cache_data
def get_scheme_codes_old():
    with urllib.request.urlopen('https://api.mfapi.in/mf') as url:
        data = json.load(url)
    df_mfs = pd.DataFrame(data)
    return df_mfs

@st.cache_data
def download_latest_nav():
    url = "https://www.amfiindia.com/api/download-excel/latest-nav"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), header=None)
        return df
    except Exception as e:
        print(f"Error downloading NAV from AMFI: {e}")
        return None

@st.cache_data
def get_scheme_codes_from_amfi():
    df = download_latest_nav()
    if df is None:
        return pd.DataFrame(columns=['schemeCode', 'schemeISIN', 'schemeName'])
    list_code = []
    for idx, row in df.iterrows():
        row_values = [str(val) if pd.notna(val) else "" for val in row.values]
        if all(val == "" for val in row_values):
            continue
        scheme_name = str(row[1]) if pd.notna(row[1]) else ""
        scheme_isin = str(row[2]) if pd.notna(row[2]) else ""
        scheme_isin_reinv = str(row[3]) if pd.notna(row[3]) else ""
        is_valid_isin = scheme_isin and len(scheme_isin) > 10 and scheme_isin.startswith('INF')
        if scheme_name.startswith(('A.', 'B.', 'C.', 'D.')) and not is_valid_isin:
            continue
        if is_valid_isin:
            isin_to_use = scheme_isin
            if not isin_to_use or len(isin_to_use) < 10:
                if scheme_isin_reinv and len(scheme_isin_reinv) > 10:
                    isin_to_use = scheme_isin_reinv
            scheme_code = str(row[0]) if pd.notna(row[0]) else f"CODE_{idx}"
            scheme_name_clean = re.sub(r'\s+', ' ', scheme_name).strip()
            if isin_to_use and len(isin_to_use) > 10:
                list_code.append([scheme_code, isin_to_use, scheme_name_clean])
    df_codes = pd.DataFrame(list_code, columns=['schemeCode', 'schemeISIN', 'schemeName'])
    df_codes = df_codes.drop_duplicates(subset=['schemeISIN'], keep='first').reset_index(drop=True)
    return df_codes

@st.cache_data
def get_scheme_codes():
    df = get_scheme_codes_from_amfi()
    if not df.empty:
        return df
    # Fallback: read from local txt file
    with open('./data/mf_codes.txt', 'r') as fp:
        list_code = []
        line = fp.readline()
        while line:
            words = line.strip().split(';')
            if len(words) > 5:
                list_code.append([words[i] for i in [0, 1, 3]])
            line = fp.readline()
    df_codes = pd.DataFrame(list_code, columns=['schemeCode', 'schemeISIN', 'schemeName'])
    return df_codes

# @st.cache(allow_output_mutation=True)
@st.cache_data
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

@st.cache_data
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
# 1. Nav Charting (done)
# 2. CAGR Analysis (done)
# 3. Rolling Return Analysis (done)
# 4. SIP Analysis (need to integrate frequency adjustment, and analysis of different dates)
# 5. STP Analysis
# 6. SWP Analysis
# 7. Comparison of SIPs and SWPs across two or more mutual funds
# 8. AUM, Manager, Expense Ratios etc.
# 9. Holding Analysis
#10. Giving option to select only specific funds
#11. Create the large-mid-small analysis into a separate repository
#12. Check the same with US history
#13. Subset with select set of MF - with appropriate categories

df_mfs = get_scheme_codes()
scheme_names = df_mfs.schemeName.unique().tolist()
# scheme_names = sorted(scheme_names)
sel_names = st.sidebar.multiselect("Select a Mutual Fund:", scheme_names, max_selections=1)

st.sidebar.write("To visualize the historical net asset value (NAV) and compounded annual growth rate (CAGR) for various investment horizons and compare with other mutual funds.")
st.sidebar.write("This application also helps visualize the historical monthly SIP performance.")

if sel_names == []:
    st.stop()

sel_name = sel_names[0]
st.write(sel_name)
tab_nav, tab_cagr, tab_comp, tab_sip, tab_swp, tab_stp = \
    st.tabs(["Home / NAV History", "CAGR Charts", "Comparative Analysis", "SIP", "SWP", "STP"])
# st.write(df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0])
sel_code = df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0]

df_navs = get_nav(str(sel_code))
with tab_nav:
    sub_name = ": " + sel_name if False else ""
    st.write('NAV Data')
    st.dataframe(df_navs, use_container_width=True)
    nav_log_y = st.checkbox('Log Y-Axis', value=True, key='nav_log_y')
    fig1 = px.line(df_navs, x='date', y='nav', log_y=nav_log_y)
    st.write('NAV Chart' + sub_name)
    st.plotly_chart(fig1)

with tab_cagr:
    years = [x for x in range(1, 11)]
    list_cagr = []
    for y in years:
        df_cagr = get_cagr(df_navs, y)
        list_cagr.append(df_cagr)
    df_cagrs = pd.concat(list_cagr)
    st.write('CAGR Data')
    st.dataframe(df_cagrs, use_container_width=True)
    st.write('CAGR Chart' + sub_name)
    fig2 = px.line(df_cagrs, x='date', y='cagr', color='years')
    st.plotly_chart(fig2)
    dfx = df_cagrs[['years', 'cagr']].groupby('years').describe().reset_index()
    # st.write(df_cagrs)
    # st.write([[a for (a, b) in dfx.columns][0]] + [a for a in dfx.columns.droplevel()][1:])
    dfx.columns = [[a for (a, b) in dfx.columns][0]] + [a for a in dfx.columns.droplevel()][1:]
    st.write('CAGR - Min, Median and Max')
    st.write(dfx)

    df_yield = df_cagrs.groupby('years')['cagr'].agg(['min', 'max']).reset_index()
    df_yield_long = pd.melt(df_yield, id_vars='years', value_vars=['min', 'max'], var_name='stat', value_name='cagr')
    fig_yield = px.line(df_yield_long, x='years', y='cagr', color='stat', markers=True)
    st.write('Equity Yield Curve (Min/Max CAGR by Holding Period)')
    st.plotly_chart(fig_yield)

    hist_data = [df_cagrs[df_cagrs['years'] == y]['cagr'].dropna().values for y in range(1, 11)]
    group_labels = [f'{y}Y' for y in range(1, 11)]
    fig_density = ff.create_distplot(hist_data, group_labels, show_hist=False, show_rug=False)
    st.write('CAGR Distribution (Density)')
    st.plotly_chart(fig_density)

    sel_year_hist = st.selectbox('Year for Histogram:', list(range(1, 11)), index=0)
    df_hist = df_cagrs[df_cagrs['years'] == sel_year_hist]['cagr'].dropna()
    mean_v, median_v = df_hist.mean(), df_hist.median()
    p25, p75 = df_hist.quantile(0.25), df_hist.quantile(0.75)
    min_v, max_v = df_hist.min(), df_hist.max()
    fig_hist = go.Figure(go.Histogram(x=df_hist, nbinsx=50))
    for val, color, label, dash in [
        (mean_v, "black", "Mean", "dash"),
        (median_v, "red", "Median", "dash"),
        (p25, "blue", "P25", "dot"),
        (p75, "blue", "P75", "dot"),
        (min_v, "black", "Min", "solid"),
        (max_v, "black", "Max", "solid"),
    ]:
        fig_hist.add_vline(x=val, line_dash=dash, line_color=color, annotation_text=label)
    st.write(f'CAGR Histogram ({sel_year_hist}Y)')
    st.plotly_chart(fig_hist)

with tab_comp:
    # Comparisons with other mutual funds
    check_combo = st.checkbox("Compare against a combination of MF?", value=False, label_visibility="visible")
    names_comp = st.multiselect("Select Mutual Funds to Compare:", df_mfs.schemeName.unique(), max_selections=5)
    all_names = [sel_name] + names_comp
    codes_comp = [df_mfs[df_mfs['schemeName'] == x].schemeCode.to_list()[0] for x in all_names]

    list_navs = []
    list_cagrs = []
    list_date_markers = []
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

        # Drawdown recovery: find the earliest date when NAV was last at the current level
        df_date_marker = df_nav_comp[name].reset_index()
        df_date_marker['LatestDate'] = df_date_marker.date.max()
        df_date_marker['LatestNAV'] = df_date_marker.loc[
            df_date_marker['date'] == df_date_marker['LatestDate'], name]
        df_date_marker['LatestNAV'] = df_date_marker['LatestNAV'].bfill()
        df_date_marker['Cross'] = df_date_marker[name] > df_date_marker['LatestNAV']
        df_marked = df_date_marker[df_date_marker['Cross']].head(1)
        if not df_marked.empty:
            back_to_date = pd.to_datetime(df_marked.date.values[0])
            value_then = df_marked[name].values[0]
            df_date_marker['BackToDate'] = back_to_date
            df_date_marker['NAVThen'] = value_then
            df_mark = df_date_marker[['LatestDate', 'LatestNAV', 'BackToDate', 'NAVThen']].tail(1).transpose()
            df_mark.columns = [name]
            list_date_markers.append(df_mark.transpose())

        df_cagrs_comp = df_cagrs_comp.set_index(['date', 'years'])
        df_cagrs_comp = df_cagrs_comp.rename(columns={'cagr': name})
        list_cagrs.append(df_cagrs_comp)

    df_nav_all = pd.concat(list_navs, axis=1).dropna()

    if list_date_markers:
        df_marker = pd.concat(list_date_markers, axis=0)
        st.write('Drawdown Recovery — Current NAV Level Last Seen On')
        st.dataframe(df_marker, use_container_width=True)

    if check_combo:
        if len(names_comp) == 0:
            wt = "100.0"
        else:
            wt = ((str(round(100 / len(names_comp), 2)) + ", ") * len(names_comp)).rstrip(", ")
        wt_text = st.text_input("Weightage:", value=wt)
        wt_nums = [float(x.strip()) for x in wt_text.split(",")]

        if sum(wt_nums) != 100.0:
            st.error("Weights do not add up to 100.0. Please Check!")
        else:
            st.write("Weights add up to 100.0.  Okay!")

        ctr = 0
        for name in names_comp:
            df_nav_all[name + '_wt'] = df_nav_all[name] * wt_nums[ctr] / 100
            ctr += 1
        names_wt = [name + '_wt' for name in names_comp]
        df_nav_all['combo'] = df_nav_all[names_wt].sum(axis=1)

        df_nav = df_nav_all.reset_index()[['date', 'combo']]
        df_nav.columns = ['date', 'nav']
        list_cagr = []
        for y in years:
            df_cagr = get_cagr(df_nav, y)
            list_cagr.append(df_cagr)
        df_cagrs_comp = pd.concat(list_cagr)
        df_cagrs_comp = df_cagrs_comp.set_index(['date', 'years'])
        df_cagrs_comp = df_cagrs_comp.rename(columns={'cagr': 'combo'})
        list_cagrs.append(df_cagrs_comp)
        all_names = all_names + ['combo']

    df_cagr_all = pd.concat(list_cagrs, axis=1).dropna()

    df_navs_date = df_nav_all.reset_index()
    min_date = df_navs_date['date'].min()
    max_date = df_navs_date['date'].max()
    st.write('Cumulative Returns Comparisons')
    col1_cr, col2_cr = st.columns(2)
    with col1_cr:
        from_date = st.date_input('From Date:', value=min_date, min_value=min_date, max_value=max_date)
    with col2_cr:
        cumr_log_y = st.checkbox('Log Y-Axis', value=True, key='cumr_log_y')
    df_nav_all = df_navs_date[df_navs_date['date'] >= np.datetime64(from_date)].set_index('date')

    df_rebased = df_nav_all.div(df_nav_all.iloc[0]).reset_index()
    df_rebased_long = pd.melt(df_rebased, id_vars='date', value_vars=all_names, var_name='mf', value_name='nav')

    fig3 = px.line(df_rebased_long, x='date', y='nav', log_y=cumr_log_y, color='mf')
    fig3.update_layout(legend=dict(yanchor="bottom", y=-0.7, xanchor="left", x=0))
    st.plotly_chart(fig3)

    df_cagr_wide = df_cagr_all.reset_index()
    df_cagr_long = pd.melt(df_cagr_wide, id_vars=['date', 'years'], value_vars=all_names, var_name='mf', value_name='cagr')

    st.write("Rolling CAGR Comparison")
    sel_year = st.number_input('Investment Duration (Number of Years):', value=1, min_value=1, max_value=10, step=1)
    df_cagr_plot = df_cagr_long[df_cagr_long['years'] == sel_year]
    fig4 = px.line(df_cagr_plot, x='date', y='cagr', color='mf')
    fig4.update_layout(legend=dict(yanchor="bottom", y=-0.7, xanchor="left", x=0))
    st.plotly_chart(fig4)

    st.write('Draw Down Comparison')
    df_rebased_long['cum_max'] = df_rebased_long.groupby('mf').nav.cummax()
    df_rebased_long['draw_down'] = (df_rebased_long['nav'] - df_rebased_long['cum_max']) / df_rebased_long['cum_max']
    fig5 = px.line(df_rebased_long, x="date", y="draw_down", color="mf")
    fig5.update_layout(legend=dict(yanchor="bottom", y=-0.7, xanchor="left", x=0))
    st.plotly_chart(fig5)

    st.write('Comparative Growth — Value of Rs 1000 Invested')
    col1_g, col2_g = st.columns(2)
    with col1_g:
        sel_year_growth = st.number_input('Holding Period (Years):', value=5, min_value=1, max_value=10, step=1, key='growth_year')
    with col2_g:
        log_growth = st.checkbox("Log Y-axis", value=False, key='growth_log')
    list_growth = []
    for name in all_names:
        code = df_mfs[df_mfs['schemeName'] == name].schemeCode.to_list()[0]
        df_nav_g = get_nav(str(code))
        df_g = df_nav_g.copy()
        df_g['prev_nav'] = df_g['nav'].shift(365 * sel_year_growth)
        df_g = df_g.dropna()
        df_g['returns'] = df_g['nav'] / df_g['prev_nav'] - 1
        df_g['end_value'] = 1000 * (1 + df_g['returns'])
        df_g['fund'] = name
        list_growth.append(df_g[['date', 'fund', 'end_value']])
    df_growth_all = pd.concat(list_growth)
    fig_growth = px.line(df_growth_all, x='date', y='end_value', color='fund', log_y=log_growth)
    fig_growth.update_layout(legend=dict(yanchor="bottom", y=-0.7, xanchor="left", x=0))
    st.plotly_chart(fig_growth)

with tab_sip:
    #start_date = pd.to_datetime('2006-05-01')
    #end_date = pd.to_datetime('2020-04-01')
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input('Start Date:', datetime.date(2006, 5, 1))
    with col2:
        end_date = st.date_input('End Date:', datetime.date(2022, 4, 1))

    df_dates = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq='M'))
    df_dates.columns = ['date']

    df_cf = df_navs.merge(df_dates, on='date')
    df_cf['amount'] = 1000
    df_cf['units'] = df_cf['amount'] / df_cf['nav']
    df_cf['cum_units'] = df_cf['units'].cumsum()
    df_cf['cur_value'] = df_cf['cum_units'] * df_cf['nav']
    df_cf['inv_amount'] = df_cf['amount'].cumsum()
    df_cf = df_cf.reset_index()
    df_cf['amount'] = df_cf['amount'] * (1.05)**(df_cf['index'] // 12)

    df_investment = df_cf[['date', 'amount']]
    df_redemption = pd.DataFrame(
        [{'date': df_cf.iloc[-1:].date.values[0],
          'amount': -df_cf['units'].sum() * df_cf.iloc[-1:].nav.values[0]}])
    df_irr = pd.concat([df_investment, df_redemption]).reset_index(drop=True)

    xirr_value = xirr(df_irr[['date', 'amount']]) * 100
    st.write("XIRR: (%)")
    st.write(round(xirr_value,2))

    st.write('Invested Amount vs Current Value')
    df_daily_dates = pd.DataFrame(
        pd.date_range(start=df_cf['date'].min(), end=df_cf['date'].max(), freq='D'))
    df_daily_dates.columns = ['date']
    df_daily_navs = df_navs.merge(df_daily_dates, on='date')
    del df_cf['nav']
    df_cfs = df_cf.merge(df_daily_navs, on='date', how='right').sort_values(['date'])
    df_cfs = df_cfs.ffill()
    df_cfs['cur_value'] = df_cfs['cum_units'] * df_cfs['nav']
    df_cf_long = pd.melt(df_cfs[['date', 'inv_amount', 'cur_value']], id_vars=['date'],
                         value_vars=['inv_amount', 'cur_value'], var_name='component', value_name='amount')
    df_cf_long.loc[df_cf_long['component'] == 'inv_amount', 'component'] = 'Invested Amount'
    df_cf_long.loc[df_cf_long['component'] == 'cur_value', 'component'] = 'Current Value'
    fig6 = px.line(df_cf_long, x='date', y='amount', color='component')
    st.plotly_chart(fig6)

    st.write('Unit Accumulation - Normalized')
    df_cfs['cum_units'] = (df_cfs['cum_units'] / df_cfs.iloc[-1:].cum_units.values[0])
    df_cfs['inv_amount'] = (df_cfs['inv_amount'] / df_cfs.iloc[-1:].inv_amount.values[0])
    df_cf_long1 = pd.melt(df_cfs[['date', 'inv_amount', 'cum_units']], id_vars=['date'],
                         value_vars=['inv_amount', 'cum_units'], var_name='component', value_name='proportion')
    df_cf_long1.loc[df_cf_long1['component'] == 'inv_amount', 'component'] = 'Invested Amount'
    df_cf_long1.loc[df_cf_long1['component'] == 'cum_units', 'component'] = 'Accumulated Units'
    fig7 = px.line(df_cf_long1, x='date', y='proportion', color='component')
    # fig7 = px.line(df_cfs, x='date', y='cum_units')
    st.plotly_chart(fig7)

with tab_swp: # Still in Progress, need to refine this logic
    st.write('Systematic Withdrawal Plan - Analysis')
    col1, col2 = st.columns(2)
    with col1:
        inv_amount = st.number_input('Amount Invested:', value=100000, min_value=100000, step=10000)
        start_date = st.date_input('Start Date:', datetime.date(2005, 4, 1), key='st_date_swp')
    with col2:
        red_amount = st.number_input('Monthly Withdrawn:', value=1000, min_value=1000, step=100)
        end_date = st.date_input('End Date:', datetime.date(2022, 4, 1), key='end_date_swp')

    df_dates = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq='M'))
    df_dates.columns = ['date']

    df_cf = df_navs.merge(df_dates, on='date')
    df_cf['inv_value'] = inv_amount
    df_cf['init_units'] = df_cf['inv_value'] / df_cf['nav'][0]
    df_cf['amount'] = red_amount
    df_cf['units'] = df_cf['amount'] / df_cf['nav']
    df_cf['cum_units'] = df_cf['units'].cumsum()
    df_cf['cur_units'] = df_cf['init_units'] - df_cf['cum_units']
    df_cf['cur_value'] = df_cf['cur_units'] * df_cf['nav']

    df_investment = df_cf[['date', 'inv_value']].head(1)
    df_investment.columns = ['date', 'amount']
    df_redemption = df_cf[['date', 'amount']]
    df_remaining = df_cf.iloc[-1:][['date', 'cur_value']]
    df_remaining.columns = df_investment.columns
    df_redemption = pd.concat([df_redemption, df_remaining]).reset_index(drop=True)
    df_redemption['amount'] = -1 * df_redemption['amount']
    df_irr = pd.concat([df_investment, df_redemption]).reset_index(drop=True)

    xirr_value = xirr(df_irr[['date', 'amount']]) * 100
    st.write("XIRR: (%)")
    st.write(round(xirr_value,2))

    df_cf['cum_amount'] = df_cf['amount'].cumsum()
    df_cf['total'] = df_cf['cur_value'] + df_cf['cum_amount']
    df_cf_long = pd.melt(df_cf[['date', 'inv_value', 'cur_value', 'cum_amount', 'total']],
                         id_vars = ['date'],
                         value_vars = ['inv_value', 'cur_value', 'cum_amount', 'total'],
                         var_name = 'component',
                         value_name = 'amount')

    fig = px.line(df_cf_long, x='date', y='amount', color='component')
    st.plotly_chart(fig)

    # Similarly implement a step-up swp
with tab_stp:
    st.write('Systematic Transfer Plan - Analysis')
    st.write(f'Target Fund: **{sel_name}**')

    # --- Inputs ---
    stp_source_name = st.selectbox('Source Fund (transfer FROM):', df_mfs.schemeName.unique(), key='stp_source')

    col1, col2 = st.columns(2)
    with col1:
        stp_inv_amount = st.number_input('Amount Invested in Source (₹):', value=100000, min_value=1000, step=10000, key='stp_inv')
        stp_start = st.date_input('Start Date:', datetime.date(2010, 1, 1), key='stp_start')
    with col2:
        stp_transfer = st.number_input('Monthly Transfer Amount (₹):', value=5000, min_value=100, step=500, key='stp_transfer')
        stp_end = st.date_input('End Date:', datetime.date(2022, 1, 1), key='stp_end')

    # --- Validation ---
    if stp_source_name == sel_name:
        st.warning('Source and Target funds are the same. Please select a different source fund.')
        st.stop()

    # --- Data preparation ---
    stp_source_code = df_mfs[df_mfs['schemeName'] == stp_source_name].schemeCode.to_list()[0]
    df_src = get_nav(str(stp_source_code))

    df_stp_dates = pd.DataFrame(pd.date_range(start=stp_start, end=stp_end, freq='MS'), columns=['date'])

    df_src_m = df_src.merge(df_stp_dates, on='date').rename(columns={'nav': 'nav_src'})
    df_tgt_m = df_navs.merge(df_stp_dates, on='date').rename(columns={'nav': 'nav_tgt'})
    df_stp = df_src_m.merge(df_tgt_m, on='date')

    if df_stp.empty:
        st.error('No overlapping dates between source and target funds for the selected period. Try adjusting the dates.')
        st.stop()

    # --- Source fund (SWP side) ---
    init_units_src = stp_inv_amount / df_stp['nav_src'].iloc[0]
    df_stp['units_out'] = stp_transfer / df_stp['nav_src']
    df_stp['cum_units_out'] = df_stp['units_out'].cumsum().clip(upper=init_units_src)
    df_stp['remaining_units_src'] = (init_units_src - df_stp['cum_units_out']).clip(lower=0)
    df_stp['value_src'] = df_stp['remaining_units_src'] * df_stp['nav_src']

    # --- Target fund (SIP side) — only while source has units ---
    df_stp['active'] = df_stp['remaining_units_src'].shift(1, fill_value=init_units_src) > 0
    df_stp['units_in'] = (stp_transfer / df_stp['nav_tgt']).where(df_stp['active'], 0)
    df_stp['cum_units_tgt'] = df_stp['units_in'].cumsum()
    df_stp['value_tgt'] = df_stp['cum_units_tgt'] * df_stp['nav_tgt']

    # --- Combined ---
    df_stp['total_value'] = df_stp['value_src'] + df_stp['value_tgt']

    # --- XIRR ---
    df_xirr_stp = pd.DataFrame([
        {'date': df_stp['date'].iloc[0],  'amount':  stp_inv_amount},
        {'date': df_stp['date'].iloc[-1], 'amount': -df_stp['total_value'].iloc[-1]}
    ])
    xirr_stp = xirr(df_xirr_stp) * 100

    # --- Metrics row ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('XIRR (%)', f'{xirr_stp:.2f}%')
    m2.metric('Final Source Value (₹)', f'{df_stp["value_src"].iloc[-1]:,.0f}')
    m3.metric('Final Target Value (₹)', f'{df_stp["value_tgt"].iloc[-1]:,.0f}')
    m4.metric('Total Portfolio Value (₹)', f'{df_stp["total_value"].iloc[-1]:,.0f}')

    # --- Chart 1: Portfolio value over time ---
    df_val_long = pd.melt(
        df_stp[['date', 'value_src', 'value_tgt', 'total_value']],
        id_vars='date',
        value_vars=['value_src', 'value_tgt', 'total_value'],
        var_name='component', value_name='value'
    )
    df_val_long['component'] = df_val_long['component'].map({
        'value_src': f'Source ({stp_source_name[:30]})',
        'value_tgt': f'Target ({sel_name[:30]})',
        'total_value': 'Total Portfolio'
    })
    fig_stp1 = px.line(df_val_long, x='date', y='value', color='component')
    fig_stp1.update_layout(legend=dict(yanchor="bottom", y=-0.5, xanchor="left", x=0))
    st.write('Portfolio Value Over Time')
    st.plotly_chart(fig_stp1)

    # --- Chart 2: Units tracker (normalised) ---
    df_stp['src_units_norm'] = df_stp['remaining_units_src'] / df_stp['remaining_units_src'].iloc[0]
    max_tgt = df_stp['cum_units_tgt'].max()
    df_stp['tgt_units_norm'] = df_stp['cum_units_tgt'] / max_tgt if max_tgt > 0 else 0
    df_units_long = pd.melt(
        df_stp[['date', 'src_units_norm', 'tgt_units_norm']],
        id_vars='date',
        value_vars=['src_units_norm', 'tgt_units_norm'],
        var_name='component', value_name='proportion'
    )
    df_units_long['component'] = df_units_long['component'].map({
        'src_units_norm': 'Source Units (depleting)',
        'tgt_units_norm': 'Target Units (accumulating)'
    })
    fig_stp2 = px.line(df_units_long, x='date', y='proportion', color='component')
    fig_stp2.update_layout(legend=dict(yanchor="bottom", y=-0.4, xanchor="left", x=0))
    st.write('Units Tracker (Normalised)')
    st.plotly_chart(fig_stp2)
