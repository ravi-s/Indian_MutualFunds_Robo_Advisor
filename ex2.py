import streamlit as st
import numpy as np
import pandas as pd

data = np.random.randn(1000, 2) / 50 + [37.76, -122.4]
print(data[0:10])
map_data = pd.DataFrame(
    data ,
    columns=['lat', 'lon'])

st.map(map_data)