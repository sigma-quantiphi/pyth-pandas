"""pyth-pandas explorer — home page."""

import streamlit as st

from pyth_pandas import PythPandas

st.set_page_config(page_title="pyth-pandas explorer", layout="wide")

st.title("pyth-pandas explorer")
st.caption("Interactive playground for the Pyth Pro Router (Pyth Lazer) API")

with st.sidebar:
    st.header("Client config")
    base_url = st.text_input("Base URL", value="https://pyth-lazer.dourolabs.app/v1/")
    api_key = st.text_input("PYTH_API_KEY", value="", type="password")

if "client" not in st.session_state or st.sidebar.button("Reload client"):
    st.session_state.client = PythPandas(
        base_url=base_url, api_key=api_key or None, use_tqdm=False
    )

st.markdown(
    """
    Pick an endpoint from the sidebar pages on the left.

    - **Latest prices** — point-in-time snapshot per feed
    - **Historical price** — feed values at a specific timestamp
    - **Guardian set upgrade** — Wormhole governance status
    """
)
