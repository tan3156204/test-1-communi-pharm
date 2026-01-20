import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V21 (ReadMe Patch)", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .status-draft { color: #f39c12; font-weight: bold; }
    .status-ready { color: #27ae60; font-weight: bold; }
    .patch-note { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border-left: 5px solid #4caf50; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"
WEEKS_PER_PERIOD = 13
BASE_COST_RX = 11.23
CONST_FEE = 2.90

# Rate Constants (Assumptions based on typical sims)
BENEFIT_RATE_LIFE = 0.05   # 5% ของค่าจ้าง
BENEFIT_RATE_HEALTH = 0.15 # 15% ของค่าจ้าง
INVESTMENT_RETURN = 0.015  # 1.5% ต่อไตรมาส

LOC_CONFIG = {
    0: {"name": "Not Selected", "rent_rate": 0.0},
    1: {"name": "Medical Center", "rent_rate": 0.045, "desc": "ค่าเช่า 4.5%"},
    2: {"name": "Neighborhood", "rent_rate": 0.030, "desc": "ค่าเช่า 3.0%"},
    3: {"name": "Shopping Center", "rent_rate": 0.025, "desc": "ค่าเช่า 2.5%"}
}

INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0/1)", "5. Pt. Records (0/1)", "6. Credit (0/1)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($/hr)",
    "19. # Clerks", "20. Clerk Wage ($/hr)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

MARKET_WEIGHTS = {
    1: {'price': 10, 'fee': 30, 'promo': 10, 'hours': 20, 'service': 30},
    2: {'price': 20, 'fee': 20, 'promo': 20, 'hours': 20, 'service': 20},
    3: {'price': 50, 'fee': 10, 'promo': 20, 'hours': 10, 'service': 10}
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP"
    st.session_state.global_period = 1
    st.session_state.players = {}

def get_starting_inputs():
    return [
        50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 
        0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 
        1.0, 25.0, 1.0, 10.0, 1500.0, 30.0, 40.0, 60.0, 
        0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 
        0.0, 0.0, 0.0, 0.0
    ]

def initialize_teams(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0, 'retained_earnings': 138000.0
        }
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': (i % 3) + 1,
            'status': 'Pending', 'period': 1, 'inputs': get_starting_inputs(),
            'financials': financials, 'prev_stats': { 'avg_price': 15.00, 'mkt_share': 100.0/num_teams },
            'history': [] 
        }
    st.session_state.game_state = "CONFIG_P1"

# ==========================================
# 3. LOGIC ENGINE (V21 UPDATED)
# ==========================================
def calculate_results(store_list):
    # --- 1. Ranking & Market Share ---
    loc_code = store_list[0]['location_code']
    w = MARKET_WEIGHTS[loc_code]
    market_size_usd = 300000 if loc_code == 1 else 1200000 
    if loc_code == 3: market_size_usd = 900000

    comp_data = []
    for p in store_list:
        inp = p['inputs']
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] + CONST_FEE
        service_score = inp[3] + inp[4] + inp[5]
        score = (1000/price)*w['price'] + (10/(inp[1]+1))*w['fee'] + (inp[7]/1000)*w['promo'] + (inp[6]/50)*w['hours'] + service_score*w['service']
        comp_data.append({'p': p, 'score': score})
    
    total_score = sum([x['score'] for x in comp_data])
    
    # --- 2. Financial Calculation ---
    for item in comp_data:
        p = item['p']
        inp = p['inputs']
        fin = p['financials']
        share = item['score'] / total_score if total_score > 0 else 0
        
        # Sales & COGS
        total_sales = share * market_size_usd
        rx_sales = total_sales * 0.70; otc_sales = total_sales * 0.30
        cost_rx = rx_sales / (1 + (inp[0]/100)); cost_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cost_rx + cost_otc
        gross_margin = total_sales - total_cogs
        
        # Expenses (Updated with Benefits)
        wage_hourly = (inp[16]*inp[17]) + (inp[18]*inp[19])
        wages_base = wage_hourly * inp[6] * WEEKS_PER_PERIOD
        
        # [PATCH] Benefit Calculation
        ben_cost = 0
        if inp[32] == 1: ben_cost += wages_base * BENEFIT_RATE_LIFE    # Life Ins.
        if inp[33] == 1: ben_cost += wages_base * BENEFIT_RATE_HEALTH  # Health Ins.
        
        wages_total = wages_base + ben_cost # รวมค่าจ้างและสวัสดิการ
        
        rent_exp = total_sales * LOC_CONFIG[loc_code]['rent_rate']
        fixed_exp = inp[21] + inp[24] + 3000 + inp[7]
        depreciation = fin['fixed_assets'] * 0.02
        bad_debt = inp[29]
        
        total_opex = wages_total + rent_exp + fixed_exp + depreciation + bad_debt
        operating_profit = gross_margin - total_opex
        
        # Interest & Investment
        investment_income = fin['investments'] * INVESTMENT_RETURN # คิดจากยอดสะสม
        # Handle New Investment/Withdrawal
        new_invest = inp[9]  # Input 10
        withdraw = inp[11]   # Input 12
        fin['investments'] += (new_invest - withdraw)
        
        interest_expense = (fin['long_term_debt'] * 0.025)

        # [PATCH] Inventory Return Limit (25% Rule)
        # Input 27 (Rx Return) index 26, Input 28 (Oth Return) index 27
        max_rx_ret = fin['inventory_rx'] * 0.25
        max_otc_ret = fin['inventory_otc'] * 0.25
        
        actual_rx_ret = min(inp[26], max_rx_ret)
        actual_otc_ret = min(inp[27], max_otc_ret)
        
        # Inventory Updates
        purchases = inp[14] + inp[15]
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] - actual_rx_ret) - cost_rx
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] - actual_otc_ret) - cost_otc
        
        # Cash Flow
        cash_begin = fin['cash']
        cash_collections = total_sales * 0.90
        cash_in = cash_collections + investment_income + actual_rx_ret + actual_otc_ret # ได้เงินคืนจากการ Return
        
        payment_on_ap = inp[28]
        cash_out = wages_total + rent_exp + fixed_exp + interest_expense + payment_on_ap + new_invest
        cash_in += withdraw # ถอนเงินลงทุนได้เงินสด
        
        preliminary_cash = cash_begin + cash_in - cash_out
        
        # Emergency Loan
        emergency_loan = 0; penalty = 0
        if preliminary_cash < 0:
            emergency_loan = abs(preliminary_cash) + 2000
            penalty = emergency_loan * 0.20
            preliminary_cash += emergency_loan
            interest_expense += penalty
            
        if payment_on_ap > 200000: interest_expense += 29000000 # The Bug
        
        net_profit = operating_profit + investment_income - interest_expense
        
        # Update Balances
        fin['cash'] = preliminary_cash
        fin['acct_receivable'] = fin['acct_receivable'] + (total_sales * 0.10) - bad_debt
        fin['acct_payable'] = fin['acct_payable'] + purchases - payment_on_ap
        fin['notes_payable'] += emergency_loan
        fin['retained_earnings'] += net_profit
        
        # Record
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        p['history'].append({
            "Period": st.session_state.global_period,
            "Net Profit": net_profit, "Sales": total_sales, "Cash": fin['cash'], 
            "Emerg Loan": emergency_loan, "Current Ratio": curr_assets/curr_liab if curr_liab else 0,
            "details": {"ben_cost": ben_cost, "returns": actual_rx_ret+actual_otc_ret}
        })
        p['status'] = 'Pending'

