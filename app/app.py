# Base file for the streamlit application
# The idea is to use the R functions directly from this Python file

import pandas as pd
import urllib.request, json
import plotly_express as px
import plotly.figure_factory as ff
import streamlit as st


@st.cache
def get_scheme_codes():
    with urllib.request.urlopen('https://api.mfapi.in/mf') as url:
        data = json.load(url)
    df_mfs = pd.DataFrame(data)
    return df_mfs

@st.cache
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
st.write(df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0])
sel_code = df_mfs[df_mfs['schemeName'] == sel_name].schemeCode.to_list()[0]

df_navs = get_nav(str(sel_code))
fig1 = px.line(df_navs, x = 'date', y='nav', log_y=True)
st.write('NAV Chart - ' + sel_name)
st.plotly_chart(fig1)

years = [x + 1 for x in range(9)]
list_cagr = []
for y in years:
    df_cagr = get_cagr(df_navs, y)
    list_cagr.append(df_cagr)
df_cagrs = pd.concat(list_cagr)

fig2 = px.line(df_cagrs, x='date', y='cagr', color='years')
st.write('CAGR Chart - ' + sel_name)
st.plotly_chart(fig2)

# Next to do: Comparisons with other mutual funds