import streamlit as st
from Valuation_model import market_snapshot, long_term_model, company_dcf

st.title("📊 Market Valuation Engine")

option = st.selectbox("Choose Mode", ["Market", "DCF"])

if option == "Market":
    st.text("Running market model...")
    fpe = market_snapshot()
    long_term_model(fpe)

elif option == "DCF":
    ticker = st.text_input("Enter Ticker (e.g. AAPL)")
    if ticker:
        company_dcf(ticker)
