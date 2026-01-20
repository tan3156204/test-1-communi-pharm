import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. SYSTEM CONFIG & STATE
# ==========================================
st.set_page_config(page_title="Communi-Pharm V17 (Control Ed.)", layout="wide")

# Constants
BASE_COST_RX = 11.23
CONST_FEE = 2.90
WEEKS = 13
EMERGENCY_LOAN_RATE = 0.20

# Location Config
LOC_CONFIG = {
    1: {"name": "Medical Center", "rent": 0.045, "desc": "เน้นใบสั่งยา, ค่าเช่า 4.5%"},
    2: {"name": "Neighborhood", "rent": 0.030, "desc": "ชุมชน, ค่าเช่า 3.0%"},
    3: {"name": "Shopping Center", "rent": 0.025, "desc": "ห้างฯ, ค่าเช่า 2.5%"}
}

# Market Weights
WEIGHTS = {
    1: {'price': 10, 'fee': 30, 'promo': 5, 'hours': 20, 'delivery': 5},
    2: {'price': 20, 'fee': 25, 'promo': 10, 'hours': 10, 'delivery': 10},
    3: {'price': 40, 'fee': 30, 'promo': 15, 'hours': 5, 'delivery': 0}
}

# Initialize Session State
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP" # SETUP, ACTIVE
    st.session_state.current_period = 1
    st.session_state.teams = {} 
    st.session_state.history = {} 

# ==========================================
# 2. CALCULATION ENGINE
# ==========================================
def run_period_processing():
    period = st.session_state.current_period
    all_teams = st.session_state.teams
    
    # 1. จัดกลุ่มแข่งตามทำเล
    for loc_id in [1, 2, 3]:
        teams_in_loc = [tid for tid, t in all_teams.items() if t['loc'] == loc_id]
        if not teams_in_loc: continue
        
        # 2. คำนวณ Market Share
        df_score = pd.DataFrame()
        for tid in teams_in_loc:
            curr_inputs = all_teams[tid]['inputs_next']
            price = (BASE_COST_RX * (1 + curr_inputs[0]/100)) + curr_inputs[1] + CONST_FEE
            
            score = 0
            w = WEIGHTS[loc_id]
            score += (1000/price) * w['price']
            score += (curr_inputs[7]/1000) * w['promo']
            score += (curr_inputs[6]/50) * w['hours']
            
            df_score = pd.concat([df_score, pd.DataFrame({'tid': tid, 'score': score}, index=[0])])
            
        df_score['share'] = df_score['score'] / df_score['score'].sum()
        
        # 3. คำนวณงบการเงิน
        market_size = 300000 if loc_id == 1 else 1200000
        if loc_id == 3: market_size = 900000
        
        for idx, row in df_score.iterrows():
            tid = row['tid']
            share = row['share']
            inp = all_teams[tid]['inputs_next']
            prev_bal = all_teams[tid]['balance_sheet']
            
            sales = share * market_size
            cogs = sales / (1 + (inp[0]/100))
            gross_margin = sales - cogs
            
            rent_exp = sales * LOC_CONFIG[loc_id]['rent']
            wages = (inp[16]*inp[17] + inp[18]*inp[19]) * inp[6] * WEEKS
            fixed = inp[20] + inp[7] + 3000
            depr = 50000 * 0.025
            
            inv_income = inp[9] * 0.02
            interest_exp = 0
            
            cash_begin = prev_bal['cash']
            purchases = inp[14] + inp[15]
            pay_ap = inp[28]
            
            cash_in = sales * 0.9 + inv_income
            cash_out = wages + rent_exp + fixed + pay_ap + purchases
            
            cash_end = cash_begin + cash_in - cash_out
            
            emergency_loan = 0
            if cash_end < 0:
                emergency_loan = abs(cash_end) + 2000
                interest_exp += emergency_loan * EMERGENCY_LOAN_RATE
                cash_end += emergency_loan
                
            if pay_ap > 200000: interest_exp += 29000000
            
            net_profit = (gross_margin - (wages + rent_exp + fixed + depr)) + inv_income - interest_exp
            
            inventory = prev_bal['inventory'] + purchases - cogs
            ar = prev_bal['ar'] + (sales * 0.1)
            ap = prev_bal['ap'] + purchases - pay_ap
            retained_earnings = prev_bal['retained_earnings'] + net_profit
            
            new_bal = {
                'cash': cash_end, 'inventory': inventory, 'ar': ar,
                'fixed_assets': prev_bal['fixed_assets'] - depr, 'ap': ap,
                'emergency_loan': emergency_loan, 'long_term_debt': 100000,
                'retained_earnings': retained_earnings
            }
            
            if tid not in st.session_state.history: st.session_state.history[tid] = []
            st.session_state.history[tid].append({
                "period": period,
                "income_statement": {
                    "Sales": sales, "COGS": cogs, "Gross Margin": gross_margin,
                    "Expenses": wages+rent_exp+fixed+depr, "Interest": interest_exp, "Net Profit": net_profit
                },
                "balance_sheet": new_bal,
                "ratios": {
                    "ROS": (net_profit/sales)*100,
                    "Current Ratio": (cash_end+inventory+ar)/(ap+emergency_loan) if (ap+emergency_loan)>0 else 99
                }
            })
            
            all_teams[tid]['balance_sheet'] = new_bal
            all_teams[tid]['inputs_prev'] = inp.copy()
            all_teams[tid]['status'] = "Pending" # Reset status

    st.session_state.current_period += 1

