import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. SYSTEM CONFIG & STATE
# ==========================================
st.set_page_config(page_title="Communi-Pharm V16 (Classroom Ed.)", layout="wide")

# Constants ตามคู่มือ
BASE_COST_RX = 11.23
CONST_FEE = 2.90
WEEKS = 13
EMERGENCY_LOAN_RATE = 0.20
TAX_RATE = 0.0

# Location Config (ค่าเช่าตามคู่มือ)
LOC_CONFIG = {
    1: {"name": "Medical Center", "rent": 0.045, "desc": "เน้นใบสั่งยา, ค่าเช่า 4.5%"},
    2: {"name": "Neighborhood", "rent": 0.030, "desc": "ชุมชน, ค่าเช่า 3.0%"},
    3: {"name": "Shopping Center", "rent": 0.025, "desc": "ห้างฯ, ค่าเช่า 2.5%"}
}

# Market Weights (ความสำคัญของปัจจัยในแต่ละทำเล)
WEIGHTS = {
    1: {'price': 10, 'fee': 30, 'promo': 5, 'hours': 20, 'delivery': 5},
    2: {'price': 20, 'fee': 25, 'promo': 10, 'hours': 10, 'delivery': 10},
    3: {'price': 40, 'fee': 30, 'promo': 15, 'hours': 5, 'delivery': 0}
}

# Initialize Session State (จำลอง Database)
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP" # SETUP, ACTIVE
    st.session_state.current_period = 1
    st.session_state.teams = {} # เก็บข้อมูลทุกทีม
    st.session_state.history = {} # เก็บประวัติผลลัพธ์

# ==========================================
# 2. CALCULATION ENGINE (CORE LOGIC)
# ==========================================
def run_period_processing():
    """ฟังก์ชันนี้คือ 'Computer Program' ที่อาจารย์กด Run เพื่อประมวลผล"""
    period = st.session_state.current_period
    all_teams = st.session_state.teams
    
    # 1. จัดกลุ่มแข่งตามทำเล (Competition)
    for loc_id in [1, 2, 3]:
        teams_in_loc = [tid for tid, t in all_teams.items() if t['loc'] == loc_id]
        if not teams_in_loc: continue
        
        # 2. คำนวณ Market Share
        df_score = pd.DataFrame()
        for tid in teams_in_loc:
            curr_inputs = all_teams[tid]['inputs_next'] # ดึงค่าที่นศ.กรอกมา
            
            # คำนวณราคาขาย
            price = (BASE_COST_RX * (1 + curr_inputs[0]/100)) + curr_inputs[1] + CONST_FEE
            
            score = 0
            w = WEIGHTS[loc_id]
            # Scoring Logic (Simplified)
            score += (1000/price) * w['price']
            score += (curr_inputs[7]/1000) * w['promo']
            score += (curr_inputs[6]/50) * w['hours']
            
            df_score = pd.concat([df_score, pd.DataFrame({'tid': tid, 'score': score}, index=[0])])
            
        df_score['share'] = df_score['score'] / df_score['score'].sum()
        
        # 3. คำนวณงบการเงินรายทีม
        market_size = 300000 if loc_id == 1 else 1200000 # สมมติ Market Size
        if loc_id == 3: market_size = 900000
        
        for idx, row in df_score.iterrows():
            tid = row['tid']
            share = row['share']
            inp = all_teams[tid]['inputs_next']
            prev_bal = all_teams[tid]['balance_sheet'] # งบดุลปีก่อน
            
            # --- INCOME STATEMENT ---
            sales = share * market_size
            cogs = sales / (1 + (inp[0]/100))
            gross_margin = sales - cogs
            
            rent_exp = sales * LOC_CONFIG[loc_id]['rent']
            wages = (inp[16]*inp[17] + inp[18]*inp[19]) * inp[6] * WEEKS
            fixed = inp[20] + inp[7] + 3000
            depr = 50000 * 0.025
            
            # Interest
            inv_income = inp[9] * 0.02
            interest_exp = 0
            
            # --- CASH FLOW LOGIC ---
            cash_begin = prev_bal['cash']
            purchases = inp[14] + inp[15]
            pay_ap = inp[28]
            
            cash_in = sales * 0.9 + inv_income
            cash_out = wages + rent_exp + fixed + pay_ap + purchases
            
            cash_end = cash_begin + cash_in - cash_out
            
            emergency_loan = 0
            if cash_end < 0:
                emergency_loan = abs(cash_end) + 2000
                interest_exp += emergency_loan * EMERGENCY_LOAN_RATE # Penalty
                cash_end += emergency_loan
                
            # Special Penalty 999999
            if pay_ap > 200000: interest_exp += 29000000
            
            net_profit = (gross_margin - (wages + rent_exp + fixed + depr)) + inv_income - interest_exp
            
            # --- UPDATE BALANCE SHEET ---
            inventory = prev_bal['inventory'] + purchases - cogs
            ar = prev_bal['ar'] + (sales * 0.1)
            ap = prev_bal['ap'] + purchases - pay_ap
            
            retained_earnings = prev_bal['retained_earnings'] + net_profit
            
            new_bal = {
                'cash': cash_end,
                'inventory': inventory,
                'ar': ar,
                'fixed_assets': prev_bal['fixed_assets'] - depr,
                'ap': ap,
                'emergency_loan': emergency_loan,
                'long_term_debt': 100000,
                'retained_earnings': retained_earnings
            }
            
            # Save History
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
            
            # Update Current State for Next Round
            all_teams[tid]['balance_sheet'] = new_bal
            # Reset Inputs for next round (copy old ones as default)
            all_teams[tid]['inputs_prev'] = inp.copy()
            all_teams[tid]['submitted'] = False

    st.session_state.current_period += 1

