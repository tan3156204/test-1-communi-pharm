import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIG & DATA
# ==========================================
st.set_page_config(page_title="Communi-Pharm V13 (Financial Statements)", layout="wide")

# Constants
BASE_COST_RX = 11.23
CONST_FEE = 2.90
WEEKS = 13
EMERGENCY_LOAN_RATE = 0.50  # 50% Penalty Interest

# Competitor Data
COMPETITORS = [
    {"name": "LhaiJai", "loc": 1, "inputs": [49, 0.5, 0, 0, 1, 1, 48, 600, 100, 2000, 1, 0, 0, 55, 40000, 24000, 1, 9.75, 1, 4.9, 8050, 99, 48, 900, 0, 1000, 0, 0, 999999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "N&M", "loc": 2, "inputs": [30, 2.5, 0, 1, 1, 0, 60, 1500, 40, 3000, 3, 2000, 1, 38, 60000, 80000, 1, 21, 6.6, 4.75, 7000, 50, 48, 1299, 0, 1500, 0, 0, 999999, 0, 0, 1, 1, 1, 1, 0]},
    {"name": "NueyDeng", "loc": 2, "inputs": [30, 2.4, 0.25, 0, 1, 0, 70, 1900, 40, 3000, 3, 2000, 1, 39, 65000, 120000, 1.3, 22.75, 7, 5, 8000, 50, 48, 1200, 0, 2300, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Puaypepakor", "loc": 2, "inputs": [40, 0.9, 0.25, 0, 0, 0, 70, 1500, 33, 2000, 3, 0, 0, 34, 65000, 145000, 1.5, 19.5, 6.5, 4.75, 8000, 66, 48, 1200, 0, 2200, 0, 0, 99999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "HappyPills", "loc": 3, "inputs": [35, 2.2, 0, 0, 0, 1, 90, 2200, 34, 2000, 1, 0, 0, 33, 85000, 145000, 1.5, 20, 8.9, 4.75, 8000, 30, 48, 2000, 0, 2500, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Oceanville", "loc": 3, "inputs": [38, 1.8, 0, 0, 1, 0, 75, 3000, 10, 10000, 2, 10000, 3, 37, 65000, 75000, 1.75, 22, 8, 5.12, 8000, 50, 48, 1300, 0, 2200, 0, 0, 999999, 0, 0, 0, 1, 0, 1, 0]}
]

WEIGHTS_RX = {
    1: {'price': 10, 'fee': 30, 'promo': 5, 'hours': 20, 'delivery': 5, 'records': 10, 'credit': 5, 'inv': 5},
    2: {'price': 20, 'fee': 25, 'promo': 10, 'hours': 10, 'delivery': 10, 'records': 5, 'credit': 5, 'inv': 5},
    3: {'price': 40, 'fee': 30, 'promo': 15, 'hours': 5, 'delivery': 0, 'records': 0, 'credit': 5, 'inv': 0}
}

# ==========================================
# 2. LOGIC ENGINE
# ==========================================
def run_simulation(user_inputs):
    user_team = {"name": "Thaikritosot (You)", "loc": 1, "inputs": user_inputs}
    all_teams = [user_team] + COMPETITORS
    
    # Store Financial Statements Data
    financial_report = {} 

    for loc_id in [1, 2, 3]:
        teams_in_loc = [t for t in all_teams if t['loc'] == loc_id]
        if not teams_in_loc: continue
        
        # --- A. RANKING & MARKET SHARE ---
        df = pd.DataFrame()
        for t in teams_in_loc:
            i = t['inputs']
            price = (BASE_COST_RX * (1 + i[0]/100)) + i[1] + CONST_FEE
            df = pd.concat([df, pd.DataFrame([{
                'name': t['name'], 'inputs': i, 'price': price, 
                'promo': i[7], 'hours': i[6]
            }])], ignore_index=True)
        
        w = WEIGHTS_RX[loc_id]
        min_price = df['price'].min()
        max_promo = df['promo'].max() if df['promo'].max() > 0 else 1
        
        df['score'] = ((min_price/df['price'])*w.get('price',0)*3) + ((df['promo']/max_promo)*w.get('promo',0)) + ((df['hours']/168)*w.get('hours',0)*2)
        df['share'] = df['score'] / df['score'].sum()

        # --- B. FINANCIALS ---
        MARKET_SIZE = 280000 if loc_id == 1 else 1300000
        if loc_id == 3: MARKET_SIZE = 800000

        for idx, row in df.iterrows():
            if row['name'] != "Thaikritosot (You)": continue # Calculate details for user only
            
            inp = row['inputs']
            
            # --- 1. Income Statement (งบกำไรขาดทุน) ---
            sales = row['share'] * MARKET_SIZE
            cogs = sales / (1 + (inp[0]/100)) # Expense (ต้นทุนขาย)
            gross_margin = sales - cogs
            
            # Expenses
            wages = ((inp[16]*inp[17]) + (inp[18]*inp[19])) * inp[6] * WEEKS
            fixed_ops = inp[20] + inp[23] + inp[7] + 3000
            depreciation = 50000 * 0.02 # สมมติ Fixed Assets 50k
            
            operating_profit = gross_margin - wages - fixed_ops - depreciation
            
            # --- 2. Cash Flow & Balance Sheet Logic ---
            cash_begin = 15000
            retained_earnings_begin = 138000 # จากไฟล์ก่อนหน้า
            
            # Cash Inflow/Outflow
            cash_receipts = sales * 0.9 # เก็บเงินได้ 90%
            purchases = inp[14] + inp[15] # Expenditure (รายจ่ายซื้อของ)
            ap_payment = inp[28] # จ่ายหนี้เจ้าหนี้
            
            cash_expenses_paid = wages + fixed_ops # จ่ายค่าใช้จ่ายเป็นเงินสด
            
            # Preliminary Cash Balance
            cash_balance = cash_begin + cash_receipts - purchases - ap_payment - cash_expenses_paid
            
            # Emergency Loan Logic
            emergency_loan = 0
            interest = 0
            if cash_balance < 0:
                shortage = abs(cash_balance)
                emergency_loan = shortage + 1000
                interest = emergency_loan * EMERGENCY_LOAN_RATE # Penalty Interest
                cash_balance += emergency_loan
            
            net_profit = operating_profit - interest
            
            # Balance Sheet Items
            inventory_end = (55000 + 25000) + purchases - cogs # Beginning + Buy - Sold
            ar_end = 45000 + (sales * 0.1) # Old AR + Uncollected Sales
            ap_end = 30000 + purchases - ap_payment # Old AP + New Debt (Purchases) - Paid
            
            total_assets = cash_balance + inventory_end + ar_end + (50000 - depreciation)
            total_liabilities = ap_end + emergency_loan + 100000 # + Long Term Debt
            total_equity = retained_earnings_begin + net_profit
            
            financial_report = {
                "Income Statement": {
                    "Total Sales": sales,
                    "COGS": cogs,
                    "Gross Margin": gross_margin,
                    "Wages": wages,
                    "Fixed Expenses": fixed_ops,
                    "Depreciation": depreciation,
                    "Interest (Penalty)": interest,
                    "Net Profit": net_profit
                },
                "Balance Sheet": {
                    "Cash": cash_balance,
                    "Inventory": inventory_end,
                    "Accounts Receivable": ar_end,
                    "Fixed Assets (Net)": 50000 - depreciation,
                    "Total Assets": total_assets,
                    "Accounts Payable": ap_end,
                    "Emergency Loan": emergency_loan,
                    "Long Term Debt": 100000,
                    "Total Liabilities": total_liabilities,
                    "Owners Equity": total_equity
                },
                "Analysis": {
                    "Purchases (Expenditure)": purchases,
                    "COGS (Expense)": cogs,
                    "Emergency Loan Triggered": emergency_loan > 0
                }
            }

    return financial_report

# ==========================================
# 3. USER INTERFACE
# ==========================================
st.sidebar.header("🛠️ Thaikritosot Inputs")
def user_controls():
    defaults = [49, 0, 0, 1, 1, 1, 46, 600, 90, 2000, 3, 0, 0, 47, 40000, 16000, 0.8, 21, 1.2, 4.75, 8050, 99, 48, 898, 0, 1000, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]
    inputs = [0] * 36
    
    st.sidebar.warning("⚡ ระวัง: Input 29 (Pay A/P) กับ Input 15,16 (Purchases)")
    inputs[28] = st.sidebar.number_input("29. Pay A/P ($)", value=0)
    inputs[14] = st.sidebar.number_input("15. Rx Purchase ($)", value=defaults[14])
    inputs[15] = st.sidebar.number_input("16. Other Purchase ($)", value=defaults[15])
    inputs[6] = st.sidebar.number_input("7. Hours/Week", value=defaults[6])
    inputs[0] = st.sidebar.number_input("1. Rx Markup (%)", value=defaults[0])
    inputs[7] = st.sidebar.number_input("8. Promo ($)", value=defaults[7])
    
    for i in range(36):
        if inputs[i] == 0: inputs[i] = defaults[i]
    return inputs

inputs = user_controls()
report = run_simulation(inputs)

st.title("📊 Financial Statements (ตามหลักการบัญชี)")

if report:
    tab1, tab2, tab3 = st.tabs(["📄 Income Statement", "⚖️ Balance Sheet", "💡 Key Concepts"])
    
    with tab1:
        st.subheader("งบกำไรขาดทุน (Income Statement)")
        st.caption("แสดงผลการดำเนินงาน (กำไร/ขาดทุน) ในช่วงเวลานี้")
        
        inc = report['Income Statement']
        
        # Display as a clean table
        df_inc = pd.DataFrame([
            ["(+) Total Sales", inc['Total Sales']],
            ["(-) Cost of Goods Sold (Expense)", inc['COGS']],
            ["(=) Gross Margin", inc['Gross Margin']],
            ["(-) Wages", inc['Wages']],
            ["(-) Fixed Expenses", inc['Fixed Expenses']],
            ["(-) Depreciation", inc['Depreciation']],
            ["(-) Interest (Penalty)", inc['Interest (Penalty)']],
            ["(=) Net Profit", inc['Net Profit']]
        ], columns=["Item", "Amount ($)"])
        
        st.dataframe(df_inc.style.format({"Amount ($)": "{:,.2f}"}), use_container_width=True)
        
        if inc['Net Profit'] < 0:
            st.error(f"Loss: ${inc['Net Profit']:,.2f}")
        else:
            st.success(f"Profit: ${inc['Net Profit']:,.2f}")

    with tab2:
        st.subheader("งบดุล (Balance Sheet)")
        st.caption("สมการบัญชี: Assets = Liabilities + Equity")
        
        bal = report['Balance Sheet']
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🟢 Assets (สินทรัพย์)")
            st.write(f"Cash: ${bal['Cash']:,.2f}")
            st.write(f"Inventory: ${bal['Inventory']:,.2f}")
            st.write(f"A/R: ${bal['Accounts Receivable']:,.2f}")
            st.write(f"Fixed Assets: ${bal['Fixed Assets (Net)']:,.2f}")
            st.markdown(f"**Total Assets: ${bal['Total Assets']:,.2f}**")
            
        with c2:
            st.markdown("### 🔴 Liabilities & Equity")
            st.write(f"A/P: ${bal['Accounts Payable']:,.2f}")
            st.write(f"Emergency Loan: ${bal['Emergency Loan']:,.2f}")
            st.write(f"Long Term Debt: ${bal['Long Term Debt']:,.2f}")
            st.markdown(f"**Total Liabilities: ${bal['Total Liabilities']:,.2f}**")
            st.markdown("---")
            st.markdown(f"**Owners Equity: ${bal['Owners Equity']:,.2f}**")
            
        # Check Equation
        diff = bal['Total Assets'] - (bal['Total Liabilities'] + bal['Owners Equity'])
        if abs(diff) < 1:
            st.success("✅ Balance Sheet ลงตัว (Assets = Liab + Equity)")
        else:
            st.error(f"❌ Balance Sheet ไม่ลงตัว (Diff: {diff})")

    with tab3:
        st.subheader("บทเรียนบัญชี (Accounting Concepts)")
        
        st.markdown("#### 1. Expenditure vs Expense")
        
        col_a, col_b = st.columns(2)
        col_a.metric("Purchases (Expenditure)", f"${report['Analysis']['Purchases (Expenditure)']:,.2f}", help="เงินสดที่จ่ายเพื่อซื้อของเข้าสต็อก (กระทบ Cash Flow)")
        col_b.metric("COGS (Expense)", f"${report['Analysis']['COGS (Expense)']:,.2f}", help="ต้นทุนของสินค้าที่ขายออกไปจริง (กระทบ Net Profit)")
        st.info("💡 สังเกตว่าตัวเลขไม่เท่ากัน! การซื้อของเยอะๆ (Expenditure) จะทำให้เงินสดหมด แต่ไม่ทำให้กำไรลดลงทันที (จนกว่าจะขายออก)")

        st.markdown("#### 2. Net Profit vs Cash")
        col_c, col_d = st.columns(2)
        col_c.metric("Net Profit", f"${inc['Net Profit']:,.2f}")
        col_d.metric("Cash Balance", f"${bal['Cash']:,.2f}")
        
        if report['Analysis']['Emergency Loan Triggered']:
            st.error("⚠️ **Case Study:** กำไรคุณอาจจะดูดี แต่เงินสดคุณติดลบจนต้องกู้ (Emergency Loan) เพราะคุณจ่ายหนี้ (Input 29) หรือซื้อของมากเกินไป!")
else:
    st.write("Calculating...")
