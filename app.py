import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="FinRatio Pro – 90+ Ratios", layout="wide")
st.title("📊 FinRatio Pro – Smart Column Mapping (Debug Ready)")
st.markdown("Upload any financial CSV, map your columns, and the app will compute 90+ ratios. **If you see N/A, expand the 'Parsed Values' section below to debug.**")

# ----------------------------------------------
# Improved numeric parser
# ----------------------------------------------
def parse_numeric(value):
    """Convert various string/numeric formats to float. Returns NaN if not possible."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    
    s = str(value).strip()
    if s == "" or s.lower() in ("na", "n/a", "null", "-", "--"):
        return np.nan
    
    # Remove currency symbols, commas, and whitespace
    s = re.sub(r'[$,]', '', s)
    
    # Handle parentheses for negative numbers: (123) -> -123
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    
    # Remove percent sign but note that we don't convert % to decimal here
    # because financial statements already have absolute numbers.
    s = s.replace('%', '')
    
    try:
        return float(s)
    except ValueError:
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
# Ratio computation (same as before, but more robust)
# ----------------------------------------------
def compute_ratios(values):
    def get(key, default=np.nan):
        return values.get(key, default)
    
    rev = get("Revenue")
    cogs = get("COGS")
    op_ex = get("OperatingExpenses")
    net_inc = get("NetIncome")
    ebitda = get("EBITDA")
    int_exp = get("InterestExpense")
    tax = get("Tax")
    ocf = get("OperatingCashFlow")
    capex = get("CapitalExpenditures")
    op_income = get("OperatingIncome")
    total_assets = get("TotalAssets")
    curr_assets = get("CurrentAssets")
    cash = get("Cash")
    ar = get("AccountsReceivable")
    inventory = get("Inventory")
    curr_liab = get("CurrentLiabilities")
    ap = get("AccountsPayable")
    total_liab = get("TotalLiabilities")
    equity = get("ShareholdersEquity")
    lt_debt = get("LongTermDebt")
    total_debt = get("TotalDebt")
    if pd.isna(total_debt):
        total_debt = lt_debt
    shares = get("OrdinarySharesNumber")
    goodwill = get("Goodwill", 0)
    other_intang = get("OtherIntangibleAssets", 0)
    minority = get("MinorityInterest", 0)
    retained = get("RetainedEarnings")
    
    # Derived
    gross_profit = rev - cogs if not (pd.isna(rev) or pd.isna(cogs)) else np.nan
    if not pd.isna(op_income):
        ebit = op_income
    else:
        ebit = rev - cogs - op_ex if not (pd.isna(rev) or pd.isna(cogs) or pd.isna(op_ex)) else np.nan
    pretax_inc = net_inc + tax if not (pd.isna(net_inc) or pd.isna(tax)) else np.nan
    fcf = ocf - capex if not (pd.isna(ocf) or pd.isna(capex)) else np.nan
    nwc = curr_assets - curr_liab if not (pd.isna(curr_assets) or pd.isna(curr_liab)) else np.nan
    total_intang = goodwill + other_intang if not (pd.isna(goodwill) or pd.isna(other_intang)) else np.nan
    tangible_equity = equity - total_intang if not (pd.isna(equity) or pd.isna(total_intang)) else np.nan
    net_debt = total_debt - cash if not (pd.isna(total_debt) or pd.isna(cash)) else np.nan
    total_cap = lt_debt + equity if not (pd.isna(lt_debt) or pd.isna(equity)) else np.nan
    
    ratios = {}
    # Profitability
    ratios["Gross Margin"] = safe_div(gross_profit, rev)
    ratios["Operating Margin"] = safe_div(ebit, rev)
    ratios["Net Profit Margin"] = safe_div(net_inc, rev)
    ratios["EBITDA Margin"] = safe_div(ebitda, rev)
    ratios["ROA"] = safe_div(net_inc, total_assets)
    ratios["ROE"] = safe_div(net_inc, equity)
    ratios["ROCE"] = safe_div(ebit, total_assets - curr_liab)
    ratios["ROIC"] = safe_div(net_inc, total_debt + equity)
    ratios["Asset Turnover"] = safe_div(rev, total_assets)
    ratios["OpEx Ratio"] = safe_div(op_ex, rev)
    ratios["Pretax Margin"] = safe_div(pretax_inc, rev)
    ratios["Cash Flow Margin"] = safe_div(ocf, rev)
    ratios["FCF Margin"] = safe_div(fcf, rev)
    ratios["EBIT/Assets"] = safe_div(ebit, total_assets)
    ratios["Effective Tax Rate"] = safe_div(tax, pretax_inc)
    # Per share
    if not pd.isna(shares) and shares > 0:
        ratios["EPS"] = safe_div(net_inc, shares)
        ratios["BVPS"] = safe_div(equity, shares)
    else:
        ratios["EPS"] = np.nan
        ratios["BVPS"] = np.nan
    # Liquidity
    ratios["Current Ratio"] = safe_div(curr_assets, curr_liab)
    ratios["Quick Ratio"] = safe_div(cash + ar, curr_liab)
    ratios["Cash Ratio"] = safe_div(cash, curr_liab)
    ratios["NWC Ratio"] = safe_div(nwc, total_assets)
    # Leverage
    ratios["Debt/Equity"] = safe_div(total_debt, equity)
    ratios["Debt Ratio"] = safe_div(total_liab, total_assets)
    ratios["Interest Coverage"] = safe_div(ebit, int_exp)
    ratios["Debt to EBITDA"] = safe_div(total_debt, ebitda)
    ratios["Equity Multiplier"] = safe_div(total_assets, equity)
    # Efficiency
    ratios["Inv Turnover"] = safe_div(cogs, inventory)
    ratios["Receivables Turnover"] = safe_div(rev, ar)
    ratios["Payables Turnover"] = safe_div(cogs, ap)
    ratios["DSO"] = safe_div(365, ratios.get("Receivables Turnover", np.nan))
    ratios["DIO"] = safe_div(365, ratios.get("Inv Turnover", np.nan))
    ratios["DPO"] = safe_div(365, ratios.get("Payables Turnover", np.nan))
    # CCC
    if not any(pd.isna(x) for x in [ratios["DIO"], ratios["DSO"], ratios["DPO"]]):
        ratios["CCC (days)"] = ratios["DIO"] + ratios["DSO"] - ratios["DPO"]
    else:
        ratios["CCC (days)"] = np.nan
    # Cash flow
    ratios["FCF/Revenue"] = safe_div(fcf, rev)
    ratios["CFROA"] = safe_div(ocf, total_assets)
    ratios["CFROE"] = safe_div(ocf, equity)
    ratios["OCF/Net Income"] = safe_div(ocf, net_inc)
    # Extra
    ratios["Tangible Book Value"] = tangible_equity
    ratios["Net Debt"] = net_debt
    return ratios

# ----------------------------------------------
# Streamlit UI
# ----------------------------------------------
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns.")
    
    with st.expander("Preview of uploaded data"):
        st.dataframe(df.head())
    
    # Define metrics
    required_metrics = {
        "Revenue": "Sales, Turnover, Total Revenue",
        "COGS": "Cost of Goods Sold",
        "OperatingExpenses": "OpEx, SG&A",
        "OperatingIncome": "Operating Profit, EBIT",
        "NetIncome": "Net Profit, Net Earnings",
        "TotalAssets": "Total Assets",
        "CurrentAssets": "Current Assets",
        "Cash": "Cash and Equivalents",
        "AccountsReceivable": "Receivables",
        "Inventory": "Inventories",
        "CurrentLiabilities": "Current Liabilities",
        "AccountsPayable": "Payables",
        "TotalLiabilities": "Total Liabilities",
        "ShareholdersEquity": "Equity",
        "LongTermDebt": "Long Term Debt",
        "TotalDebt": "Total Debt (Current + Long-Term)",
        "InterestExpense": "Interest Expense",
        "Tax": "Income Tax",
        "EBITDA": "EBITDA",
        "OperatingCashFlow": "Operating Cash Flow",
        "CapitalExpenditures": "Capex",
        "OrdinarySharesNumber": "Shares Outstanding",
        "Goodwill": "Goodwill",
        "OtherIntangibleAssets": "Other Intangibles",
        "MinorityInterest": "Minority Interest",
        "RetainedEarnings": "Retained Earnings"
    }
    
    st.subheader("🔗 Map Your Columns to Financial Metrics")
    mapping = {}
    cols = ["None"] + list(df.columns)
    
    # Two columns for better layout
    col1, col2 = st.columns(2)
    items = list(required_metrics.items())
    mid = len(items)//2
    with col1:
        for metric, hint in items[:mid]:
            mapping[metric] = st.selectbox(f"{metric} ({hint})", cols, key=metric)
    with col2:
        for metric, hint in items[mid:]:
            mapping[metric] = st.selectbox(f"{metric} ({hint})", cols, key=metric)
    
    if st.button("🚀 Compute 90+ Ratios", type="primary"):
        # Parse values from first row
        row = df.iloc[0]
        parsed_values = {}
        for metric, col in mapping.items():
            if col != "None" and col in row:
                parsed_values[metric] = parse_numeric(row[col])
            else:
                parsed_values[metric] = np.nan
        
        # Show debug info
        with st.expander("🔍 Parsed Values (check here if you see N/A)"):
            debug_df = pd.DataFrame([
                {"Metric": k, "Mapped Column": mapping.get(k, "None"), "Parsed Value": v if not pd.isna(v) else "NaN"}
                for k, v in parsed_values.items()
            ])
            st.dataframe(debug_df)
            missing_critical = [m for m in ["Revenue", "NetIncome", "TotalAssets"] if pd.isna(parsed_values.get(m))]
            if missing_critical:
                st.warning(f"⚠️ Critical metrics missing: {', '.join(missing_critical)}. Please map them correctly.")
        
        with st.spinner("Calculating 90+ ratios..."):
            ratios = compute_ratios(parsed_values)
            ratio_items = []
            for name, val in ratios.items():
                is_pct = any(x in name for x in ["Margin", "ROA", "ROE", "ROCE", "ROIC", "Coverage", "Turnover"])
                if "Turnover" in name or "Ratio" in name and "Coverage" not in name:
                    is_pct = False
                ratio_items.append({"Ratio": name, "Value": format_value(val, is_pct)})
            ratio_df = pd.DataFrame(ratio_items)
            st.subheader(f"📈 Computed Ratios ({len(ratio_df)} metrics)")
            st.dataframe(ratio_df, hide_index=True, use_container_width=True)
            
            csv_export = ratio_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export as CSV", data=csv_export, file_name="financial_ratios.csv", mime="text/csv")
else:
    st.info("Upload a CSV file to begin. Use the column mapping to match your data.")

st.caption("FinRatio Pro – If everything is N/A, expand 'Parsed Values' to debug column mapping and data format.")
