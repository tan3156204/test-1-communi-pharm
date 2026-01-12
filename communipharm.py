import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Multiplayer)", layout="wide")

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
# 2. State Initialization (สร้างข้อมูล 7 ทีม)
# ==========================================
# โหลดค่า Market
if 'market_params' not in st.session_state:
    st.session_state.market_params = DEFAULT_MARKET.copy()

# โหลดข้อมูลผู้เล่น (ถ้ายังไม่มี ให้สร้าง 7 ทีม)
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
            'history': [] # เก็บประวัติแยกของใครของมัน
        }

# ==========================================
# 3. Logic Engine (รองรับ Team ID) 🧠
# ==========================================
def run_period(team_name, decisions):
    # ดึงข้อมูลเฉพาะทีมที่เล่น
    player_data = st.session_state.players[team_name]
    fin = player_data['financials']
    mkt = st.session_state.market_params
    
    # --- Logic คำนวณ (เหมือนเดิม) ---
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
    
    # บันทึก History ลงในทีมนั้นๆ
    player_data['history'].append({
        "Period": player_data['period'],
        "Total Sales": rx_revenue + otc_revenue,
        "Net Profit": net_profit,
        "Cash": fin['cash']
    })
    player_data['period'] += 1

# ==========================================
# 4. Sidebar: Login & Team Selector
# ==========================================
with st.sidebar:
    st.header("🔐 ระบบเข้าใช้งาน")
    role = st.selectbox("สถานะผู้ใช้งาน", ["Student (นักเรียน)", "Instructor (อาจารย์)"])
    
    selected_team = None
    is_admin = False
    
    if role == "Student (นักเรียน)":
        # เลือกทีมที่จะเล่น
        team_list = list(st.session_state.players.keys())
        selected_team = st.selectbox("เลือกทีมของคุณ (Select Team)", team_list)
        st.info(f"คุณกำลังเล่นในชื่อ: **{selected_team}**")
        
    else: # Instructor
        pwd = st.text_input("รหัสผ่านอาจารย์", type="password")
        if pwd == "admin":
            is_admin = True
            st.success("Admin Mode ✅")
        
    st.divider()
    if st.button("Reset All Teams (ล้างกระดาน)"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 5. Main Content
# ==========================================

if is_admin:
    # ----------------------------------
    # 👨‍🏫 INSTRUCTOR DASHBOARD
    # ----------------------------------
    st.title("🏆 Instructor Leaderboard")
    
    # 1. ปรับค่าตลาด (เหมือนเดิม)
    with st.expander("⚙️ ปรับตั้งค่าตลาด (Game Parameters)"):
        with st.form("admin_settings"):
            c1, c2 = st.columns(2)
            new_traffic = c1.number_input("Base Traffic", value=st.session_state.market_params['base_traffic'])
            new_rent = c2.number_input("Rent", value=st.session_state.market_params['rent'])
            if st.form_submit_button("Update Params"):
                st.session_state.market_params['base_traffic'] = new_traffic
                st.session_state.market_params['rent'] = new_rent
                st.rerun()

    # 2. ตารางคะแนนรวม (Leaderboard)
    st.subheader("📊 อันดับคะแนนปัจจุบัน")
    
    leaderboard_data = []
    for t_name, t_data in st.session_state.players.items():
        # เอาข้อมูลล่าสุดมาโชว์
        last_profit = 0
        if t_data['history']:
            last_profit = t_data['history'][-1]['Net Profit']
        
        leaderboard_data.append({
            "Team": t_name,
            "Current Period": t_data['period'],
            "Cash in Hand": t_data['financials']['cash'],
            "Last Net Profit": last_profit,
            "Rx Stock": t_data['financials']['inv_rx'],
            "OTC Stock": t_data['financials']['inv_otc']
        })
        
    df_leader = pd.DataFrame(leaderboard_data)
    # จัดเรียงตามเงินสด (Cash)
    df_leader = df_leader.sort_values(by="Cash in Hand", ascending=False).reset_index(drop=True)
    
    # ไฮไลท์สีทีมที่รวยสุด
    st.dataframe(df_leader.style.background_gradient(subset=['Cash in Hand'], cmap='Greens'))
    
    st.caption("*Instructor สามารถดูภาพรวมสถานะการเงินของนักเรียนทั้ง 7 ทีมได้ที่นี่")

elif selected_team:
    # ----------------------------------
    # 🎓 STUDENT PLAY AREA
    # ----------------------------------
    # ดึงข้อมูลเฉพาะทีมที่เลือก
    my_data = st.session_state.players[selected_team]
    my_fin = my_data['financials']
    
    st.title(f"🏥 {selected_team}: Period {my_data['period']}")
    
    # Dashboard ส่วนตัว
    c1, c2, c3 = st.columns(3)
    c1.metric("My Cash", f"${my_fin['cash']:,.2f}")
    c2.metric("Rx Stock", f"${my_fin['inv_rx']:,.2f}")
    c3.metric("OTC Stock", f"${my_fin['inv_otc']:,.2f}")
    
    # Form ตัดสินใจ (เหมือนเดิม แต่ส่งค่า team_name ไปด้วย)
    with st.form("decision_form"):
        st.subheader("📝 Decisions")
        # (ย่อโค้ด Input เพื่อความกระชับ แต่ Logic เหมือนเดิม)
        col_A, col_B = st.columns(2)
        with col_A:
            in_rx_m = st.number_input("Rx Markup %", 0.0, 100.0, 25.0)
            in_rx_f = st.number_input("Rx Fee $", 0.0, 20.0, 4.0)
            in_otc_m = st.number_input("OTC Markup %", 0.0, 100.0, 50.0)
            in_ads = st.number_input("Ads Budget $", 0, 10000, 500)
        with col_B:
            in_buy_rx = st.number_input("Buy Rx $", 0, 100000, 15000)
            in_buy_otc = st.number_input("Buy OTC $", 0, 100000, 20000)
            in_n_pharm = st.number_input("# Pharm", 1, 5, 1)
            in_w_pharm = st.number_input("Wage Pharm", 10.0, 60.0, 22.0)
        
        # ใส่ค่า Default สำหรับตัวแปรที่เหลือเพื่อประหยัดที่หน้าจอ
        in_n_clerk, in_w_clerk = 2, 6.50
        in_del, in_rec = False, False
        
        if st.form_submit_button("🚀 Submit for THIS TEAM"):
            decisions = {
                'rx_markup': in_rx_m, 'rx_fee': in_rx_f, 'otc_markup': in_otc_m,
                'ads_budget': in_ads, 'buy_rx': in_buy_rx, 'buy_otc': in_buy_otc,
                'n_pharm': in_n_pharm, 'wage_pharm': in_w_pharm,
                'n_clerk': in_n_clerk, 'wage_clerk': in_w_clerk,
                'delivery': in_del, 'records': in_rec
            }
            # ส่งชื่อทีมเข้าไปประมวลผล
            run_period(selected_team, decisions)
            st.rerun()

    # History ส่วนตัว
    if my_data['history']:
        st.divider()
        st.subheader("📜 ประวัติการเล่นของทีมเรา")
        st.dataframe(pd.DataFrame(my_data['history']))

else:
    st.info("กรุณาเลือกโหมดการใช้งานจากเมนูด้านซ้าย")