def run_period_step():
    stores_by_loc = {1: [], 2: [], 3: []}
    for p in st.session_state.players.values():
        if p['location_code'] != 0: stores_by_loc[p['location_code']].append(p)
    for loc in stores_by_loc:
        if stores_by_loc[loc]: calculate_results(stores_by_loc[loc])
    st.session_state.global_period += 1

# ==========================================
# 4. SIDEBAR & INSTRUCTOR
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V21")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()
    role = st.selectbox("Role", ["Student", "Instructor"])

if role == "Instructor":
    if st.sidebar.text_input("Password", type="password") == ADMIN_PASSWORD:
        st.header("👨‍🏫 Instructor (Patch V21)")
        if st.session_state.game_state == "SETUP":
            if st.button("Create Teams"): initialize_teams(st.number_input("Teams",1,10,3)); st.rerun()
        elif st.session_state.game_state == "CONFIG_P1":
            st.warning("Configure Period 1 Inputs")
            tabs = st.tabs(list(st.session_state.players.keys()))
            for i, (tid, p) in enumerate(st.session_state.players.items()):
                with tabs[i]:
                    c1, c2, c3 = st.columns(3)
                    p['inputs'][0] = c1.number_input(f"Markup", value=p['inputs'][0], key=f"m{i}")
                    p['inputs'][7] = c2.number_input(f"Promo", value=p['inputs'][7], key=f"p{i}")
                    p['inputs'][28] = c3.number_input(f"Pay AP", value=p['inputs'][28], key=f"ap{i}")
            if st.button("🏁 Start Game"): run_period_step(); st.session_state.game_state="ACTIVE"; st.rerun()
        else:
            st.success(f"Period {st.session_state.global_period}")
            if st.button("🚀 Run Next Period"): run_period_step(); st.rerun()

# ==========================================
# 5. STUDENT VIEW
# ==========================================
if role == "Student":
    if st.session_state.game_state == "ACTIVE":
        t_ids = list(st.session_state.players.keys())
        sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
        p = st.session_state.players[sel_id]
        
        tab1, tab2 = st.tabs(["📝 Decisions", "📊 Report"])
        
        with tab1:
            if p['status'] == 'Submitted': st.success("Submitted!"); st.button("Unsubmit", on_click=lambda: p.update({'status': 'Draft'}))
            else:
                df_inp = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
                edited = st.data_editor(df_inp, column_config={"Value": st.column_config.NumberColumn(min_value=0.0)}, hide_index=True, height=600)
                if st.button("✅ Submit"): p['inputs'] = edited['Value'].tolist(); p['status']='Submitted'; st.rerun()

        with tab2:
            if p['history']:
                last = p['history'][-1]
                st.markdown(f"### Period {last['Period']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m2.metric("Cash", f"${last['Cash']:,.0f}")
                m3.metric("Benefits Paid", f"${last['details']['ben_cost']:,.0f}")
                m4.metric("Inv Returns", f"${last['details']['returns']:,.0f}")
                
                if last['details']['ben_cost'] > 0:
                    st.markdown('<div class="patch-note">💡 <b>New Feature:</b> ค่าใช้จ่ายสวัสดิการ (Employee Benefits) ถูกคำนวณรวมในค่าจ้างแล้ว</div>', unsafe_allow_html=True)
                
                st.dataframe(pd.DataFrame([last]).style.format("{:,.2f}"), use_container_width=True)
    else: st.warning("Waiting for Instructor...")
