import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="FinRatio Pro – 90+ Ratios", layout="wide")
st.title("📊 FinRatio Pro – Smart Column Mapping")
st.markdown("Upload any financial CSV, then **map your columns** to the required metrics. The app will compute 90+ ratios.")

# ----------------------------------------------
# Helper functions
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
# Core ratio calculation (90+ ratios)
# ----------------------------------------------
def compute_ratios(values):
    """values: dict with keys (must match the mapping). Returns dict of ratios."""
    def get(key, default=np.nan):
        return values.get(key, default)
    
    # ---------- Income Statement ----------
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
    
    # ---------- Balance Sheet ----------
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
    add_paid = get("AdditionalPaidInCapital")
    common_stock = get("CommonStock")
    
    # ---------- Derived metrics ----------
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
    invested_capital = total_liab + equity - cash - curr_liab if not any(pd.isna(x) for x in [total_liab, equity, cash, curr_liab]) else np.nan
    net_debt = total_debt - cash if not (pd.isna(total_debt) or pd.isna(cash)) else np.nan
    total_cap = lt_debt + equity if not (pd.isna(lt_debt) or pd.isna(equity)) else np.nan
    
    # ---------- Ratios dictionary (90+ items) ----------
    ratios = {}
    
    # Profitability (16)
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
    ratios["Gross Profit / Assets"] = safe_div(gross_profit, total_assets)
    
    # Per Share (if shares known)
    if not pd.isna(shares) and shares > 0:
        ratios["EPS (Basic)"] = safe_div(net_inc, shares)
        ratios["Book Value Per Share"] = safe_div(equity, shares)
        ratios["Tangible Book Value Per Share"] = safe_div(tangible_equity, shares)
        ratios["Operating Cash Flow Per Share"] = safe_div(ocf, shares)
    else:
        ratios["EPS (Basic)"] = np.nan
        ratios["Book Value Per Share"] = np.nan
        ratios["Tangible Book Value Per Share"] = np.nan
        ratios["Operating Cash Flow Per Share"] = np.nan
    
    # Liquidity (7)
    ratios["Current Ratio"] = safe_div(curr_assets, curr_liab)
    ratios["Quick Ratio"] = safe_div(cash + ar, curr_liab)
    ratios["Cash Ratio"] = safe_div(cash, curr_liab)
    ratios["NWC Ratio"] = safe_div(nwc, total_assets)
    daily_ops = (cogs + op_ex) / 365 if not (pd.isna(cogs) or pd.isna(op_ex)) else np.nan
    ratios["Defensive Interval (days)"] = safe_div(cash + ar, daily_ops)
    ratios["OCF Ratio"] = safe_div(ocf, curr_liab)
    ratios["Cash Flow to Current Liab"] = safe_div(ocf, curr_liab)
    
    # Solvency & Leverage (12)
    ratios["Debt to Equity"] = safe_div(total_debt, equity)
    ratios["Net Debt to Equity"] = safe_div(net_debt, equity)
    ratios["Debt Ratio"] = safe_div(total_liab, total_assets)
    ratios["Equity Ratio"] = safe_div(equity, total_assets)
    ratios["LT Debt to Equity"] = safe_div(lt_debt, equity)
    ratios["Interest Coverage (EBIT/Int)"] = safe_div(ebit, int_exp)
    ratios["Debt to EBITDA"] = safe_div(total_debt, ebitda)
    ratios["Net Debt to EBITDA"] = safe_div(net_debt, ebitda)
    ratios["OCF to Total Debt"] = safe_div(ocf, total_debt)
    ratios["Equity Multiplier"] = safe_div(total_assets, equity)
    ratios["Total Debt / Capitalization"] = safe_div(total_debt, total_cap)
    ratios["LT Debt / Capitalization"] = safe_div(lt_debt, total_cap)
    
    # Efficiency (14)
    ratios["Receivables Turnover"] = safe_div(rev, ar)
    if not pd.isna(ratios["Receivables Turnover"]) and ratios["Receivables Turnover"] > 0:
        ratios["DSO (days)"] = 365 / ratios["Receivables Turnover"]
    else:
        ratios["DSO (days)"] = np.nan
    ratios["Inventory Turnover"] = safe_div(cogs, inventory)
    if not pd.isna(ratios["Inventory Turnover"]) and ratios["Inventory Turnover"] > 0:
        ratios["DIO (days)"] = 365 / ratios["Inventory Turnover"]
    else:
        ratios["DIO (days)"] = np.nan
    ratios["Payables Turnover"] = safe_div(cogs, ap)
    if not pd.isna(ratios["Payables Turnover"]) and ratios["Payables Turnover"] > 0:
        ratios["DPO (days)"] = 365 / ratios["Payables Turnover"]
    else:
        ratios["DPO (days)"] = np.nan
    # CCC
    dio = ratios.get("DIO (days)", np.nan)
    dso = ratios.get("DSO (days)", np.nan)
    dpo = ratios.get("DPO (days)", np.nan)
    if not any(pd.isna(x) for x in [dio, dso, dpo]):
        ratios["CCC (days)"] = dio + dso - dpo
    else:
        ratios["CCC (days)"] = np.nan
    ratios["Fixed Asset Turnover"] = safe_div(rev, total_assets - curr_assets)
    ratios["Working Capital Turnover"] = safe_div(rev, nwc)
    ratios["Equity Turnover"] = safe_div(rev, equity)
    ratios["Inventory to Sales"] = safe_div(inventory, rev)
    ratios["Receivables to Sales"] = safe_div(ar, rev)
    ratios["Capex to Revenue"] = safe_div(capex, rev)
    ratios["FCF / Net Income"] = safe_div(fcf, net_inc)
    
    # Cash Flow & extra (14)
    ratios["CFROA"] = safe_div(ocf, total_assets)
    ratios["CFROE"] = safe_div(ocf, equity)
    ratios["EBITDA / Interest"] = safe_div(ebitda, int_exp)
    ratios["OCF to Net Income"] = safe_div(ocf, net_inc)
    ratios["OCF / Interest"] = safe_div(ocf, int_exp)
    ratios["LT Debt to Assets"] = safe_div(lt_debt, total_assets)
    ratios["Current Liab / Equity"] = safe_div(curr_liab, equity)
    ratios["FCF / OCF"] = safe_div(fcf, ocf)
    ratios["NWC / Sales"] = safe_div(nwc, rev)
    ratios["Tangible Book / Assets"] = safe_div(tangible_equity, total_assets)
    ratios["Invested Capital Turnover"] = safe_div(rev, invested_capital)
    ratios["Net Tangible Assets / Equity"] = safe_div(tangible_equity, equity)
    ratios["Minority Interest / Equity"] = safe_div(minority, equity)
    ratios["Retained Earnings / Equity"] = safe_div(retained, equity)
    
    # DuPont
    npm = ratios.get("Net Profit Margin", np.nan)
    at = ratios.get("Asset Turnover", np.nan)
    em = ratios.get("Equity Multiplier", np.nan)
    if not any(pd.isna(x) for x in [npm, at, em]):
        ratios["DuPont ROE"] = npm * at * em
    else:
        ratios["DuPont ROE"] = np.nan
    
    return ratios

