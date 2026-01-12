import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Multiplayer Full)", layout="wide")

# ค่าเริ่มต้นตลาด (Market Params)
DEFAULT_MARKET = {
    'base_traffic': 1200,      
    'mkt_rx_fee': 4.0,         
    'mkt_wage_pharm': 22.0,    
    'mkt_wage_clerk': 6.50,    
    'rent': 2000,              
    'owner_salary': 3000,      
    'tax_rate': 30,            
    'interest_rate': 12        
}

# ==========================================
# 2. State Initialization
# ==========================================
if 'market_params' not in st.session_state:
    st.session_state.market_params = DEFAULT_MARKET.copy()

if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8): # สร้าง Team 1 ถึง Team 7
        team_name = f"Team {i}"
        st.session_state.players[team_name] = {
            'period': 2,
            'financials': {
                'cash': 40000.0,
                'inv_rx': 25000.0,
                'inv_otc': 40000.0,
                'loans': 0.0
            },
            'history': []
        }

# ==========================================
# 3. Logic Engine 🧠
# ==========================================
def run_period(team_name, decisions):
    player_data = st.session_state.players[team_name]
    fin = player_data['financials']
    mkt = st.session_state.market_params
    
    # --- Logic ---
    price_sensitivity = 1.0 - ((decisions['rx_fee'] - mkt['mkt_rx_fee']) / 10.0)
    service_score = 1.0
    if decisions['delivery']: service_score += 0.05
    if decisions['records']: service_score += 0.10
    
    wage_quality_pharm = decisions['wage_pharm'] / mkt['mkt_wage_pharm']
    wage_quality_clerk = decisions['wage_clerk'] / mkt['mkt_wage_clerk']
    staff_quality = (wage_quality_pharm + wage_quality_clerk) / 2
    
    actual_traffic = mkt['base_traffic'] * price_sensitivity * service_score * staff_quality
    
    # Sales
    rx_cust = actual_traffic * 0.3
    rx_revenue = (rx_cust * 20) * (1 + decisions['rx_markup']/100) + (rx_cust * decisions['rx_fee'])
    cogs_rx = rx_cust * 20
    
    otc_cust = actual_traffic * 0.7
    otc_revenue = (otc_cust * 10) * (1 + decisions['otc_markup']/100)
    cogs_otc = otc_cust * 10
    
    # Expenses
    total_wages = (decisions['n_pharm']*160*decisions['wage_pharm']) + \
                  (decisions['n_clerk']*160*decisions['wage_clerk'])
    expenses = mkt['owner_salary'] + mkt['rent'] + total_wages + decisions['ads_budget'] + 500
    
    # Profit
    gross_margin = (rx_revenue + otc_revenue) - (cogs_rx + cogs_otc)
    net_profit_before_tax = gross_margin - expenses
    tax = net_profit_before_tax * (mkt['tax_rate']/100) if net_profit_before_tax > 0 else 0
    net_profit = net_profit_before_tax - tax
    
    # Update State
    fin['cash'] += (rx_revenue + otc_revenue) - (decisions['buy_rx'] + decisions['buy_otc'] + expenses + tax)
    fin['inv_rx'] += decisions['buy_rx'] - cogs_rx
    fin['inv_otc'] += decisions['buy_otc'] - cogs_otc
    
    player_data['history'].append({
        "Period": player_data['period'],
        "Total Sales": rx_revenue + otc_revenue,
        "Net Profit": net_profit,
        "Cash": fin['cash']
    })
    player_data['period'] += 1

# ==========================================
# 4. Sidebar
# ==========================================
with st.sidebar:
    st.header("🔐 ระบบเข้าใช้งาน")
    role = st.selectbox("สถานะผู้ใช้งาน", ["Student (นักเรียน)", "Instructor (อาจารย์)"])
    
    selected_team = None
    is_admin = False
    
    if role == "Student (นักเรียน)":
        team_list = list(st.session_state.players.keys())
        selected_team = st.selectbox("เลือกทีมของคุณ (Select Team)", team_list)
        st.info(f"Team: **{selected_team}**")
        
    else: # Instructor
        pwd = st.text_input("รหัสผ่านอาจารย์", type="password")
        if pwd == "admin":
            is_admin = True
            st.success("Admin Mode ✅")
        
    st.divider()
    if st.button("Reset All Teams"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 5. Main Content
# ==========================================

if is_admin:
    # ----------------------------------
    # 👨‍🏫 INSTRUCTOR FULL CONTROL
    # ----------------------------------
    st.title("👨‍🏫 Instructor Control Panel")
    
    # 1. ปรับค่าตลาด (Full Options)
    with st.expander("⚙️ ตั้งค่าตัวแปรตลาด (Market Parameters)", expanded=True):
        with st.form("admin_settings"):
            st.markdown("#### 1. สภาพตลาด & คู่แข่ง")
            c1, c2, c3, c4 = st.columns(4)
            new_traffic = c1.number_input("Base Traffic", value=st.session_state.market_params['base_traffic'])
            new_rx_fee = c2.number_input("Mkt Rx Fee ($)", value=st.session_state.market_params['mkt_rx_fee'])
            new_w_pharm = c3.number_input("Mkt Pharm Wage", value=st.session_state.market_params['mkt_wage_pharm'])
            new_w_clerk = c4.number_input("Mkt Clerk Wage", value=st.session_state.market_params['mkt_wage_clerk'])
            
            st.markdown("#### 2. ต้นทุนคงที่ & เศรษฐกิจ")
            c5, c6, c7, c8 = st.columns(4)
            new_rent = c5.number_input("Rent ($)", value=st.session_state.market_params['rent'])
            new_salary = c6.number_input("Owner Salary", value=st.session_state.market_params['owner_salary'])
            new_tax = c7.number_input("Tax Rate (%)", value=st.session_state.market_params['tax_rate'])
            new_int = c8.number_input("Interest Rate (%)", value=st.session_state.market_params['interest_rate'])

            if st.form_submit_button("💾 Save All Parameters"):
                st.session_state.market_params.update({
                    'base_traffic': new_traffic, 'mkt_rx_fee': new_rx_fee,
                    'mkt_wage_pharm': new_w_pharm, 'mkt_wage_clerk': new_w_clerk,
                    'rent': new_rent, 'owner_salary': new_salary,
                    'tax_rate': new_tax, 'interest_rate': new_int
                })
                st.success("อัปเดตค่าตัวแปรระบบครบถ้วนแล้ว!")

    # 2. Leaderboard (Fix Bug: ไม่ใช้ style.background_gradient)
    st.divider()
    st.subheader("🏆 อันดับคะแนน (