# ==========================================
# 3. INSTRUCTOR VIEW (ผู้คุมเกม)
# ==========================================
def instructor_view():
    st.header("👨‍🏫 Instructor Dashboard (ผู้คุมเกม)")
    
    if st.session_state.game_state == "SETUP":
        st.subheader("1. Setup Period 1 (เริ่มเกม)")
        st.info("กำหนดจำนวนร้านและสร้างข้อมูลเริ่มต้นสำหรับ Period 1")
        
        num_teams = st.number_input("จำนวนทีม (Stores)", 1, 10, 3)
        if st.button("Initialize Game & Run Period 1"):
            # Create Default Teams
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
                    'submitted': True # P1 auto-submitted
                }
            
            # Run Period 1 Calculation immediately
            run_period_processing()
            st.session_state.game_state = "ACTIVE"
            st.rerun()
            
    else: # GAME ACTIVE
        period = st.session_state.current_period
        st.subheader(f"Current Status: Period {period}")
        st.markdown("---")
        
        # Monitor Student Submission
        st.write("### 📡 สถานะการส่งงานของนักเรียน")
        status_data = []
        ready_to_run = True
        for tid, data in st.session_state.teams.items():
            status = "✅ Submitted" if data['submitted'] else "⏳ Waiting..."
            if not data['submitted']: ready_to_run = False
            status_data.append({"Team": tid, "Location": LOC_CONFIG[data['loc']]['name'], "Status": status})
        st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        
        # Control Panel
        st.markdown("### ⚙️ Game Control")
        if ready_to_run:
            st.success("ทุกทีมส่งข้อมูลครบแล้ว สามารถรันผลลัพธ์ได้เลย")
        else:
            st.warning("บางทีมยังไม่ส่งข้อมูล (กด Run เพื่อบังคับประมวลผลได้)")
            
        if st.button(f"🚀 Run Simulation (Process Period {period})", type="primary"):
            run_period_processing()
            st.success("Processing Complete! Students can now view results.")
            st.rerun()

        # View Master Report
        st.markdown("---")
        st.write("### 🏆 Master Report (ผลประกอบการรวม)")
        if st.checkbox("Show All Teams Financials"):
            # Combine history logic here
            pass

