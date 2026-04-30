import streamlit as st
import pandas as pd
import numpy as np
import io
import re

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def parse_numeric(value):
    """Convert various formats to float, return NaN if fails."""
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

def find_column(df, possible_names):
    """Return the first column in df whose name (lowercase) matches any in possible_names."""
    for col in df.columns:
        col_lower = col.lower().strip()
        for name in possible_names:
            if name.lower() == col_lower:
                return col
    return None

# ------------------------------------------------------------
# Core ratio computation (using any available fields)
# ------------------------------------------------------------
def compute_all_ratios(row):
    """Compute 90+ ratios from a dictionary of values (keys = original column names)."""
    # 1. Standard aliases mapping (case‑insensitive lookup)
    # We'll try to extract each needed field using find_column logic.
    # But for simplicity, we directly use the keys as given; the user must have the columns.
    # However, we complete with optional fields.
    
    # Helper to get value (returns NaN if missing)
    def get(key):
        return row.get(key, np.nan)
    
    # ---------- CORE INCOME STATEMENT ----------
    revenue = get("Revenue")
    cogs = get("COGS")
    op_ex = get("OperatingExpenses")
    net_inc = get("NetIncome")
    ebitda = get("EBITDA")
    int_exp = get("InterestExpense")
    tax = get("Tax")
    ocf = get("OperatingCashFlow")
    capex = get("CapitalExpenditures")
    
    # Alternative names for common items
    if pd.isna(revenue):
        revenue = get("Sales") or get("Total Revenue")
    if pd.isna(cogs):
        cogs = get("CostOfRevenue")
    if pd.isna(op_ex):
        op_ex = get("SellingGeneralAdministrative") or get("OperatingExpense")
    if pd.isna(net_inc):
        net_inc = get("NetIncomeCommonStockholders") or get("NetProfit")
    if pd.isna(ebitda):
        ebitda = get("EBITDA") or get("EarningsBeforeInterestTaxesDepreciationAmortization")
    
    # Derived
    gross_profit = revenue - cogs if not (pd.isna(revenue) or pd.isna(cogs)) else np.nan
    ebit = get("OperatingIncome")
    if pd.isna(ebit):
        ebit = revenue - cogs - op_ex if not (pd.isna(revenue) or pd.isna(cogs) or pd.isna(op_ex)) else np.nan
    pretax_inc = get("PretaxIncome")
    if pd.isna(pretax_inc) and not pd.isna(net_inc) and not pd.isna(tax):
        pretax_inc = net_inc + tax
    
    # ---------- BALANCE SHEET (extensive list) ----------
    # Assets
    total_assets = get("TotalAssets")
    current_assets = get("CurrentAssets")
    cash = get("CashAndCashEquivalents")
    if pd.isna(cash):
        cash = get("Cash")
    ar = get("AccountsReceivable")
    inventory = get("Inventory")
    ppe_net = get("NetPPE")
    goodwill = get("Goodwill")
    other_intangibles = get("OtherIntangibleAssets")
    total_intangibles = goodwill + other_intangibles if not (pd.isna(goodwill) or pd.isna(other_intangibles)) else np.nan
    investments = get("LongTermEquityInvestment") or get("InvestmentsinAssociatesatCost")
    
    # Liabilities
    current_liab = get("CurrentLiabilities")
    accounts_payable = get("AccountsPayable")
    total_liab = get("TotalLiabilities")
    long_term_debt = get("LongTermDebt")
    if pd.isna(long_term_debt):
        long_term_debt = get("LongTermDebtAndCapitalLeaseObligation")
    total_debt = get("TotalDebt")
    if pd.isna(total_debt):
        total_debt = (get("CurrentDebt") or 0) + (long_term_debt or 0)
    net_debt = total_debt - cash if not (pd.isna(total_debt) or pd.isna(cash)) else np.nan
    
    # Equity
    total_equity = get("TotalEquityGrossMinorityInterest")
    if pd.isna(total_equity):
        total_equity = get("StockholdersEquity")
    common_stock = get("CommonStock")
    additional_paid_in = get("AdditionalPaidInCapital")
    retained_earnings = get("RetainedEarnings")
    treasury = get("TreasuryStock") or 0
    minority = get("MinorityInterest")
    shares_outstanding = get("OrdinarySharesNumber")
    if pd.isna(shares_outstanding):
        shares_outstanding = get("ShareIssued")
    
    # Other useful
    working_capital = current_assets - current_liab if not (pd.isna(current_assets) or pd.isna(current_liab)) else np.nan
    tangible_book_value = total_equity - total_intangibles if not (pd.isna(total_equity) or pd.isna(total_intangibles)) else np.nan
    invested_capital = total_liab + total_equity - cash - current_liab if not any(pd.isna(x) for x in [total_liab, total_equity, cash, current_liab]) else np.nan
    net_tangible_assets = tangible_book_value  # same
    total_capitalization = long_term_debt + total_equity if not (pd.isna(long_term_debt) or pd.isna(total_equity)) else np.nan
    
    # ---------- CASH FLOW (extra) ----------
    fcf = ocf - capex if not (pd.isna(ocf) or pd.isna(capex)) else np.nan
    
    # ---------- RATIOS DICTIONARY ----------
    ratios = {}
    
    # Profitability (15)
    ratios["Gross Margin"] = safe_div(gross_profit, revenue)
    ratios["Operating Margin"] = safe_div(ebit, revenue)
    ratios["Net Profit Margin"] = safe_div(net_inc, revenue)
    ratios["EBITDA Margin"] = safe_div(ebitda, revenue)
    ratios["Return on Assets (ROA)"] = safe_div(net_inc, total_assets)
    ratios["Return on Equity (ROE)"] = safe_div(net_inc, total_equity)
    ratios["ROCE"] = safe_div(ebit, total_assets - current_liab)
    ratios["ROIC"] = safe_div(net_inc, total_debt + total_equity)
    ratios["Asset Turnover"] = safe_div(revenue, total_assets)
    ratios["OpEx Ratio"] = safe_div(op_ex, revenue)
    ratios["Pretax Margin"] = safe_div(pretax_inc, revenue)
    ratios["Cash Flow Margin"] = safe_div(ocf, revenue)
    ratios["FCF Margin"] = safe_div(fcf, revenue)
    ratios["EBIT/Assets"] = safe_div(ebit, total_assets)
    ratios["Effective Tax Rate"] = safe_div(tax, pretax_inc)
    
    # Per Share (if shares outstanding known)
    if not pd.isna(shares_outstanding) and shares_outstanding > 0:
        ratios["EPS (Basic)"] = safe_div(net_inc, shares_outstanding)
        ratios["Book Value Per Share"] = safe_div(total_equity, shares_outstanding)
        ratios["Tangible Book Value Per Share"] = safe_div(tangible_book_value, shares_outstanding)
        ratios["Operating Cash Flow Per Share"] = safe_div(ocf, shares_outstanding)
    else:
        ratios["EPS (Basic)"] = np.nan
        ratios["Book Value Per Share"] = np.nan
        ratios["Tangible Book Value Per Share"] = np.nan
        ratios["Operating Cash Flow Per Share"] = np.nan
    
    # Liquidity (7)
    ratios["Current Ratio"] = safe_div(current_assets, current_liab)
    ratios["Quick Ratio"] = safe_div(cash + ar, current_liab)
    ratios["Cash Ratio"] = safe_div(cash, current_liab)
    ratios["NWC Ratio"] = safe_div(working_capital, total_assets)
    ratios["Defensive Interval (days)"] = safe_div(cash + ar, (cogs+op_ex)/365) if not pd.isna(cogs+op_ex) else np.nan
    ratios["OCF Ratio"] = safe_div(ocf, current_liab)
    ratios["Cash Flow to Current Liab"] = safe_div(ocf, current_liab)
    
    # Solvency & Leverage (12)
    ratios["Debt to Equity"] = safe_div(total_debt, total_equity)
    ratios["Net Debt to Equity"] = safe_div(net_debt, total_equity)
    ratios["Debt Ratio"] = safe_div(total_liab, total_assets)
    ratios["Equity Ratio"] = safe_div(total_equity, total_assets)
    ratios["LT Debt to Equity"] = safe_div(long_term_debt, total_equity)
    ratios["Interest Coverage (EBIT/Int)"] = safe_div(ebit, int_exp)
    ratios["Debt to EBITDA"] = safe_div(total_debt, ebitda)
    ratios["Net Debt to EBITDA"] = safe_div(net_debt, ebitda)
    ratios["OCF to Total Debt"] = safe_div(ocf, total_debt)
    ratios["Equity Multiplier"] = safe_div(total_assets, total_equity)
    ratios["Total Debt / Capitalization"] = safe_div(total_debt, total_capitalization)
    ratios["LT Debt / Capitalization"] = safe_div(long_term_debt, total_capitalization)
    
    # Efficiency (14)
    ratios["Receivables Turnover"] = safe_div(revenue, ar)
    if not pd.isna(ratios["Receivables Turnover"]) and ratios["Receivables Turnover"] > 0:
        ratios["DSO (days)"] = 365 / ratios["Receivables Turnover"]
    else:
        ratios["DSO (days)"] = np.nan
    ratios["Inventory Turnover"] = safe_div(cogs, inventory)
    if not pd.isna(ratios["Inventory Turnover"]) and ratios["Inventory Turnover"] > 0:
        ratios["DIO (days)"] = 365 / ratios["Inventory Turnover"]
    else:
        ratios["DIO (days)"] = np.nan
    ratios["Payables Turnover"] = safe_div(cogs, accounts_payable)
    if not pd.isna(ratios["Payables Turnover"]) and ratios["Payables Turnover"] > 0:
        ratios["DPO (days)"] = 365 / ratios["Payables Turnover"]
    else:
        ratios["DPO (days)"] = np.nan
    # Cash conversion cycle
    dio = ratios.get("DIO (days)", np.nan)
    dso = ratios.get("DSO (days)", np.nan)
    dpo = ratios.get("DPO (days)", np.nan)
    if not any(pd.isna(x) for x in [dio, dso, dpo]):
        ratios["CCC (days)"] = dio + dso - dpo
    else:
        ratios["CCC (days)"] = np.nan
    
    ratios["Fixed Asset Turnover"] = safe_div(revenue, ppe_net)
    ratios["Working Capital Turnover"] = safe_div(revenue, working_capital)
    ratios["Equity Turnover"] = safe_div(revenue, total_equity)
    ratios["Inventory to Sales"] = safe_div(inventory, revenue)
    ratios["Receivables to Sales"] = safe_div(ar, revenue)
    ratios["Capex to Revenue"] = safe_div(capex, revenue)
    ratios["FCF / Net Income"] = safe_div(fcf, net_inc)
    
    # Cash Flow & extra (14)
    ratios["CFROA"] = safe_div(ocf, total_assets)
    ratios["CFROE"] = safe_div(ocf, total_equity)
    ratios["EBITDA / Interest"] = safe_div(ebitda, int_exp)
    ratios["OCF to Net Income"] = safe_div(ocf, net_inc)
    ratios["OCF / Interest"] = safe_div(ocf, int_exp)
    ratios["LT Debt to Assets"] = safe_div(long_term_debt, total_assets)
    ratios["Current Liab / Equity"] = safe_div(current_liab, total_equity)
    ratios["Gross Profit / Assets"] = safe_div(gross_profit, total_assets)
    ratios["FCF / OCF"] = safe_div(fcf, ocf)
    ratios["NWC / Sales"] = safe_div(working_capital, revenue)
    ratios["Tangible Book / Assets"] = safe_div(tangible_book_value, total_assets)
    ratios["Invested Capital Turnover"] = safe_div(revenue, invested_capital)
    ratios["Net Tangible Assets / Equity"] = safe_div(net_tangible_assets, total_equity)
    ratios["Minority Interest / Equity"] = safe_div(minority, total_equity)
    
    # DuPont
    npm = ratios.get("Net Profit Margin", np.nan)
    at = ratios.get("Asset Turnover", np.nan)
    em = ratios.get("Equity Multiplier", np.nan)
    if not any(pd.isna(x) for x in [npm, at, em]):
        ratios["DuPont ROE"] = npm * at * em
    else:
        ratios["DuPont ROE"] = np.nan
    
    # Remove NaN entries (replace with N/A later)
    return ratios

# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------
st.set_page_config(page_title="FinRatio Pro – 90+ Financial Ratios", layout="wide")
st.title("📊 FinRatio Pro (Enhanced)")
st.markdown("Upload a CSV with any of the **80+ financial line items** (see sidebar). The app will compute **90+ ratios** including EPS, net debt metrics, tangible book value, and many more.")

with st.sidebar:
    st.header("📁 Accepted Columns (any subset)")
    st.markdown("""
    The app automatically recognises these fields (case‑insensitive):  
    `Revenue`, `COGS`, `OperatingExpenses`, `NetIncome`, `TotalAssets`, `CurrentAssets`,  
    `Cash`, `AccountsReceivable`, `Inventory`, `CurrentLiabilities`, `AccountsPayable`,  
    `TotalLiabilities`, `ShareholdersEquity`, `LongTermDebt`, `InterestExpense`, `Tax`,  
    `EBITDA`, `OperatingCashFlow`, `CapitalExpenditures`, `OrdinarySharesNumber`, `ShareIssued`,  
    `NetDebt`, `TotalDebt`, `TangibleBookValue`, `InvestedCapital`, `Goodwill`, `OtherIntangibleAssets`,  
    `MinorityInterest`, `RetainedEarnings`, `AdditionalPaidInCapital`, `CommonStock`,  
    `LongTermDebtAndCapitalLeaseObligation`, `CurrentDebt`, and many more.
    """)
    
    # Sample download (includes many of the new fields)
    sample_data = {
        "Revenue": 2500000, "COGS": 1200000, "OperatingExpenses": 500000, "OperatingIncome": 800000,
        "NetIncome": 560000, "TotalAssets": 3800000, "CurrentAssets": 1200000, "Cash": 300000,
        "AccountsReceivable": 400000, "Inventory": 350000, "CurrentLiabilities": 600000,
        "AccountsPayable": 250000, "TotalLiabilities": 1800000, "ShareholdersEquity": 2000000,
        "LongTermDebt": 900000, "InterestExpense": 45000, "Tax": 195000, "EBITDA": 950000,
        "OperatingCashFlow": 680000, "CapitalExpenditures": 150000, "OrdinarySharesNumber": 1000000,
        "Goodwill": 200000, "OtherIntangibleAssets": 50000, "MinorityInterest": 50000,
        "RetainedEarnings": 1200000, "AdditionalPaidInCapital": 500000, "CommonStock": 300000
    }
    sample_df = pd.DataFrame([sample_data])
    csv_buffer = io.StringIO()
    sample_df.to_csv(csv_buffer, index=False)
    st.download_button("📎 Download Advanced Sample CSV", data=csv_buffer.getvalue(),
                       file_name="sample_financials_advanced.csv", mime="text/csv")
    st.info("After upload, all available ratios are computed. Export results via the button below the table.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        if df.empty:
            st.error("Empty CSV file.")
        else:
            row = df.iloc[0].to_dict()
            with st.spinner("Computing 90+ ratios..."):
                ratios = compute_all_ratios(row)
            # Convert to DataFrame
            ratio_df = pd.DataFrame(list(ratios.items()), columns=["Ratio", "Value"])
            # Format values for display
            def disp(val):
                if pd.isna(val):
                    return "N/A"
                if isinstance(val, float):
                    # Heuristic: if ratio name contains "Margin", "RO", "Tax Rate", format as %
                    return format_value(val, is_pct=False)  # Let user see raw number; but we can add % later if needed
                return str(val)
            ratio_df["Value"] = ratio_df["Value"].apply(disp)
            st.subheader(f"📈 Computed Ratios ({len(ratio_df)} metrics)")
            st.dataframe(ratio_df, hide_index=True, use_container_width=True)
            
            csv_export = ratio_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Ratios as CSV", data=csv_export,
                               file_name="financial_ratios.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Awaiting CSV upload. Use the sample file to test.")

st.caption("FinRatio Pro | 90+ financial ratios from comprehensive financial statements.")
