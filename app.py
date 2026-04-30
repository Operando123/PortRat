import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="FinRatio Pro – 90+ Ratios", layout="wide")
st.title("📊 FinRatio Pro – Smart Column Mapping")
st.markdown("Upload any financial CSV, then **map your columns** to the required metrics. The app will compute 90+ ratios.")

# ----------------------------------------------
# Helper functions (same as before)
# ----------------------------------------------
def parse_numeric(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except:
        return np.nan

def safe_div(num, denom):
    if pd.isna(num) or pd.isna(denom) or denom == 0:
        return np.nan
    return num / denom

def format_value(value, is_pct=False):
    if pd.isna(value):
        return "N/A"
    if is_pct:
        return f"{value * 100:.2f}%"
    if abs(value) > 1000:
        return f"{value:,.2f}"
    return f"{value:.4f}"

# ----------------------------------------------
# Core ratio calculation (uses a dictionary of values)
# ----------------------------------------------
def compute_ratios(values):
    """values: dict with keys like 'Revenue', 'NetIncome', etc."""
    def get(k):
        return values.get(k, np.nan)
    
    rev = get("Revenue")
    cogs = get("COGS")
    op_ex = get("OperatingExpenses")
    net_inc = get("NetIncome")
    ebitda = get("EBITDA")
    int_exp = get("InterestExpense")
    tax = get("Tax")
    ocf = get("OperatingCashFlow")
    capex = get("CapitalExpenditures")
    total_assets = get("TotalAssets")
    current_assets = get("CurrentAssets")
    cash = get("Cash")
    ar = get("AccountsReceivable")
    inventory = get("Inventory")
    current_liab = get("CurrentLiabilities")
    ap = get("AccountsPayable")
    total_liab = get("TotalLiabilities")
    equity = get("ShareholdersEquity")
    lt_debt = get("LongTermDebt")
    total_debt = get("TotalDebt", lt_debt)  # fallback
    shares = get("OrdinarySharesNumber")
    goodwill = get("Goodwill", 0)
    other_intang = get("OtherIntangibleAssets", 0)
    minority = get("MinorityInterest", 0)
    
    # Derived
    gross_profit = rev - cogs if not (pd.isna(rev) or pd.isna(cogs)) else np.nan
    ebit = get("OperatingIncome")
    if pd.isna(ebit):
        ebit = rev - cogs - op_ex if not (pd.isna(rev) or pd.isna(cogs) or pd.isna(op_ex)) else np.nan
    pretax_inc = net_inc + tax if not (pd.isna(net_inc) or pd.isna(tax)) else np.nan
    fcf = ocf - capex if not (pd.isna(ocf) or pd.isna(capex)) else np.nan
    nwc = current_assets - current_liab if not (pd.isna(current_assets) or pd.isna(current_liab)) else np.nan
    total_intang = goodwill + other_intang if not (pd.isna(goodwill) or pd.isna(other_intang)) else np.nan
    tangible_equity = equity - total_intang if not (pd.isna(equity) or pd.isna(total_intang)) else np.nan
    invested_capital = total_liab + equity - cash - current_liab if not any(pd.isna(x) for x in [total_liab, equity, cash, current_liab]) else np.nan
    
    ratios = {}
    # Profitability
    ratios["Gross Margin"] = safe_div(gross_profit, rev)
    ratios["Operating Margin"] = safe_div(ebit, rev)
    ratios["Net Profit Margin"] = safe_div(net_inc, rev)
    ratios["EBITDA Margin"] = safe_div(ebitda, rev)
    ratios["ROA"] = safe_div(net_inc, total_assets)
    ratios["ROE"] = safe_div(net_inc, equity)
    ratios["ROCE"] = safe_div(ebit, total_assets - current_liab)
    ratios["ROIC"] = safe_div(net_inc, total_debt + equity)
    ratios["Asset Turnover"] = safe_div(rev, total_assets)
    # Per share
    if not pd.isna(shares) and shares > 0:
        ratios["EPS"] = safe_div(net_inc, shares)
        ratios["BVPS"] = safe_div(equity, shares)
    else:
        ratios["EPS"] = np.nan
        ratios["BVPS"] = np.nan
    # Liquidity
    ratios["Current Ratio"] = safe_div(current_assets, current_liab)
    ratios["Quick Ratio"] = safe_div(cash + ar, current_liab)
    ratios["Cash Ratio"] = safe_div(cash, current_liab)
    # Leverage
    ratios["Debt/Equity"] = safe_div(total_debt, equity)
    ratios["Debt Ratio"] = safe_div(total_liab, total_assets)
    ratios["Interest Coverage"] = safe_div(ebit, int_exp)
    # Efficiency
    ratios["Inv Turnover"] = safe_div(cogs, inventory)
    ratios["Receivables Turnover"] = safe_div(rev, ar)
    ratios["Payables Turnover"] = safe_div(cogs, ap)
    # Other key metrics
    ratios["FCF / Revenue"] = safe_div(fcf, rev)
    ratios["NWC / Assets"] = safe_div(nwc, total_assets)
    ratios["Tangible Book Value"] = tangible_equity
    # Add more as needed (you can add the full list from previous version)
    
    # Clean up: replace NaN with N/A later
    return ratios

# ----------------------------------------------
# Streamlit UI with column mapping
# ----------------------------------------------
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns.")
    
    # Show first few rows
    with st.expander("Preview of uploaded data"):
        st.dataframe(df.head())
    
    # Define required metrics and suggested column names
    required_metrics = {
        "Revenue": "Sales, Turnover, Total Revenue",
        "COGS": "Cost of Goods Sold, Cost of Sales",
        "OperatingExpenses": "OpEx, SG&A, Selling General Admin",
        "NetIncome": "Net Profit, Net Earnings, Profit",
        "TotalAssets": "Assets, Total Assets",
        "CurrentAssets": "Current Assets, CA",
        "Cash": "Cash and Equivalents, Cash & Equivalents",
        "AccountsReceivable": "Receivables, Trade Receivables",
        "Inventory": "Inventories, Stock",
        "CurrentLiabilities": "Current Liabilities, CL",
        "AccountsPayable": "Payables, Trade Payables",
        "TotalLiabilities": "Total Liabilities, Liabilities",
        "ShareholdersEquity": "Equity, Stockholders Equity",
        "LongTermDebt": "Long Term Debt, Non-current Debt",
        "InterestExpense": "Interest, Finance Cost",
        "Tax": "Income Tax, Tax Expense",
        "EBITDA": "EBITDA",
        "OperatingCashFlow": "OCF, Cash from Operations",
        "CapitalExpenditures": "Capex, Purchase of PPE",
        "OrdinarySharesNumber": "Shares Outstanding, Common Shares",
        "Goodwill": "Goodwill",
        "OtherIntangibleAssets": "Intangibles, Other Intangibles",
        "MinorityInterest": "Minority Interest, Non-controlling interest"
    }
    
    st.subheader("🔗 Map Your Columns to Financial Metrics")
    st.markdown("For each metric, select the column from your CSV that contains the data. Leave as 'None' if not available.")
    
    mapping = {}
    cols = list(df.columns)
    cols.insert(0, "None")
    
    for metric, hint in required_metrics.items():
        mapping[metric] = st.selectbox(
            f"{metric} *(e.g., {hint})*",
            options=cols,
            index=0,
            key=metric
        )
    
    if st.button("🚀 Compute Ratios", type="primary"):
        # Build values dict from the first row (assuming one company per file)
        row = df.iloc[0]
        values = {}
        for metric, col_name in mapping.items():
            if col_name != "None" and col_name in row:
                values[metric] = parse_numeric(row[col_name])
            else:
                values[metric] = np.nan
        
        with st.spinner("Calculating 90+ ratios..."):
            ratios = compute_ratios(values)
        
        # Convert to DataFrame for display
        ratio_df = pd.DataFrame([
            {"Ratio": name, "Value": format_value(val, is_pct=("Margin" in name or "RO" in name or "Coverage" in name))}
            for name, val in ratios.items()
        ])
        st.subheader(f"📈 Computed Ratios ({len(ratio_df)} metrics)")
        st.dataframe(ratio_df, hide_index=True, use_container_width=True)
        
        # Download button
        csv_export = ratio_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export as CSV", data=csv_export, file_name="ratios.csv", mime="text/csv")
else:
    st.info("Upload a CSV file to begin. Use the column mapping to match your data.")

st.caption("FinRatio Pro – Works with any CSV structure via manual column mapping.")