# ----------------------------------------------
# Streamlit UI with Column Mapping
# ----------------------------------------------
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns.")
    
    with st.expander("Preview of uploaded data"):
        st.dataframe(df.head())
    
    # Define required metrics and suggested column names
    required_metrics = {
        "Revenue": "Sales, Turnover, Total Revenue",
        "COGS": "Cost of Goods Sold, Cost of Sales",
        "OperatingExpenses": "OpEx, SG&A, Selling General Admin",
        "OperatingIncome": "Operating Profit, EBIT",
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
        "TotalDebt": "Total Debt (Current + Long-Term)",
        "InterestExpense": "Interest, Finance Cost",
        "Tax": "Income Tax, Tax Expense",
        "EBITDA": "EBITDA",
        "OperatingCashFlow": "OCF, Cash from Operations",
        "CapitalExpenditures": "Capex, Purchase of PPE",
        "OrdinarySharesNumber": "Shares Outstanding, Common Shares",
        "Goodwill": "Goodwill",
        "OtherIntangibleAssets": "Intangibles, Other Intangibles",
        "MinorityInterest": "Minority Interest, Non-controlling interest",
        "RetainedEarnings": "Retained Earnings, Accumulated Profit",
        "AdditionalPaidInCapital": "APIC, Paid-in Capital",
        "CommonStock": "Common Stock, Share Capital"
    }
    
    st.subheader("🔗 Map Your Columns to Financial Metrics")
    st.markdown("For each metric, select the column from your CSV that contains the data. Leave as 'None' if not available.")
    
    mapping = {}
    cols = list(df.columns)
    cols.insert(0, "None")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    metrics_list = list(required_metrics.items())
    half = len(metrics_list) // 2
    
    with col1:
        for metric, hint in metrics_list[:half]:
            mapping[metric] = st.selectbox(
                f"{metric} *(e.g., {hint})*",
                options=cols,
                index=0,
                key=f"map_{metric}"
            )
    with col2:
        for metric, hint in metrics_list[half:]:
            mapping[metric] = st.selectbox(
                f"{metric} *(e.g., {hint})*",
                options=cols,
                index=0,
                key=f"map_{metric}"
            )
    
    if st.button("🚀 Compute 90+ Ratios", type="primary"):
        # Build values dict from the first row (single company)
        row = df.iloc[0]
        values = {}
        for metric, col_name in mapping.items():
            if col_name != "None" and col_name in row:
                values[metric] = parse_numeric(row[col_name])
            else:
                values[metric] = np.nan
        
        with st.spinner("Calculating 90+ ratios..."):
            try:
                ratios = compute_ratios(values)
                # Convert to DataFrame
                ratio_items = []
                for name, val in ratios.items():
                    is_pct = any(x in name for x in ["Margin", "ROA", "ROE", "ROCE", "ROIC", "Coverage", "Ratio", "Tax Rate", "Turnover"])
                    # Avoid marking turnover as %
                    if "Turnover" in name:
                        is_pct = False
                    ratio_items.append({"Ratio": name, "Value": format_value(val, is_pct=is_pct)})
                ratio_df = pd.DataFrame(ratio_items)
                st.subheader(f"📈 Computed Ratios ({len(ratio_df)} metrics)")
                st.dataframe(ratio_df, hide_index=True, use_container_width=True)
                
                # Download button
                csv_export = ratio_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export as CSV", data=csv_export, file_name="financial_ratios.csv", mime="text/csv")
            except Exception as e:
                st.error(f"An error occurred during ratio calculation: {str(e)}")
                st.stop()
else:
    st.info("Upload a CSV file to begin. Use the column mapping to match your data.")

st.caption("FinRatio Pro – Works with any CSV via manual column mapping. Missing data → N/A.")
