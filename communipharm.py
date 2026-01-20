import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(page_title="Communi-Pharm V21 (True Original)", layout="wide")

# CSS Styling (Clean Interface)
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .status-draft { color: #f39c12; font-weight: bold; }
    .status-ready { color: #27ae60; font-weight: bold; }
    .accounting-alert { background-color: #ffebee; border-left: 5px solid #ef5350; padding: 10px; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# --- Constants from Manual/ReadMe ---
WEEKS_PER_PERIOD = 13
BASE_COST_RX = 11.23
CONST_FEE = 2.90
BENEFIT_RATE_LIFE = 0.05   # 5% (ReadMe)
BENEFIT_RATE_HEALTH = 0.15 # 15% (ReadMe)
INVESTMENT_RETURN = 0.015  # 1.5% per period

INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0=No, 1=Yes)", "5. Pt. Records (0=No, 1=Yes)", "6. Credit (0=No, 1=Yes)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($)",
    "19. # Clerks", "20. Clerk Wage ($)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0=No, 1=Yes)",
    "34. Ben: Health (0=No, 1=Yes)", "35. 3rd Party (0=No, 1=Yes)", "36. HMO Bid ($)"
]

REPORT_COLUMNS = [
    "Net Profit", "TOT SALES", "Cash", "ROI", 
    "Rx SALES", "OTH SALES", "Rx Mkt Sh", "OTC Mkt Sh",
    "Avg Rx Pr", "Store Hrs", "Net Worth", "Current", 
    "Turnover", "G Margin", "Debt/NW", "Emerg Loan"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# Rent Rates based on Location (Manual Page 13:25)
LOC_CONFIG = {
    1: {"name": "Medical Center", "rent": 0.045},
    2: {"name": "Neighborhood", "rent": 0.030},
    3: {"name": "Shopping Center", "rent": 0.025}
}

# Market Share Weights (Consumer Behavior)
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
            'notes_payable': 0.0, 'long_term_debt': 100000.0,
            'retained_earnings': 138000.0
        }
        st.session_state.players[team_id] = {
            'id': team_id,
            'shop_name': f"Store {i}",
            'location_code': (i % 3) + 1,
            'status': 'Pending',
            'period': 1,
            'inputs': get_starting_inputs(),
            'financials': financials,
            'prev_stats': { 'avg_price': 15.00, 'mkt_share': 100.0/num_teams },
            'history': [] 
        }
    st.session_state.game_state = "CONFIG_P1"

# ==========================================
# 3. LOGIC ENGINE (V21: Verified Original Logic)
# ==========================================
def calculate_results(store_list):
    # --- 1. Ranking & Market Share ---
    loc_code = store_list[0]['location_code']
    w = MARKET_WEIGHTS[loc_code]
    # Adjusted Market Sizes to match PDF outputs ratio
    market_size_usd = 300000 if loc_code == 1 else 1200000 
    if loc_code == 3: market_size_usd = 900000

    comp_data = []
    for p in store_list:
        inp = p['inputs']
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] + CONST_FEE
        service_score = inp[3] + inp[4] + inp[5]
        
        # Scoring Formula (Inverse Price, Direct Service/Promo)
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
        
        # Wages + Benefits (ReadMe Update)
        wage_hourly = (inp[16]*inp[17]) + (inp[18]*inp[19])
        wages_base = wage_hourly * inp[6] * WEEKS_PER_PERIOD
        ben_cost = 0
        if inp[32] == 1: ben_cost += wages_base * BENEFIT_RATE_LIFE    
        if inp[33] == 1: ben_cost += wages_base * BENEFIT_RATE_HEALTH  
        wages_total = wages_base + ben_cost 
        
        # Rent (Manual: % of Sales)
        rent_exp = total_sales * LOC_CONFIG[loc_code]['rent']
        
        fixed_exp = inp[21] + inp[24] + 3000 + inp[7]
        depreciation = fin['fixed_assets'] * 0.02
        bad_debt = inp[29]
        
        # Investment Income
        investment_income = fin['investments'] * INVESTMENT_RETURN 
        new_invest = inp[9]; withdraw = inp[11]
        fin['investments'] += (new_invest - withdraw)
        
        interest_expense = (fin['long_term_debt'] * 0.025)

        # Inventory Returns (ReadMe: Cap at 25%)
        max_rx_ret = fin['inventory_rx'] * 0.25
        max_otc_ret = fin['inventory_otc'] * 0.25
        actual_rx_ret = min(inp[26], max_rx_ret)
        actual_otc_ret = min(inp[27], max_otc_ret)
        
        # Inventory Update (Accrual)
        purchases = inp[14] + inp[15]
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] - actual_rx_ret) - cost_rx
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] - actual_otc_ret) - cost_otc
        
        # Cash Flow Logic (Critical Accounting)
        cash_begin = fin['cash']
        cash_in = (total_sales * 0.90) + investment_income + actual_rx_ret + actual_otc_ret + withdraw
        
        payment_on_ap = inp[28]; debt_payment = inp[30]
        cash_out_ops = wages_total + rent_exp + fixed_exp + interest_expense
        cash_out = cash_out_ops + payment_on_ap + new_invest + debt_payment
        
        preliminary_cash = cash_begin + cash_in - cash_out
        
        # Emergency Loan (Logic from Manual/PDF)
        emergency_loan = 0
        if preliminary_cash < 0:
            emergency_loan = abs(preliminary_cash) + 2000
            interest_expense += (emergency_loan * 0.20) # Penalty Interest
            preliminary_cash += emergency_loan
            
        # The "999999" Bug (User specified)
        if payment_on_ap > 200000: interest_expense += 29000000 
        
        total_opex = wages_total + rent_exp + fixed_exp + depreciation + bad_debt + interest_expense
        net_profit = gross_margin - total_opex + investment_income
        
        # Update Balances
        fin['cash'] = preliminary_cash
        fin['acct_receivable'] = fin['acct_receivable'] + (total_sales * 0.10) - bad_debt
        fin['acct_payable'] = fin['acct_payable'] + purchases - payment_on_ap
        fin['notes_payable'] += emergency_loan
        fin['retained_earnings'] += net_profit
        fin['long_term_debt'] -= debt_payment
        
        # Ratios
        nw = fin['retained_earnings']
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        p['history'].append({
            "Period": st.session_state.global_period,
            "Net Profit": net_profit, "Sales": total_sales, "Cash": fin['cash'], 
            "Emerg Loan": emergency_loan, 
            "ROI": (net_profit/nw*100) if nw else 0,
            "Current Ratio": curr_assets/curr_liab if curr_liab else 0,
            "details": {"ben_cost": ben_cost, "pay_ap": payment_on_ap, "purchases": purchases}
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
# 4. USER INTERFACE
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V21")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()
    st.markdown("---")
    role = st.selectbox("Select Role", ["Student", "Instructor"])

# --- INSTRUCTOR VIEW ---
if role == "Instructor":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("👨‍🏫 Instructor Dashboard")
        
        if st.session_state.game_state == "SETUP":
            st.info("Step 1: Create Teams")
            n = st.number_input("Number of Teams", 1, 10, 3)
            if st.button("Create Teams"): initialize_teams(n); st.rerun()
                
        elif st.session_state.game_state == "CONFIG_P1":
            st.warning("Step 2: Configure Scenario (Period 1 Inputs)")
            tabs = st.tabs(list(st.session_state.players.keys()))
            for i, (tid, p) in enumerate(st.session_state.players.items()):
                with tabs[i]:
                    st.write(f"**Editing {p['shop_name']}**")
                    c1, c2, c3 = st.columns(3)
                    p['inputs'][0] = c1.number_input(f"Markup %", value=p['inputs'][0], key=f"m{i}")
                    p['inputs'][7] = c2.number_input(f"Promo $", value=p['inputs'][7], key=f"p{i}")
                    p['inputs'][28] = c3.number_input(f"Pay A/P $", value=p['inputs'][28], key=f"ap{i}")
            
            st.markdown("---")
            if st.button("🏁 Start Game (Run P1)", type="primary"):
                run_period_step()
                st.session_state.game_state = "ACTIVE"
                st.success("Game Started!")
                st.rerun()
                
        else: # ACTIVE
            st.subheader(f"Status: Period {st.session_state.global_period}")
            status_data = []
            ready = 0
            for tid, p in st.session_state.players.items():
                stat = "⚪ Pending"
                if p['status'] == "Draft": stat = "🟡 Draft"
                if p['status'] == "Submitted": stat = "✅ Submitted"; ready += 1
                status_data.append({"Store": p['shop_name'], "Status": stat})
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)
            
            if st.button(f"🚀 Run Period {st.session_state.global_period}"):
                run_period_step(); st.success("Processed!"); st.rerun()

# --- STUDENT VIEW ---
if role == "Student":
    if st.session_state.game_state != "ACTIVE":
        st.warning("Instructor ยังไม่ได้เริ่มเกม (Waiting for Start)")
    else:
        t_ids = list(st.session_state.players.keys())
        sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
        p = st.session_state.players[sel_id]
        
        st.title(f"🏥 {p['shop_name']}")
        st.caption(f"Period: {st.session_state.global_period} | Location: {LOC_MAP[p['location_code']]}")
        
        tab1, tab2 = st.tabs([f"📝 Decisions (P{st.session_state.global_period})", f"📊 Report (P{st.session_state.global_period-1})"])
        
        with tab1:
            if p['status'] == 'Submitted':
                st.success("✅ Submitted! Waiting for results.")
                if st.button("Unsubmit"): p['status'] = 'Draft'; st.rerun()
            else:
                df_inp = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
                edited = st.data_editor(df_inp, column_config={"Value": st.column_config.NumberColumn(min_value=0.0)}, hide_index=True, height=600)
                c1, c2 = st.columns(2)
                if c1.button("💾 Save Draft"): p['inputs'] = edited['Value'].tolist(); p['status'] = 'Draft'; st.toast("Saved!"); st.rerun()
                if c2.button("✅ Submit", type="primary"): p['inputs'] = edited['Value'].tolist(); p['status'] = 'Submitted'; st.rerun()

        with tab2:
            if p['history']:
                last = p['history'][-1]
                st.markdown(f"### Results for Period {last['Period']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m2.metric("Sales", f"${last['Sales']:,.0f}")
                m3.metric("Cash", f"${last['Cash']:,.0f}")
                m4.metric("Emerg Loan", f"${last['Emerg Loan']:,.0f}", delta_color="inverse")
                
                with st.expander("💡 Accounting Analysis"):
                    st.markdown(f"""
                    * **Inventory Purchases:** ${last['details']['purchases']:,.0f} (Added to A/P)
                    * **Payment on A/P (Input 29):** ${last['details']['pay_ap']:,.0f} (Reduced Cash)
                    * **Benefits Paid:** ${last['details']['ben_cost']:,.0f} (Included in Expenses)
                    """)
                    if last['Emerg Loan'] > 0:
                        st.markdown('<div class="accounting-alert">⚠️ <b>Cash Shortage:</b> Emergency Loan triggered (20% Interest). Check your A/P Payments.</div>', unsafe_allow_html=True)
                
                st.dataframe(pd.DataFrame([last]).style.format("{:,.2f}"), use_container_width=True)
            else: st.info("No data available.")
