import streamlit as st
import pandas as pd

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Final Fixed)", layout="wide")

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
    # 1. Demand Factors
    price_sensitivity = 1.0 - ((decisions['rx_fee'] - mkt['mkt_rx_fee']) / 10.0)
    service_score = 1.0
    if decisions['delivery']: service_score += 0.05
    if decisions['records']: service_score += 0.10
    
    wage_quality_pharm = decisions['wage_pharm'] / mkt['mkt_wage_pharm']
    wage_quality_clerk = decisions['wage_clerk'] / mkt['mkt_wage_clerk']
    staff_quality = (wage_quality_pharm + wage_quality_clerk) / 2
    
    actual_traffic = mkt['base_traffic'] * price_sensitivity * service_score * staff_quality
    
    # 2. Sales
    rx_cust = actual_traffic * 0.3
    rx_revenue = (rx_cust * 20) * (1 + decisions['rx_markup']/100) + (rx_cust * decisions['rx_fee'])
    cogs_rx = rx_cust * 20
    
    otc_cust = actual_traffic * 0.7
    otc_revenue = (otc_cust * 10) * (1 + decisions['otc_markup']/100)
    cogs_otc = otc_cust * 10
    
    # 3. Expenses
    total_wages = (decisions['n_pharm']*160*decisions['wage_pharm']) + \
                  (decisions['n_clerk']*160*decisions['wage_clerk'])
    expenses = mkt['owner_salary'] + mkt['rent'] + total_wages + decisions['ads_budget'] + 500
    
    # 4. Profit
    gross_margin = (rx_revenue + otc_revenue) - (cogs_rx + cogs_otc)
    net_profit_before_tax = gross_margin - expenses
    tax = net_profit_before_tax * (mkt['tax_rate']/100) if net_profit_before_tax > 0 else 0
    net_profit = net_profit_before_tax - tax
    
    # 5. Update State
    fin['cash'] += (rx_revenue + otc_revenue) - (decisions['buy_rx'] + decisions['buy_otc'] + expenses + tax)
    fin['inv_rx'] += decisions['buy_rx'] - cogs_rx
    fin['inv_otc'] += decisions['buy_otc'] - cogs_otc
    
    # 6. Save History
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
    st.header("🔐 Access Control")
    role = st.selectbox("เลือกบทบาท (Role)", ["Student (นักเรียน)", "Instructor (อาจารย์)"])
    
    selected_team = None
    is_admin = False
    
    if role == "Student (นักเรียน)":
        team_list = list(st.session_state.players.keys())
        selected_team = st.selectbox("เลือกทีมของคุณ (Team)", team_list)
        st.info(f"Playing as: **{selected_team}**")
        
    else: # Instructor
        pwd = st.text_input("Admin Password", type="password")
        if pwd == "admin":
            is_admin = True
            st.success("Admin Logged In ✅")
        elif pwd:
            st.error("Wrong Password ❌")
            
    st.divider()
    if st.button("Reset Game (เริ่มใหม่ทั้งหมด)"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 5. Main Content
# ==========================================

if is_admin:
    # ----------------------------------
    # 👨‍🏫 INSTRUCTOR DASHBOARD
    # ----------------------------------
    st.title("👨‍🏫 Instructor Control Panel")
    st.info("หน้านี้สำหรับอาจารย์เพื่อกำหนดความยากง่ายของเกม")

    # ส่วนที่ 1: ปรับค่าตลาด (คืนค่ามาให้ครบ 8 ตัวแล้วครับ)
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

            if st.form_submit_button("💾 Save Parameters"):
                st.session_state.market_params.update({
                    'base_traffic': new_traffic, 'mkt_rx_fee': new_rx_fee,
                    'mkt_wage_pharm': new_w_pharm, 'mkt_wage_clerk': new_w_clerk,
                    'rent': new_rent, 'owner_salary': new_salary,
                    'tax_rate': new_tax, 'interest_rate': new_int
                })
                st.success("บันทึกค่าตัวแปรใหม่เรียบร้อย!")

    # ส่วนที่ 2: Leaderboard (เอาส่วนที่ทำ Error ออกแล้ว)
    st.divider()
    st.subheader("🏆 อันดับคะแนน (Leaderboard)")
    
    leaderboard_data = []
    for t_name, t_data in st.session_state.players.items():
        last_profit = 0
        if t_data['history']:
            last_profit = t_data['history'][-1]['Net Profit']
        
        leaderboard_data.append({
            "Team": t_name,
            "Period": t_data['period'],
            "Cash": t_data['financials']['cash'],
            "Last Profit": last_profit,
            "Rx Stock": t_data['financials']['inv_rx'],
            "OTC Stock": t_data['financials']['inv_otc']
        })
        
    df_leader = pd.DataFrame(leaderboard_data)
    # เรียงลำดับคนรวยสุดขึ้นก่อน
    df_leader = df_leader.sort_values(by="Cash", ascending=False).reset_index(drop=True)
    
    # แสดงตารางแบบคลีนๆ ไม่ใช้สีไล่ระดับเพื่อกัน Error
    st.dataframe(
        df_leader,
        column_config={
            "Cash": st.column_config.NumberColumn(format="$%.2f"),
            "Last Profit": st.column_config.NumberColumn(format="$%.2f"),
            "Rx Stock": st.column_config.NumberColumn(format="$%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )

elif selected_team:
    # ----------------------------------
    # 🎓 STUDENT PLAY AREA
    # ----------------------------------
    my_data = st.session_state.players[selected_team]
    my_fin = my_data['financials']
    
    st.title(f"🏥 {selected_team} - Period {my_data['period']}")
    
    # Dashboard
    col1, col2, col3 = st.columns(3)
    col1.metric("Cash (เงินสด)", f"${my_fin['cash']:,.2f}")
    col2.metric("Rx Stock (ยา)", f"${my_fin['inv_rx']:,.2f}")
    col3.metric("OTC Stock (สินค้าทั่วไป)", f"${my_fin['inv_otc']:,.2f}")
    
    with st.form("decision_form"):
        st.subheader("📝 ตัดสินใจบริหาร (Decisions)")
        
        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown("**1. ราคาและการตลาด**")
            in_rx_m = st.number_input("Rx Markup (%)", 0.0, 100.0, 25.0)
            in_rx_f = st.number_input("Rx Fee ($)", 0.0, 20.0, 4.0)
            in_otc_m = st.number_input("OTC Markup (%)", 0.0, 100.0, 50.0)
            in_ads = st.number_input("Ads Budget ($)", 0, 10000, 500)
            
        with c_b:
            st.markdown("**2. การจัดการและบุคลากร**")
            in_buy_rx = st.number_input("ซื้อยาเพิ่ม (Buy Rx $)", 0, 100000, 15000)
            in_buy_otc = st.number_input("ซื้อของเพิ่ม (Buy OTC $)", 0, 100000, 20000)
            in_n_pharm = st.number_input("จ้างเภสัช (คน)", 1, 5, 1)
            in_w_pharm = st.number_input("ค่าแรงเภสัช ($/hr)", 10.0, 60.0, 22.0)
        
        # ค่า Default สำหรับตัวที่ซ่อนไว้ (เพื่อประหยัดที่)
        in_n_clerk, in_w_clerk = 2, 6.50
        in_del, in_rec = False, False
        
        if st.form_submit_button("🚀 ส่งผลการตัดสินใจ (Submit)"):
            decisions = {
                'rx_markup': in_rx_m, 'rx_fee': in_rx_f, 'otc_markup': in_otc_m,
                'ads_budget': in_ads, 'buy_rx': in_buy_rx, 'buy_otc': in_buy_otc,
                'n_pharm': in_n_pharm, 'wage_pharm': in_w_pharm,
                'n_clerk': in_n_clerk, 'wage_clerk': in_w_clerk,
                'delivery': in_del, 'records': in_rec
            }
            run_period(selected_team, decisions)
            st.rerun()

    # History
    if my_data['history']:
        st.divider()
        st.subheader("📜 ประวัติผลประกอบการ")
        hist_df = pd.DataFrame(my_data['history'])
        st.dataframe(hist_df.style.format({"Total Sales": "${:,.2f}", "Net Profit": "${:,.2f}", "Cash": "${:,.2f}"}))

else:
    st.info("กรุณาเลือกบทบาทจากเมนูด้านซ้าย (Sidebar)")
