import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. GAME SETTINGS & CONSTANTS (ตามคู่มือ)
# ==========================================
st.set_page_config(page_title="Communi-Pharm V15 (Original Settings)", layout="wide")

# ค่าคงที่พื้นฐาน
BASE_COST_RX = 11.23
CONST_FEE = 2.90
WEEKS_PER_PERIOD = 13  # 1 รอบ = 3 เดือน (ไตรมาส)

# --- LOCATION CONFIGURATION (ตามคู่มือหน้า 13:25) ---
LOCATION_CONFIG = {
    1: {
        "name": "Medical Center",
        "desc": "ร้านยาในศูนย์การแพทย์ (เน้นยาตามใบสั่ง)",
        "rent_rate": 0.045, # 4.5% ของยอดขาย
        "area_size": "800-1300 sq.ft"
    },
    2: {
        "name": "Neighborhood",
        "desc": "ร้านยาใกล้บ้าน (ชุมชน 20-30k คน)",
        "rent_rate": 0.030, # 3.0% ของยอดขาย
        "area_size": "Medium"
    },
    3: {
        "name": "Shopping Center",
        "desc": "ร้านยาในห้าง (Chain Store)",
        "rent_rate": 0.025, # 2.5% ของยอดขาย
        "area_size": "3500-3800 sq.ft"
    }
}

