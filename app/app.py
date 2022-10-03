# Base file for the streamlit application
# The idea is to use the R functions directly from this Python file

import pandas as pd
import streamlit as st
import numpy as np
import plotly_express as px

# Here is the top level outline
# Multi page
# 1. Nav Charting
# 2. CAGR Analysis
# 3. Rolling Return Analysis
# 4. SIP Analysis
# 5. STP Analysis
# 6. SWP Analysis

st.plotly_chart(fig_1)