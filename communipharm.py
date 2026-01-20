import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION (จากคู่มือ)
# ==========================================
st.set_page_config(page_title="Communi-Pharm V20 (Instructor's Guide)", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .status-draft { color: #f39c12; font-weight: bold; }
    .status-ready { color: #27ae60; font-weight: bold; }
    .accounting-alert { background-color: #fce4ec; padding: 10px; border-radius: 5px; border-left: 5px solid #e91e63; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"
WEEKS_PER_PERIOD = 13
BASE_COST_RX = 11.23
CONST_FEE = 2.90

# Location Settings (หน้า 13:25 ในคู่มือ)
LOC_CONFIG = {
    0: {"name": "Not Selected", "rent_rate": 0.0},
    1: {"name": "Medical Center", "rent_rate": 0.045, "desc": "ค่าเช่า 4.5% (เน้น Professional Fee)"},
    2: {"name": "Neighborhood", "rent_rate": 0.030, "desc": "ค่าเช่า 3.0% (ชุมชน)"},
    3: {"name": "Shopping Center", "rent_rate": 0.025, "desc": "ค่าเช่า 2.5% (เน้น Volume/Price)"}
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
    "28. Oth Return ($)", "29. Pay A/P ($) [จ่ายหนี้]", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

# Weights (Market Share Logic)
# Medical Center: ไม่สนราคามาก เน้น Fee(2) และ Hours(7)
# Shopping Center: สนราคา(1) และ Promo(8) มากที่สุด
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
    # Default inputs based on typical P1 values
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
            'cash': 15000.0, 
            'investments': 2000.0, 
            'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 
            'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 
            'acct_payable': 30000.0,   # หนี้สินเจ้าหนี้การค้าเริ่มต้น
            'notes_payable': 0.0,      # เงินกู้ระยะสั้น/ฉุกเฉิน
            'long_term_debt': 100000.0,
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
# 3. LOGIC ENGINE (ACCOUNTING CORE)
# ==========================================
def calculate_results(store_list):
    # 1. Ranking & Market Share Calculation
    # -------------------------------------
    loc_code = store_list[0]['location_code']
    w = MARKET_WEIGHTS[loc_code]
    market_size_usd = 300000 if loc_code == 1 else 1200000 # Base Market Size
    if loc_code == 3: market_size_usd = 900000

    comp_data = []
    for p in store_list:
        inp = p['inputs']
        # Price = Base Cost + Markup + Fee
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] + CONST_FEE
        
        # Service Score (Delivery + Records + Credit)
        service_score = inp[3] + inp[4] + inp[5]
        
        score = 0
        # ยิ่งราคาน้อย ยิ่งดี (Inverse)
        score += (1000 / price) * w['price']
        # ยิ่ง Fee น้อย ยิ่งดี
        score += (10 / (inp[1]+1)) * w['fee']
        # Promo & Hours & Service ยิ่งมาก ยิ่งดี
        score += (inp[7] / 1000) * w['promo']
        score += (inp[6] / 50) * w['hours']
        score += service_score * w['service']
        
        comp_data.append({'p': p, 'score': score, 'price': price})
    
    total_score = sum([x['score'] for x in comp_data])
    
    # 2. Financial Calculation (Per Store)
    # ------------------------------------
    for item in comp_data:
        p = item['p']
        inp = p['inputs']
        fin = p['financials']
        
        # Share
        share = item['score'] / total_score if total_score > 0 else 0
        
        # --- Income Statement Logic ---
        total_sales = share * market_size_usd
        rx_sales = total_sales * 0.70
        otc_sales = total_sales * 0.30
        
        # COGS (Cost of Goods Sold)
        cost_rx = rx_sales / (1 + (inp[0]/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cost_rx + cost_otc
        
        gross_margin = total_sales - total_cogs
        
        # Operating Expenses
        # Wages: (Pharm * Rate + Clerk * Rate) * Hours * 13 Weeks
        wage_hourly = (inp[16]*inp[17]) + (inp[18]*inp[19])
        wages_total = wage_hourly * inp[6] * WEEKS_PER_PERIOD
        
        # Rent: % of Sales (ตามคู่มือ)
        rent_rate = LOC_CONFIG[loc_code]['rent_rate']
        rent_exp = total_sales * rent_rate
        
        fixed_exp = inp[21] + inp[24] + 3000 + inp[7] # Mgr + Mortgage + Util + Promo
        depreciation = fin['fixed_assets'] * 0.02 # Straight line approx
        bad_debt = inp[29] # Input 30 in list = index 29 (Debt Written)
        
        total_opex = wages_total + rent_exp + fixed_exp + depreciation + bad_debt
        operating_profit = gross_margin - total_opex
        
        # Interest & Other
        investment_income = inp[9] * 0.015 # 1.5% return
        interest_expense = (fin['long_term_debt'] * 0.025) # Normal Loan Interest
        
        # --- Cash Flow & Balance Sheet Logic (CRITICAL) ---
        cash_begin = fin['cash']
        
        # Cash Inflows
        cash_collections = total_sales * 0.90 # เก็บเงินได้ 90% (อีก 10% เป็น A/R)
        cash_in = cash_collections + investment_income
        
        # Cash Outflows
        # *Note: Purchases (Input 15,16) do NOT reduce cash immediately. They go to A/P.
        # Cash only reduces when Paying A/P (Input 29).
        purchases = inp[14] + inp[15]
        payment_on_ap = inp[28] # จ่ายเจ้าหนี้
        
        cash_expenses = wages_total + rent_exp + fixed_exp + interest_expense
        cash_out = cash_expenses + payment_on_ap 
        
        preliminary_cash = cash_begin + cash_in - cash_out
        
        # Emergency Loan Check (Auto-Loan if Cash < 0)
        emergency_loan = 0
        penalty_interest = 0
        
        if preliminary_cash < 0:
            shortage = abs(preliminary_cash)
            emergency_loan = shortage + 2000 # กู้เผื่อ
            penalty_interest = emergency_loan * 0.20 # 20% Penalty Interest
            preliminary_cash += emergency_loan
            
            # Add penalty to expenses
            interest_expense += penalty_interest
            
        # The "999999" Bug/Feature Simulation
        if payment_on_ap > 200000: 
            penalty_interest += 29000000
            interest_expense += 29000000
            
        net_profit = operating_profit + investment_income - interest_expense
        
        # Update Balance Sheet Accounts
        fin['cash'] = preliminary_cash
        
        # Inventory: Begin + Purch - COGS
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - cost_rx
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - cost_otc
        
        # A/R: Begin + Credit Sales (10%) - Collections (simplified) - Bad Debt
        fin['acct_receivable'] = fin['acct_receivable'] + (total_sales * 0.10) - bad_debt
        
        # A/P: Begin + Purchases - Payments
        fin['acct_payable'] = fin['acct_payable'] + purchases - payment_on_ap
        
        fin['notes_payable'] += emergency_loan
        fin['retained_earnings'] += net_profit
        
        # Ratios
        nw = fin['retained_earnings']
        curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        # Record History
        p['history'].append({
            "Period": st.session_state.global_period,
            "Net Profit": net_profit, 
            "Sales": total_sales, 
            "Cash": fin['cash'], 
            "AP Balance": fin['acct_payable'],
            "Emergency Loan": emergency_loan,
            "ROI": (net_profit/nw*100) if nw else 0,
            "Current Ratio": curr_assets/curr_liab if curr_liab else 0,
            "details": {
                "purchases": purchases,
                "pay_ap": payment_on_ap,
                "rent": rent_exp,
                "cogs": total_cogs
            }
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
# 4. SIDEBAR & RESET
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V20")
    if st.button("🔄 HARD RESET (เริ่มใหม่)", type="primary"):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    role = st.selectbox("เลือกบทบาท (Role)", ["Student", "Instructor"])

# ==========================================
# 5. INSTRUCTOR VIEW
# ==========================================
if role == "Instructor":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("👨‍🏫 Instructor Dashboard")
        
        if st.session_state.game_state == "SETUP":
            st.info("Step 1: Create Teams")
            n = st.number_input("Number of Teams", 1, 10, 3)
            if st.button("Create Teams"):
                initialize_teams(n)
                st.rerun()
                
        elif st.session_state.game_state == "CONFIG_P1":
            st.subheader("Step 2: Configure Scenario (Period 1)")
            st.markdown("""
            **คำแนะนำสำหรับการสร้างโจทย์:**
            * อยากให้ร้านไหนขาดสภาพคล่อง: ใส่ **Pay A/P (Input 29)** เยอะๆ
            * อยากให้ร้านไหนกำไรน้อย: ใส่ **Promo (Input 8)** เยอะๆ แต่ **Markup (Input 1)** ต่ำ
            """)
            
            tabs = st.tabs(list(st.session_state.players.keys()))
            for i, (tid, p) in enumerate(st.session_state.players.items()):
                with tabs[i]:
                    st.write(f"**{p['shop_name']}** ({LOC_CONFIG[p['location_code']]['name']})")
                    c1, c2, c3 = st.columns(3)
                    p['inputs'][0] = c1.number_input(f"Markup %", value=p['inputs'][0], key=f"mk_{tid}")
                    p['inputs'][7] = c2.number_input(f"Promo $", value=p['inputs'][7], key=f"pr_{tid}")
                    p['inputs'][28] = c3.number_input(f"Pay A/P $", value=p['inputs'][28], key=f"ap_{tid}")
            
            st.markdown("---")
            if st.button("🏁 Start Game (Run P1)", type="primary"):
                run_period_step()
                st.session_state.game_state = "ACTIVE"
                st.success("Game Started!")
                st.rerun()
                
        else: # ACTIVE
            st.subheader(f"Status: Period {st.session_state.global_period}")
            
            # Status Table
            status_data = []
            ready_count = 0
            for tid, p in st.session_state.players.items():
                stat = "⚪ Pending"
                if p['status'] == "Draft": stat = "🟡 Draft"
                if p['status'] == "Submitted": stat = "✅ Submitted"; ready_count += 1
                status_data.append({"Store": p['shop_name'], "Status": stat})
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)
            
            if st.button(f"🚀 Run Period {st.session_state.global_period}"):
                run_period_step()
                st.success("Processed!")
                st.rerun()

# ==========================================
# 6. STUDENT VIEW
# ==========================================
if role == "Student":
    if st.session_state.game_state != "ACTIVE":
        st.warning("Instructor ยังไม่ได้เริ่มเกม")
    else:
        # Team Selection
        t_ids = list(st.session_state.players.keys())
        sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
        p = st.session_state.players[sel_id]
        
        st.title(f"🏥 {p['shop_name']}")
        
        tab1, tab2 = st.tabs([f"📝 Decisions (P{st.session_state.global_period})", f"📊 Report (P{st.session_state.global_period-1})"])
        
        with tab1:
            if p['status'] == 'Submitted':
                st.success("✅ ส่งข้อมูลแล้ว รอผลลัพธ์")
                if st.button("Unsubmit"):
                    p['status'] = 'Draft'
                    st.rerun()
            else:
                st.info("กรอกข้อมูลแล้วกด Save Draft หรือ Submit")
                
                # Editor
                df_inp = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
                edited = st.data_editor(
                    df_inp, 
                    column_config={"Value": st.column_config.NumberColumn(min_value=0.0)},
                    hide_index=True, use_container_width=True, height=600, key=f"ed_{sel_id}_{st.session_state.global_period}"
                )
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Save Draft"):
                    p['inputs'] = edited['Value'].tolist()
                    p['status'] = 'Draft'
                    st.toast("Saved!")
                    st.rerun()
                if c2.button("✅ Submit", type="primary"):
                    p['inputs'] = edited['Value'].tolist()
                    p['status'] = 'Submitted'
                    st.rerun()
        
        with tab2:
            if p['history']:
                last = p['history'][-1]
                st.markdown(f"### ผลประกอบการ Period {last['Period']}")
                
                # Highlight Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m2.metric("Cash Balance", f"${last['Cash']:,.0f}")
                m3.metric("A/P Balance", f"${last['AP Balance']:,.0f}")
                m4.metric("Emerg Loan", f"${last['Emergency Loan']:,.0f}", delta_color="inverse")
                
                # Accounting Insight (ตามคู่มือ)
                with st.expander("💡 Accounting Analysis (Purchases vs Expenses)"):
                    st.markdown(f"""
                    * **Purchases (Input 15+16):** ${last['details']['purchases']:,.2f} (เพิ่มหนี้ A/P, ไม่ลดเงินสด)
                    * **Pay A/P (Input 29):** ${last['details']['pay_ap']:,.2f} (ลดเงินสดจริง)
                    * **COGS (Expense):** ${last['details']['cogs']:,.2f} (หักในงบกำไรขาดทุน)
                    """)
                    if last['Emergency Loan'] > 0:
                        st.markdown('<div class="accounting-alert">⚠️ <b>Warning:</b> เงินสดติดลบ! ระบบกู้เงินฉุกเฉินอัตโนมัติ (ดอกเบี้ย 20%) สาเหตุอาจเกิดจากจ่ายหนี้ (Input 29) มากเกินไป</div>', unsafe_allow_html=True)
                
                st.dataframe(pd.DataFrame([last]).style.format("{:,.2f}"), use_container_width=True)
            else:
                st.info("No data yet.")
