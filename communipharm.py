import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Exact Terms)", layout="wide")

# รหัสผ่านอาจารย์
ADMIN_PASSWORD = "admin1234"

# ตัวเลือกทำเล
LOCATIONS = ["Med Center", "Neighborhood", "Shopping"]

# Instructor Weights (ปรับชื่อตัวแปรให้ตรงกับ DOSBox)
# ค่า Default สมมติขึ้นมาเพื่อให้แต่ละทำเลมีความแตกต่างกัน
DEFAULT_WEIGHTS = {
    "Med Center": {
        "past_rx_price": 4, "present_rx_price": 5, "promotion_index": 3,
        "hours": 7, "delivery": 9, "records": 9, "credit": 4,
        "inventory": 8, "prev_market_share": 5, "rx_per_hour": 8,
        "base_traffic": 1500
    },
    "Neighborhood": {
        "past_rx_price": 5, "present_rx_price": 6, "promotion_index": 5,
        "hours": 5, "delivery": 6, "records": 5, "credit": 6,
        "inventory": 6, "prev_market_share": 6, "rx_per_hour": 5,
        "base_traffic": 1200
    },
    "Shopping": {
        "past_rx_price": 8, "present_rx_price": 10, "promotion_index": 9,
        "hours": 4, "delivery": 2, "records": 2, "credit": 3,
        "inventory": 5, "prev_market_share": 4, "rx_per_hour": 7,
        "base_traffic": 2200
    }
}

# ==========================================
# 2. State Initialization
# ==========================================
if 'location_weights' not in st.session_state:
    st.session_state.location_weights = DEFAULT_WEIGHTS.copy()

if 'players' not in st.session_state:
    st.session_state.players = {}
    # สร้างทีมรอไว้ (Team 1 - Team 7)
    for i in range(1, 8):
        team_name = f"Team {i}"
        st.session_state.players[team_name] = {
            'location': None,
            'period': 1,
            'financials': {
                'cash': 40000.0,
                'accounts_payable': 0.0,
                'long_term_debt': 0.0,
                'inventory_rx': 20000.0,
                'inventory_otc': 15000.0
            },
            'history': []
        }

