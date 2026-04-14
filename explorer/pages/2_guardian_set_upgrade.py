"""Guardian set upgrade status page."""

import streamlit as st

st.title("Guardian set upgrade")

client = st.session_state.get("client")
if client is None:
    st.warning("Configure the client on the home page first.")
    st.stop()

if st.button("Check"):
    with st.spinner("Fetching..."):
        result = client.get_guardian_set_upgrade()
    if result is None:
        st.success("No guardian set upgrade is currently in progress.")
    else:
        st.json(result)
