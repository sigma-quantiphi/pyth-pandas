"""Latest prices explorer page."""

import streamlit as st

st.title("Latest prices")

client = st.session_state.get("client")
if client is None:
    st.warning("Configure the client on the home page first.")
    st.stop()

symbols_text = st.text_input(
    "Symbols (comma-separated)", value="Crypto.BTC/USD, Crypto.ETH/USD"
)
symbols = [s.strip() for s in symbols_text.split(",") if s.strip()] or None

properties = st.multiselect(
    "Properties",
    [
        "price",
        "confidence",
        "exponent",
        "publisherCount",
        "bestBidPrice",
        "bestAskPrice",
        "emaPrice",
        "emaConfidence",
        "fundingRate",
        "feedUpdateTimestamp",
    ],
    default=["price", "confidence", "exponent", "publisherCount"],
)
channel = st.selectbox(
    "Channel",
    ["real_time", "fixed_rate@50ms", "fixed_rate@200ms", "fixed_rate@1000ms"],
)

if st.button("Fetch"):
    with st.spinner("Fetching..."):
        df = client.fetch_latest_prices(
            symbols=symbols,
            properties=properties,
            channel=channel,
        )
    st.dataframe(df, use_container_width=True)
    st.write("attrs:", df.attrs)