# ==========================================
# 3. Logic Engine
# ==========================================
def run_period(team_name, d):
    player = st.session_state.players[team_name]
    loc_type = player['location']
    # ดึงค่า Weights ที่อาจารย์ตั้งค่าไว้
    w = st.session_state.location_weights[loc_type]
    fin = player['financials']
    
    # --- 1. Demand Calculation (Using New Weights) ---
    # Price Factor: รวมผลของ Past และ Present (ยิ่ง Weight เยอะ ยิ่ง Sensitive ต่อราคา)
    price_sensitivity_total = (w['past_rx_price'] * 0.4) + (w['present_rx_price'] * 0.6)
    price_score = 1.0
    # ถ้าราคาแพงกว่ามาตรฐาน จะโดนหักคะแนนตามความ Sensitive
    if d['rx_fee'] > 5: price_score -= (price_sensitivity_total * 0.01)
    if d['rx_markup'] > 45: price_score -= (price_sensitivity_total * 0.01)
    
    # Service Factors
    service_score = 1.0
    if d['delivery'] == 1: service_score += w['delivery'] * 0.02
    if d['records'] == 1: service_score += w['records'] * 0.02
    if d['credit'] == 1: service_score += w['credit'] * 0.02
    
    # Operations Factors
    # Hours
    hours_bonus = (d['hours_open'] - 40) * (w['hours'] * 0.003)
    # Speed (Rx Per Hour Weight) - จำลองว่าถ้าจ้างคนเยอะ บริการเร็ว ลูกค้าชอบ
    speed_bonus = 0
    if d['n_pharm'] >= 1: speed_bonus = w['rx_per_hour'] * 0.01
    
    # Marketing (Promotion Index)
    promo_effect = (d['promo_exp'] / 8000) * (w['promotion_index'] * 0.2)
    
    # Inventory Level Weight (ผลกระทบถ้าของขาด หรือมีของพอ)
    # ใน Model ง่ายๆ นี้ ให้โบนัสถ้า Inventory > 10000
    inv_bonus = 0
    if fin['inventory_rx'] > 10000: inv_bonus = w['inventory'] * 0.01

    # Total Multiplier
    multiplier = price_score * service_score * (1 + hours_bonus + speed_bonus + promo_effect + inv_bonus)
    
    # Base Traffic + Momentum (Previous Market Share)
    # Momentum ช่วยพยุงยอดขายเดิมไว้ส่วนหนึ่ง
    momentum = w['prev_market_share'] * 10 
    traffic = (w['base_traffic'] + momentum) * max(0.1, multiplier)
    
    # --- 2. Sales Processing ---
    rx_cust = int(traffic * 0.35)
    otc_cust = int(traffic * 0.65)
    
    rx_cost_base = 10
    rx_price = rx_cost_base * (1 + d['rx_markup']/100) + d['rx_fee']
    rx_revenue = rx_cust * rx_price
    rx_cogs = rx_cust * rx_cost_base
    
    otc_cost_base = 5
    otc_price = otc_cost_base * (1 + d['otc_markup']/100)
    otc_revenue = otc_cust * otc_price
    otc_cogs = otc_cust * otc_cost_base
    
    # --- 3. Expenses ---
    cost_pharm = d['n_pharm'] * d['wage_pharm'] * d['hours_open'] * 4
    cost_clerk = d['n_clerk'] * d['wage_clerk'] * d['hours_open'] * 4
    cost_manager = d['manager_salary']
    
    benefits_cost = 0
    if d['benefit_life'] == 1: benefits_cost += 200
    if d['benefit_health'] == 1: benefits_cost += 500
    
    total_wages = cost_pharm + cost_clerk + cost_manager + benefits_cost
    mortgage = d['mortgage_payment']
    promo = d['promo_exp']
    other_expenses = 1000
    total_expenses = total_wages + mortgage + promo + other_expenses
    
    gross_profit = (rx_revenue + otc_revenue) - (rx_cogs + otc_cogs)
    net_profit = gross_profit - total_expenses
    
    # --- 4. Cash Flow & Balance Sheet Updates ---
    cash_in = rx_revenue + otc_revenue + d['inv_withdrawal']
    cash_out = total_expenses + d['buy_rx'] + d['buy_otc'] + d['inv_project_amt'] + d['debt_payment_long']
    
    payable_payment = d['payment_ap']
    if payable_payment > fin['accounts_payable']:
        payable_payment = fin['accounts_payable']
    
    fin['cash'] = fin['cash'] + cash_in - cash_out - payable_payment
    fin['inventory_rx'] += d['buy_rx'] - rx_cogs
    fin['inventory_otc'] += d['buy_otc'] - otc_cogs
    fin['accounts_payable'] = (fin['accounts_payable'] - payable_payment) + (d['buy_rx'] + d['buy_otc']) * 0.5
    fin['long_term_debt'] -= d['debt_payment_long']
    
    # Record History
    player['history'].append({
        "Period": player['period'],
        "Revenue": rx_revenue + otc_revenue,
        "Net Profit": net_profit,
        "Cash": fin['cash'],
        "Rx Sales (Qty)": rx_cust
    })
    player['period'] += 1

# Helper for Inputs
def make_input(label, key, default, min_v=0.0, max_v=1000000.0, step=1.0):
    return st.number_input(label, min_value=float(min_v), max_value=float(max_v), value=float(default), step=step, key=key)

