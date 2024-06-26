# Base file for the streamlit application
# The idea is to use the R functions directly from this Python file
# Need a complete listing of to-do and pending activities

# NAV History from AMFI can be downloaded from
# https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?mf=64&frmdt=01-Feb-2023&todt=21-Feb-2023

import pandas as pd
import urllib.request, json
import plotly_express as px
import plotly.figure_factory as ff
import streamlit as st
import numpy as np
from pyxirr import xirr
import datetime

@st.cache_data
def get_scheme_codes_old():
    with urllib.request.urlopen('https://api.mfapi.in/mf') as url:
        data = json.load(url)
    df_mfs = pd.DataFrame(data)
    return df_mfs

@st.cache_data
def get_scheme_codes():
    with open('./data/mf_codes.txt', 'r') as fp:
        list_code = []
        line = fp.readline()
        while line:
            words = line.strip().split(';')
            if len(words) > 5:
                list_code.append([words[i] for i in [0, 1, 3]])
            line = fp.readline()

    df_codes = pd.DataFrame(list_code)
    df_codes.columns = ['schemeCode', 'schemeISIN', 'schemeName']
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
    dfx = df_cagrs[['years', 'cagr']].groupby('years').describe().reset_index()
    # st.write(df_cagrs)
    # st.write([[a for (a, b) in dfx.columns][0]] + [a for a in dfx.columns.droplevel()][1:])
    dfx.columns = [[a for (a, b) in dfx.columns][0]] + [a for a in dfx.columns.droplevel()][1:]
    st.write('CAGR - Min, Median and Max')
    st.write(dfx)

with tab_comp:
    # Comparisons with other mutual funds
    check_combo = st.checkbox("Compare against a combination of MF?", value=False, label_visibility="visible")
    names_comp = st.multiselect("Select Mutual Funds to Compare:", df_mfs.schemeName.unique(), max_selections=5)
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
    from_date = st.date_input('From Date:', value=min_date, min_value=min_date, max_value=max_date)
    df_nav_all = df_navs_date[df_navs_date['date'] >= np.datetime64(from_date)].set_index('date')

    df_rebased = df_nav_all.div(df_nav_all.iloc[0]).reset_index()
    df_rebased_long = pd.melt(df_rebased, id_vars='date', value_vars=all_names, var_name='mf', value_name='nav')

    fig3 = px.line(df_rebased_long, x='date', y='nav', log_y=True, color='mf')
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
    # To do: Implementation of STP systematic transfer plan
    st.write('STP - In Progress')
    # A combination of SWP from one scheme and SIP into another scheme
