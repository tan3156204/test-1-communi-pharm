import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Full 36 Inputs)", layout="wide")

# ชื่อทำเล
LOCATIONS = ["Med Center", "Neighborhood", "Shopping"]

# Instructor Weights (ค่าความสำคัญที่อาจารย์กำหนด)
DEFAULT_WEIGHTS = {
    "Med Center": {
        "price_sensitivity": 3, "promotion_impact": 2, "hours_importance": 8,
        "service_delivery": 9, "service_records": 9, "credit_policy": 5,
        "inventory_level": 8, "market_share_momentum": 5, "service_speed": 8,
        "base_traffic": 1500
    },
    "Neighborhood": {
        "price_sensitivity": 5, "promotion_impact": 4, "hours_importance": 6,
        "service_delivery": 7, "service_records": 6, "credit_policy": 6,
        "inventory_level": 6, "market_share_momentum": 5, "service_speed": 5,
        "base_traffic": 1000
    },
    "Shopping": {
        "price_sensitivity": 9, "promotion_impact": 8, "hours_importance": 5,
        "service_delivery": 2, "service_records": 2, "credit_policy": 4,
        "inventory_level": 5, "market_share_momentum": 5, "service_speed": 6,
        "base_traffic": 2000
    }
}

# ==========================================
# 2. State Initialization
# ==========================================
if 'location_weights' not in st.session_state:
    st.session_state.location_weights = DEFAULT_WEIGHTS.copy()

if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_name = f"Team {i}"
        loc = LOCATIONS[(i-1) % 3]
        st.session_state.players[team_name] = {
            'location': loc,
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
# 3. Logic Engine (รองรับ 36 ตัวแปร)
# ==========================================
def run_period(team_name, d):
    # d = decisions dictionary (36 items)
    player = st.session_state.players[team_name]
    loc_type = player['location']
    weights = st.session_state.location_weights[loc_type]
    fin = player['financials']
    
    # --- 1. Demand Calculation (คิดคะแนนความนิยม) ---
    # Price Score (Rx Fee & Markup)
    price_score = 1.0
    if d['rx_fee'] > 5: price_score -= 0.1
    if d['rx_markup'] > 40: price_score -= 0.1
    
    # Service Score
    service_score = 1.0
    if d['delivery'] == 1: service_score += weights['service_delivery'] * 0.02
    if d['records'] == 1: service_score += weights['service_records'] * 0.02
    if d['credit'] == 1: service_score += weights['credit_policy'] * 0.02
    
    # Hours & Staffing
    hours_bonus = (d['hours_open'] - 40) * (weights['hours_importance'] * 0.002)
    
    # Total Traffic Multiplier
    multiplier = price_score * service_score * (1 + hours_bonus) * (1 + (d['promo_exp'] / 10000))
    traffic = weights['base_traffic'] * max(0.5, multiplier)
    
    # --- 2. Sales & Revenue ---
    rx_cust = int(traffic * 0.3)
    otc_cust = int(traffic * 0.7)
    
    # Rx Revenue
    # สูตร: (Cost + Markup) + Fee
    # สมมติ Cost ต่อ Rx = $10
    rx_cost_base = 10
    rx_price = rx_cost_base * (1 + d['rx_markup']/100) + d['rx_fee']
    rx_revenue = rx_cust * rx_price
    rx_cogs = rx_cust * rx_cost_base
    
    # OTC Revenue
    otc_cost_base = 5
    otc_price = otc_cost_base * (1 + d['otc_markup']/100)
    otc_revenue = otc_cust * otc_price
    otc_cogs = otc_cust * otc_cost_base
    
    # --- 3. Expenses Calculation (36 Variables Impact) ---
    # Staff Costs
    cost_pharm = d['n_pharm'] * d['wage_pharm'] * d['hours_open'] * 4 # 4 weeks/month
    cost_clerk = d['n_clerk'] * d['wage_clerk'] * d['hours_open'] * 4
    cost_manager = d['manager_salary']
    benefits_cost = 0
    if d['benefit_life'] == 1: benefits_cost += 200
    if d['benefit_health'] == 1: benefits_cost += 500
    
    total_wages = cost_pharm + cost_clerk + cost_manager + benefits_cost
    
    # Operation Costs
    mortgage = d['mortgage_payment']
    promo = d['promo_exp']
    other_expenses = 1000 # Utilities etc.
    
    total_expenses = total_wages + mortgage + promo + other_expenses
    
    # --- 4. Financial Updates ---
    gross_profit = (rx_revenue + otc_revenue) - (rx_cogs + otc_cogs)
    net_profit = gross_profit - total_expenses
    
    # Cash Flow Logic
    # Cash In: Sales + Withdrawals (ถ้าถอนทุนคืน)
    # Cash Out: Expenses + Purchases + Debt Payment + Investments
    
    cash_in = rx_revenue + otc_revenue + d['inv_withdrawal']
    cash_out = total_expenses + d['buy_rx'] + d['buy_otc'] + d['inv_project_amt'] + d['debt_payment_long']
    
    # Accounts Payable Logic (จ่ายหนี้เก่า)
    payable_payment = d['payment_ap']
    if payable_payment > fin['accounts_payable']:
        payable_payment = fin['accounts_payable'] # จ่ายเท่าที่มีหนี้
    
    fin['cash'] = fin['cash'] + cash_in - cash_out - payable_payment
    
    # Update Debt/Stock
    fin['inventory_rx'] += d['buy_rx'] - rx_cogs
    fin['inventory_otc'] += d['buy_otc'] - otc_cogs
    fin['accounts_payable'] = (fin['accounts_payable'] - payable_payment) + (d['buy_rx'] + d['buy_otc']) * 0.5 # สมมติเครดิต 50%
    fin['long_term_debt'] -= d['debt_payment_long']
    
    # Save History
    player['history'].append({
        "Period": player['period'],
        "Revenue": rx_revenue + otc_revenue,
        "Net Profit": net_profit,
        "Cash": fin['cash'],
        "Rx Sales": rx_cust
    })
    player['period'] += 1

# ==========================================
# 4. Helper: Input Form Generator
# ==========================================
def make_input(label, key, default, min_v=0.0, max_v=1000000.0, step=1.0):
    return st.number_input(label, min_value=float(min_v), max_value=float(max_v), value=float(default), step=step, key=key)

# ==========================================
# 5. Main UI
# ==========================================
with st.sidebar:
    st.header("💊 Communi-Pharm")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Select Team", list(st.session_state.players.keys()))
        if st.button("Reset All"):
            st.session_state.clear()
            st.rerun()

if role == "Instructor":
    st.title("👨‍🏫 Instructor Control Panel")
    
    # Tabs for each location
    tabs = st.tabs(LOCATIONS)
    for i, loc in enumerate(LOCATIONS):
        with tabs[i]:
            st.subheader(f"Settings for {loc}")
            w = st.session_state.location_weights[loc]
            
            # Form to update 10 weights
            with st.form(f"admin_{loc}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input("Base Traffic", value=w['base_traffic'], key=f"bt_{loc}")
                    st.slider("Price Sensitivity", 1, 10, w['price_sensitivity