# ==========================================
# 4. Sidebar & Login Logic
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm")
    role = st.selectbox("Select Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Select Your Team", list(st.session_state.players.keys()))
        if st.button("🔄 Reset Game"):
            st.session_state.clear()
            st.rerun()
            
    elif role == "Instructor":
        pwd = st.text_input("Enter Admin Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)
        if not is_admin and pwd != "":
            st.error("Incorrect Password")

# ==========================================
# 5. Main UI
# ==========================================

# --- INSTRUCTOR VIEW ---
if role == "Instructor":
    if is_admin:
        st.title("👨‍🏫 Instructor Control Panel")
        st.markdown("### ⚙️ Environment Parameters (Weights)")
        st.info("Adjust the weights below to match the 'FILE: RATINGS' screen.")
        
        tabs = st.tabs(LOCATIONS)
        for i, loc in enumerate(LOCATIONS):
            with tabs[i]:
                st.subheader(f"Weights for: {loc}")
                w = st.session_state.location_weights[loc]
                
                with st.form(f"admin_{loc}"):
                    # Base Traffic (Hidden Factor)
                    st.number_input("Base Traffic (Customer Volume)", value=w['base_traffic'], key=f"bt_{loc}")
                    
                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        # Price Factors
                        st.slider("Store's Past Rx Price", 0, 10, w['past_rx_price'], key=f"past_{loc}")
                        st.slider("Store's Present Rx Price", 0, 10, w['present_rx_price'], key=f"pres_{loc}")
                        
                        # Promotion & Hours
                        st.slider("Store's Promotion Index", 0, 10, w['promotion_index'], key=f"promo_{loc}")
                        st.slider("Store's Hours", 0, 10, w['hours'], key=f"hours_{loc}")
                        
                        # Service Offers
                        st.slider("Offers Delivery Service", 0, 10, w['delivery'], key=f"del_{loc}")
                        
                    with c2:
                        # More Service Offers
                        st.slider("Offers Patient Records", 0, 10, w['records'], key=f"rec_{loc}")
                        st.slider("Offers Credit", 0, 10, w['credit'], key=f"cred_{loc}")
                        
                        # Operational Stats
                        st.slider("Store's Inventory Level", 0, 10, w['inventory'], key=f"inv_{loc}")
                        st.slider("Store's Previous Market Share", 0, 10, w['prev_market_share'], key=f"share_{loc}")
                        st.slider("Store's Rx Per Hour", 0, 10, w['rx_per_hour'], key=f"speed_{loc}")

                    if st.form_submit_button(f"💾 Update {loc} Weights"):
                        st.session_state.location_weights[loc]['past_rx_price'] = st.session_state[f"past_{loc}"]
                        st.session_state.location_weights[loc]['present_rx_price'] = st.session_state[f"pres_{loc}"]
                        st.session_state.location_weights[loc]['promotion_index'] = st.session_state[f"promo_{loc}"]
                        st.session_state.location_weights[loc]['hours'] = st.session_state[f"hours_{loc}"]
                        st.session_state.location_weights[loc]['delivery'] = st.session_state[f"del_{loc}"]
                        st.session_state.location_weights[loc]['records'] = st.session_state[f"rec_{loc}"]
                        st.session_state.location_weights[loc]['credit'] = st.session_state[f"cred_{loc}"]
                        st.session_state.location_weights[loc]['inventory'] = st.session_state[f"inv_{loc}"]
                        st.session_state.location_weights[loc]['prev_market_share'] = st.session_state[f"share_{loc}"]
                        st.session_state.location_weights[loc]['rx_per_hour'] = st.session_state[f"speed_{loc}"]
                        st.session_state.location_weights[loc]['base_traffic'] = st.session_state[f"bt_{loc}"]
                        st.success(f"Weights for {loc} updated successfully!")

        st.divider()
        st.subheader("🏆 Leaderboard")
        data = []
        for t, info in st.session_state.players.items():
            loc_disp = info['location'] if info['location'] else "❌ Not Selected"
            data.append({
                "Team": t,
                "Location": loc_disp,
                "Period": info['period'],
                "Cash": info['financials']['cash']
            })
        st.dataframe(pd.DataFrame(data).sort_values("Cash", ascending=False), hide_index=True)
    else:
        st.info("Please enter the password in the sidebar to access Instructor settings.")

# --- STUDENT VIEW ---
else:
    p_data = st.session_state.players[team]
    
    if p_data['location'] is None:
        st.title(f"👋 Welcome {team}!")
        st.warning("Please choose your starting location:")
        c1, c2 = st.columns([1, 2])
        with c1:
            selected_loc = st.radio("Available Locations:", LOCATIONS)
            if st.button("✅ Confirm Location & Start"):
                st.session_state.players[team]['location'] = selected_loc
                st.rerun()
    else:
        st.title(f"🏥 {team} - Period {p_data['period']}")
        st.markdown(f"**Location:** `{p_data['location']}` | **Cash:** `${p_data['financials']['cash']:,.2f}`")
        
        with st.form("decision_form_36"):
            st.subheader("📝 Decision Data Form")
            
            # Layout based on typical form groups
            with st.expander("1. Pricing & Policy", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    v1 = make_input("1. Rx Markup (%)", "v1", 49)
                    v2 = make_input("2. Rx Professional Fee ($)", "v2", 0)
                    v3 = make_input("3. Copayment Discount ($)", "v3", 0)
                with c2:
                    v14 = make_input("14. Other Items Markup (%)", "v14", 47)
                    v35 = st.selectbox("35. Participate 3rd Party Rx (1=Yes)", [0, 1], index=1)
                    v36 = make_input("36. Bid for HMO Contract ($)", "v36", 0)
                with c3:
                    v4 = st.selectbox("4. Delivery Service (1=Yes)", [0, 1], index=1)
                    v5 = st.selectbox("5. Patient Records (1=Yes)", [0, 1], index=1)
                    v6 = st.selectbox("6. Offer Credit (1=Yes)", [0, 1], index=1)

            with st.expander("2. Operations & Marketing", expanded=True):
                c1, c2, c3 = st.columns(3)
                v7 = make_input("7. Hours Open / Week", "v7", 46)
                v8 = make_input("8. Promo Expenditures ($)", "v8", 600)
                v9 = make_input("9. % Promo on Rx (%)", "v9", 90)

            with st.expander("3. Finance & Purchasing", expanded=False):
                c1, c2 = st.columns(2)
                v15 = make_input("15. Rx Purchases ($)", "v15", 40000)
                v16 = make_input("16. Other Purchases ($)", "v16", 16000)
                v10 = make_input("10. Current Inv. ($)", "v10", 2000)
                v11 = make_input("11. Project Number", "v11", 3)
                v12 = make_input("12. Inv. Withdrawal ($)", "v12", 0)
                v13 = make_input("13. Withdrawal Proj #", "v13", 0)
                v29 = make_input("29. Pay Accounts Payable ($)", "v29", 999999)
                v24 = make_input("24. Mortgage Payment ($)", "v24", 898)
                v25 = make_input("25. Collection Agency ($)", "v25", 0)
                v26 = make_input("26. Min Cash Balance ($)", "v26", 1000)
                v30 = make_input("30. Long Term Debt Written ($)", "v30", 0)
                v31 = make_input("31. Long Term Debt Payment ($)", "v31", 0)
                v32 = make_input("32. Interest Rate Receivables", "v32", 0)
                v27 = make_input("27. Rx Returned ($)", "v27", 0)
                v28 = make_input("28. Other Returned ($)", "v28", 0)

            with st.expander("4. Personnel", expanded=False):
                c1, c2 = st.columns(2)
                v17 = make_input("17. No. Pharmacists", "v17", 0.8, step=0.1)
                v18 = make_input("18. Pharm Wage ($/hr)", "v18", 21.0)
                v19 = make_input("19. No. Clerks", "v19", 1.2, step=0.1)
                v20 = make_input("20. Clerk Wage ($/hr)", "v20", 4.75)
                v21 = make_input("21. Manager Salary ($)", "v21", 8050)
                v22 = make_input("22. Mgr % Time Rx", "v22", 99)
                v23 = make_input("23. Mgr Hours/Week", "v23", 48)
                v33 = st.selectbox("33. Life Insurance (1=Yes)", [0, 1], index=1)
                v34 = st.selectbox("34. Health Insurance (1=Yes)", [0, 1], index=1)

            if st.form_submit_button("🚀 Submit Decisions"):
                decisions = {
                    'rx_markup': v1, 'rx_fee': v2, 'copay': v3, 'delivery': v4, 'records': v5,
                    'credit': v6, 'hours_open': v7, 'promo_exp': v8, 'promo_rx_pct': v9,
                    'inv_project_amt': v10, 'inv_project_num': v11, 'inv_withdrawal': v12,
                    'inv_with_num': v13, 'otc_markup': v14, 'buy_rx': v15, 'buy_otc': v16,
                    'n_pharm': v17, 'wage_pharm': v18, 'n_clerk': v19, 'wage_clerk': v20,
                    'manager_salary': v21, 'manager_time_rx': v22, 'manager_hours': v23,
                    'mortgage_payment': v24, 'collection_agency': v25, 'min_cash': v26,
                    'return_rx': v27, 'return_otc': v28, 'payment_ap': v29,
                    'debt_written': v30, 'debt_payment_long': v31, 'int_receivable': v32,
                    'benefit_life': v33, 'benefit_health': v34, 'participate_3rd': v35, 'hmo_bid': v36
                }
                run_period(team, decisions)
                st.success("Processed Period!")
                st.rerun()

        if p_data['history']:
            st.divider()
            st.subheader("📊 Team History")
            df_hist = pd.DataFrame(p_data['history'])
            st.dataframe(df_hist.style.format({"Revenue": "${:,.2f}", "Net Profit": "${:,.2f}", "Cash": "${:,.2f}"}))