# ==========================================
# 3. SIDEBAR (RESET BUTTON)
# ==========================================
with st.sidebar:
    st.title("⚙️ System Control")
    st.write("ปุ่มควบคุมระบบสำหรับเริ่มต้นใหม่")
    if st.button("🔄 Reset Game (เริ่มใหม่)", type="primary"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 4. INSTRUCTOR VIEW
# ==========================================
def instructor_view():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP":
        st.subheader("1. Game Setup (ตั้งค่าก่อนเริ่ม)")
        st.info("กรุณากำหนดจำนวนทีม แล้วกดปุ่ม Start Game เพื่อเริ่ม Period 1")
        
        num_teams = st.number_input("จำนวนทีม (Stores)", 1, 10, 3)
        
        # --- BUTTON 1: START GAME ---
        if st.button("🏁 Start Game (เริ่มเล่นเกม)"):
            default_inputs = [49, 0, 0, 1, 1, 1, 46, 600, 90, 2000, 3, 0, 0, 47, 40000, 16000, 0.8, 21, 1.2, 4.75, 8050, 99, 48, 898, 0, 1000, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]
            default_bs = {'cash': 15000, 'inventory': 80000, 'ar': 45000, 'fixed_assets': 50000, 'ap': 30000, 'emergency_loan': 0, 'long_term_debt': 100000, 'retained_earnings': 60000}
            
            for i in range(num_teams):
                tid = f"Store {i+1}"
                loc = (i % 3) + 1
                st.session_state.teams[tid] = {
                    'loc': loc,
                    'inputs_next': default_inputs.copy(),
                    'inputs_prev': default_inputs.copy(),
                    'balance_sheet': default_bs.copy(),
                    'status': "Ready" # Pending, Draft, Ready
                }
            
            run_period_processing() # Run P1 automatically
            st.session_state.game_state = "ACTIVE"
            st.rerun()
            
    else: # ACTIVE GAME
        period = st.session_state.current_period
        st.subheader(f"Current Status: Period {period}")
        st.markdown("---")
        
        st.write("### 📡 สถานะผู้เล่น")
        status_data = []
        ready_count = 0
        for tid, data in st.session_state.teams.items():
            status_text = "⚪ รอส่งข้อมูล"
            if data['status'] == "Draft": status_text = "🟡 กำลังกรอก (Draft)"
            if data['status'] == "Ready": 
                status_text = "✅ ส่งแล้ว (Ready)"
                ready_count += 1
            
            status_data.append({"Team": tid, "Location": LOC_CONFIG[data['loc']]['name'], "Status": status_text})
        
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        
        # --- CONTROL PANEL ---
        if ready_count == len(st.session_state.teams):
            st.success("ทุกทีมพร้อมแล้ว! กด Run เพื่อประมวลผล")
        else:
            st.warning(f"มีทีมพร้อมส่ง {ready_count}/{len(st.session_state.teams)} ทีม")

        if st.button(f"🚀 Run Simulation (Process Period {period})", type="primary"):
            run_period_processing()
            st.success("ประมวลผลเสร็จสิ้น!")
            st.rerun()

# ==========================================
# 5. STUDENT VIEW
# ==========================================
def student_view():
    st.header("💊 Student Portal")
    
    if not st.session_state.teams:
        st.error("Game hasn't started yet. (รออาจารย์กด Start Game)")
        return

    my_team = st.selectbox("เลือกทีมของคุณ (Select Your Store)", list(st.session_state.teams.keys()))
    team_data = st.session_state.teams[my_team]
    current_period = st.session_state.current_period
    
    # Check Status
    is_submitted = team_data['status'] == "Ready"
    
    # Tabs
    tab1, tab2 = st.tabs([f"📊 ผลลัพธ์ (Period {current_period-1})", f"📝 ตัดสินใจ (Period {current_period})"])
    
    with tab1:
        if my_team in st.session_state.history and st.session_state.history[my_team]:
            last_result = st.session_state.history[my_team][-1]
            inc = last_result['income_statement']
            bs = last_result['balance_sheet']
            st.markdown(f"### ผลประกอบการรอบที่ {last_result['period']}")
            c1, c2 = st.columns(2)
            c1.metric("Net Profit", f"${inc['Net Profit']:,.0f}")
            c2.metric("Cash Balance", f"${bs['cash']:,.0f}")
            
            with st.expander("ดูงบการเงินละเอียด"):
                st.write("Income Statement:", inc)
                st.write("Balance Sheet:", bs)
        else:
            st.info("รอผลการรันรอบแรก")

    with tab2:
        st.markdown(f"### แบบฟอร์มตัดสินใจ รอบที่ {current_period}")
        
        if is_submitted:
            st.success("✅ คุณได้ยืนยันการส่งข้อมูลแล้ว (รออาจารย์ประมวลผล)")
            if st.button("✏️ แก้ไขข้อมูล (Unsubmit)"):
                st.session_state.teams[my_team]['status'] = "Draft"
                st.rerun()
        else:
            st.info("กรอกตัวเลข แล้วกด 'Save' เพื่อบันทึกค่า หรือ 'Submit' เพื่อส่งอาจารย์")
            
            # Form without 'st.form' to allow Save Draft functionality
            defaults = team_data['inputs_next']
            new_inputs = defaults.copy()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**การตลาด**")
                new_inputs[0] = st.number_input("1. Rx Markup (%)", value=defaults[0], key="i0")
                new_inputs[7] = st.number_input("8. Promo ($)", value=defaults[7], key="i7")
                new_inputs[6] = st.number_input("7. Hours/Week", value=defaults[6], key="i6")
            with col2:
                st.markdown("**การเงิน & สต็อก**")
                new_inputs[14] = st.number_input("15. Rx Purchase ($)", value=defaults[14], key="i14")
                new_inputs[28] = st.number_input("29. Pay A/P ($)", value=defaults[28], key="i28")
            
            st.markdown("---")
            b1, b2 = st.columns(2)
            
            # --- BUTTON 2: SAVE DRAFT ---
            if b1.button("💾 บันทึกค่า (Save Draft)"):
                st.session_state.teams[my_team]['inputs_next'] = new_inputs
                st.session_state.teams[my_team]['status'] = "Draft"
                st.toast("บันทึกข้อมูลเรียบร้อย (ยังไม่ส่ง)", icon="💾")
                st.rerun()
            
            # --- BUTTON 3: SUBMIT ---
            if b2.button("✅ ยืนยันการส่ง (Submit)", type="primary"):
                st.session_state.teams[my_team]['inputs_next'] = new_inputs
                st.session_state.teams[my_team]['status'] = "Ready"
                st.success("ส่งข้อมูลให้อาจารย์แล้ว!")
                st.rerun()

# ==========================================
# 6. APP ROUTER
# ==========================================
role = st.sidebar.radio("เลือกบทบาท (Role)", ["Student (ผู้เล่น)", "Instructor (ผู้สอน)"])

if role == "Instructor (ผู้สอน)":
    pwd = st.sidebar.text_input("Instructor Password", type="password")
    if pwd == "admin":
        instructor_view()
    else:
        st.sidebar.warning("ใส่รหัสผ่าน: admin")
else:
    if st.session_state.game_state == "SETUP":
        st.title("⏳ Game Lobby")
        st.warning("รอให้อาจารย์กดปุ่ม Start Game...")
    else:
        student_view()