# ==========================================
# 4. STUDENT VIEW (ผู้เล่น)
# ==========================================
def student_view():
    st.header("💊 Student Portal (ผู้เล่น)")
    
    # Login
    team_list = list(st.session_state.teams.keys())
    if not team_list:
        st.error("Instructor ยังไม่ได้เริ่มเกม")
        return

    my_team = st.selectbox("เลือกทีมของคุณ (Select Your Store)", team_list)
    team_data = st.session_state.teams[my_team]
    current_period = st.session_state.current_period
    
    st.caption(f"Location: {LOC_CONFIG[team_data['loc']]['name']} | Status: {'✅ ส่งข้อมูลแล้ว' if team_data['submitted'] else '✍️ รอการตัดสินใจ'}")

    # Tabs: Report (อดีต) vs Decisions (อนาคต)
    tab1, tab2 = st.tabs([f"📊 ผลประกอบการ (Period {current_period-1})", f"📝 ตัดสินใจ (For Period {current_period})"])
    
    with tab1:
        # ดึงข้อมูล History ล่าสุด
        if my_team in st.session_state.history and st.session_state.history[my_team]:
            last_result = st.session_state.history[my_team][-1]
            inc = last_result['income_statement']
            bs = last_result['balance_sheet']
            rat = last_result['ratios']
            
            st.markdown(f"### 📄 รายงานผลรอบที่ {last_result['period']}")
            
            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Net Profit", f"${inc['Net Profit']:,.0f}")
            c2.metric("Cash Balance", f"${bs['cash']:,.0f}")
            c3.metric("Current Ratio", f"{rat['Current Ratio']:.2f}")
            
            # Full Report
            with st.expander("ดูงบการเงินฉบับเต็ม (Full Financial Statements)", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.caption("Income Statement")
                    st.dataframe(pd.DataFrame(inc.items(), columns=["Item", "Amount"]), hide_index=True)
                with col_b:
                    st.caption("Balance Sheet")
                    st.dataframe(pd.DataFrame(bs.items(), columns=["Item", "Amount"]), hide_index=True)
        else:
            st.info("รอผลการรันรอบแรกจาก Instructor")

    with tab2:
        st.markdown(f"### ✍️ แบบฟอร์มตัดสินใจ (Period {current_period})")
        
        if team_data['submitted']:
            st.success("คุณได้ส่งข้อมูลของรอบนี้เรียบร้อยแล้ว กรุณารอ Instructor ประมวลผล")
        else:
            with st.form("decision_form"):
                st.info("กรุณากรอกข้อมูลเพื่อใช้ในการแข่งขันรอบถัดไป")
                
                # Load previous inputs as default
                defaults = team_data['inputs_prev']
                new_inputs = defaults.copy()
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**การตลาด & ราคา**")
                    new_inputs[0] = st.number_input("1. Rx Markup (%)", value=defaults[0])
                    new_inputs[7] = st.number_input("8. Promo Budget ($)", value=defaults[7])
                    new_inputs[6] = st.number_input("7. Hours/Week", value=defaults[6])
                
                with c2:
                    st.markdown("**การสั่งซื้อ & การเงิน**")
                    new_inputs[14] = st.number_input("15. Rx Purchase ($)", value=defaults[14])
                    new_inputs[15] = st.number_input("16. Other Purchase ($)", value=defaults[15])
                    new_inputs[28] = st.number_input("29. Pay A/P (จ่ายหนี้) ($)", value=0, help="ใส่ 0 ถ้าไม่อยากจ่าย, อย่าใส่เกินเงินที่มี")

                submitted = st.form_submit_button("Submit Decisions")
                if submitted:
                    # Save to central state
                    st.session_state.teams[my_team]['inputs_next'] = new_inputs
                    st.session_state.teams[my_team]['submitted'] = True
                    st.success("ส่งข้อมูลสำเร็จ! รอ Instructor รันผลลัพธ์")
                    st.rerun()

# ==========================================
# 5. MAIN APP ROUTER
# ==========================================
role = st.sidebar.radio("เลือกบทบาท (Role)", ["Student (ผู้เล่น)", "Instructor (ผู้สอน)"])

if role == "Instructor (ผู้สอน)":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == "admin":
        instructor_view()
    else:
        st.sidebar.warning("Incorrect Password (Hint: admin)")
else:
    if st.session_state.game_state == "SETUP":
        st.title("⏳ Waiting for Instructor...")
        st.info("กรุณารอให้อาจารย์ตั้งค่าเกมและรัน Period 1 ให้เสร็จสิ้นก่อน")
    else:
        student_view()