# --- COMPETITOR DATA (BOTS) ---
COMPETITORS = [
    {"name": "LhaiJai", "loc": 1, "inputs": [49, 0.5, 0, 0, 1, 1, 48, 600, 100, 2000, 1, 0, 0, 55, 40000, 24000, 1, 9.75, 1, 4.9, 8050, 99, 48, 900, 0, 1000, 0, 0, 999999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "N&M", "loc": 2, "inputs": [30, 2.5, 0, 1, 1, 0, 60, 1500, 40, 3000, 3, 2000, 1, 38, 60000, 80000, 1, 21, 6.6, 4.75, 7000, 50, 48, 1299, 0, 1500, 0, 0, 999999, 0, 0, 1, 1, 1, 1, 0]},
    {"name": "NueyDeng", "loc": 2, "inputs": [30, 2.4, 0.25, 0, 1, 0, 70, 1900, 40, 3000, 3, 2000, 1, 39, 65000, 120000, 1.3, 22.75, 7, 5, 8000, 50, 48, 1200, 0, 2300, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Puaypepakor", "loc": 2, "inputs": [40, 0.9, 0.25, 0, 0, 0, 70, 1500, 33, 2000, 3, 0, 0, 34, 65000, 145000, 1.5, 19.5, 6.5, 4.75, 8000, 66, 48, 1200, 0, 2200, 0, 0, 99999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "HappyPills", "loc": 3, "inputs": [35, 2.2, 0, 0, 0, 1, 90, 2200, 34, 2000, 1, 0, 0, 33, 85000, 145000, 1.5, 20, 8.9, 4.75, 8000, 30, 48, 2000, 0, 2500, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Oceanville", "loc": 3, "inputs": [38, 1.8, 0, 0, 1, 0, 75, 3000, 10, 10000, 2, 10000, 3, 37, 65000, 75000, 1.75, 22, 8, 5.12, 8000, 50, 48, 1300, 0, 2200, 0, 0, 999999, 0, 0, 0, 1, 0, 1, 0]}
]

# Market Weights (เหมือนเดิม)
WEIGHTS_RX = {
    1: {'price': 10, 'fee': 30, 'promo': 5, 'hours': 20, 'delivery': 5, 'records': 10, 'credit': 5, 'inv': 5},
    2: {'price': 20, 'fee': 25, 'promo': 10, 'hours': 10, 'delivery': 10, 'records': 5, 'credit': 5, 'inv': 5},
    3: {'price': 40, 'fee': 30, 'promo': 15, 'hours': 5, 'delivery': 0, 'records': 0, 'credit': 5, 'inv': 0}
}

# ==========================================
# 2. LOGIC ENGINE
# ==========================================
def run_simulation(user_inputs, user_loc_id):
    # Setup User Team
    user_team = {"name": "Thaikritosot (You)", "loc": user_loc_id, "inputs": user_inputs}
    all_teams = [user_team] + COMPETITORS
    
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
        
        # Scoring Logic
        df['score'] = ((min_price/df['price'])*w.get('price',0)*3) + ((df['promo']/max_promo)*w.get('promo',0)) + ((df['hours']/168)*w.get('hours',0)*2)
        df['share'] = df['score'] / df['score'].sum()

        # --- B. FINANCIALS (Manual Logic) ---
        MARKET_SIZE = 280000 if loc_id == 1 else 1300000
        if loc_id == 3: MARKET_SIZE = 800000

        for idx, row in df.iterrows():
            if row['name'] != "Thaikritosot (You)": continue
            
            inp = row['inputs']
            
            # 1. Sales
            sales = row['share'] * MARKET_SIZE
            
            # 2. COGS
            cogs = sales / (1 + (inp[0]/100))
            gross_margin = sales - cogs
            
            # 3. Expenses
            # Wages
            wage_cost_hr = (inp[16]*inp[17]) + (inp[18]*inp[19])
            wages_total = wage_cost_hr * inp[6] * WEEKS_PER_PERIOD
            
            # Rent (คำนวณตามคู่มือ: % ของยอดขาย)
            rent_rate = LOCATION_CONFIG[loc_id]["rent_rate"]
            rent_expense = sales * rent_rate
            
            # Depreciation (Straight Line)
            fixed_assets = 50000 # สมมติ
            depreciation = fixed_assets * (0.10 / 4) # สมมติ 10% ต่อปี / 4 ไตรมาส
            
            # Other Fixed
            mgr_salary = inp[20]
            promo = inp[7]
            other_fixed = 3000
            
            total_operating_expenses = wages_total + rent_expense + depreciation + mgr_salary + promo + other_fixed
            
            # 4. Interest Income / Expense
            # Input 10 = Investment, Input 32 = Interest Rate (Assume %)
            investment_income = inp[9] * 0.015 # สมมติผลตอบแทน 1.5% ต่อไตรมาส
            
            # Emergency Loan Interest (Logic เดิมที่ถูกต้อง)
            cash_begin = 15000
            purchases = inp[14] + inp[15]
            ap_payment = inp[28]
            cash_in = sales * 0.9
            
            # Cash Flow Check
            cash_out_immediate = wages_total + rent_expense + mgr_salary + promo + other_fixed
            cash_balance = cash_begin + cash_in - purchases - ap_payment - cash_out_immediate
            
            emergency_loan = 0
            interest_expense = 0
            if cash_balance < 0:
                emergency_loan = abs(cash_balance) + 2000
                interest_expense = emergency_loan * 0.20 # 20% Penalty
                cash_balance += emergency_loan
            
            # Special Penalty for 999999
            if ap_payment > 100000: interest_expense += 29000000
                
            # Net Interest
            net_interest = investment_income - interest_expense
            
            # 5. Net Profit
            # Formula: (Gross Margin - Expenses) + Interest Income
            net_profit = (gross_margin - total_operating_expenses) + net_interest
            
            # Report Data
            financial_report = {
                "Loc Name": LOCATION_CONFIG[loc_id]["name"],
                "Rent Rate": rent_rate * 100,
                "Income Statement": {
                    "Sales": sales,
                    "COGS": cogs,
                    "Gross Margin": gross_margin,
                    "Wages": wages_total,
                    "Rent": rent_expense,
                    "Depreciation": depreciation,
                    "Promo": promo,
                    "Mgr Salary": mgr_salary,
                    "Other Fixed": other_fixed,
                    "Total Expenses": total_operating_expenses,
                    "Operating Profit": gross_margin - total_operating_expenses,
                    "Interest Income": investment_income,
                    "Interest Expense": interest_expense,
                    "Net Profit": net_profit
                },
                "Balance Sheet": {
                    "Cash": cash_balance,
                    "Inventory": 80000 + purchases - cogs,
                    "Emergency Loan": emergency_loan
                }
            }

    return financial_report

# ==========================================
# 3. GUI
# ==========================================
st.sidebar.header("🛠️ Thaikritosot Settings")

# Location Selector
loc_select = st.sidebar.selectbox("เลือกทำเล (Location)", [1, 2, 3], format_func=lambda x: f"{x}: {LOCATION_CONFIG[x]['name']}")
st.sidebar.caption(f"ℹ️ {LOCATION_CONFIG[loc_select]['desc']} | ค่าเช่า: {LOCATION_CONFIG[loc_select]['rent_rate']*100}% ของยอดขาย")

def user_controls():
    defaults = [49, 0, 0, 1, 1, 1, 46, 600, 90, 2000, 3, 0, 0, 47, 40000, 16000, 0.8, 21, 1.2, 4.75, 8050, 99, 48, 898, 0, 1000, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]
    inputs = [0] * 36
    
    with st.sidebar.expander("💰 Financials", expanded=True):
        inputs[28] = st.number_input("29. Pay A/P ($)", value=0)
        inputs[9] = st.number_input("10. Current Investment ($)", value=2000)
    
    with st.sidebar.expander("🏪 Operations", expanded=True):
        inputs[6] = st.number_input("7. Hours/Week", value=defaults[6])
        inputs[0] = st.number_input("1. Rx Markup (%)", value=defaults[0])
        inputs[7] = st.number_input("8. Promo ($)", value=defaults[7])
        
    with st.sidebar.expander("📦 Inventory", expanded=False):
        inputs[14] = st.number_input("15. Rx Purchase ($)", value=defaults[14])
        inputs[15] = st.number_input("16. Other Purchase ($)", value=defaults[15])
    
    for i in range(36):
        if inputs[i] == 0: inputs[i] = defaults[i]
    return inputs

inputs = user_controls()

# Run Simulation
report = run_simulation(inputs, loc_select)

st.title("💊 Communi-Pharm Simulator V15")
st.markdown("**Original Game Settings Edition:** ปรับค่าเช่าและงบการเงินตามคู่มือ")

if report:
    inc = report['Income Statement']
    
    # Header Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Location", report['Loc Name'])
    c2.metric("Rent Expense", f"${inc['Rent']:,.0f}", f"({report['Rent Rate']}%)")
    c3.metric("Sales", f"${inc['Sales']:,.0f}")
    c4.metric("Net Profit", f"${inc['Net Profit']:,.0f}", delta_color="normal" if inc['Net Profit']>0 else "inverse")
    
    # Detailed Income Statement
    st.subheader("📄 งบกำไรขาดทุน (Income Statement)")
    st.markdown("คำนวณตามสูตร: `(Gross Margin - Expenses) + Net Interest`")
    
    # Data Preparation
    data = [
        ("
