import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config & State Init
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Classroom Edition)", layout="wide")

# กำหนดค่าเริ่มต้น (Default Market Parameters) เผื่ออาจารย์ยังไม่ได้ตั้ง
DEFAULT_PARAMS = {
    'base_traffic': 1200,      # ลูกค้าเข้าร้านเฉลี่ย/เดือน
    'mkt_rx_fee': 4.0,         # ค่าวิชาชีพมาตรฐาน ($)
    'mkt_wage_pharm': 22.0,    # ค่าแรงเภสัชตลาด ($/hr)
    'mkt_wage_clerk': 6.50,    # ค่าแรงผู้ช่วยตลาด ($/hr)
    'rent': 2000,              # ค่าเช่า ($)
    'owner_salary': 3000,      # เงินเดือนเจ้าของ ($)
    'tax_rate': 30,            # ภาษีเงินได้ (%)
    'interest_rate': 12        # ดอกเบี้ยเงินกู้ (%)
}

# โหลดค่า Market Params เข้า Session (ถ้ายังไม่มี)
if 'market_params' not in st.session_state:
    st.session_state.market_params = DEFAULT_PARAMS.copy()

if 'period' not in st.session_state:
    st.session_state.period = 2
    st.session_state.history = []
    st.session_state.financials = {
        'cash': 40000.0,
        'inv_rx': 25000.0,
        'inv_otc': 40000.0,
        'loans': 0.0
    }

# ==========================================
# 2. Logic Engine (เชื่อมโยงกับค่าที่ครูตั้ง) 🧠
# ==========================================
def run_period(decisions):
    fin = st.session_state.financials
    mkt = st.session_state.market_params # ดึงค่าที่ครูตั้งมาใช้
    
    # --- A. Demand Calculation ---
    # 1. Price Factor: เทียบกับราคาตลาดที่ครูตั้ง (mkt_rx_fee)
    price_sensitivity = 1.0 - ((decisions['rx_fee'] - mkt['mkt_rx_fee']) / 10.0)
    
    # 2. Service Factor
    service_score = 1.0
    if decisions['delivery']: service_score += 0.05
    if decisions['records']: service_score += 0.10
    
    # 3. Personnel Factor: เทียบกับค่าแรงตลาดที่ครูตั้ง
    wage_quality_pharm = decisions['wage_pharm'] / mkt['mkt_wage_pharm']
    wage_quality_clerk = decisions['wage_clerk'] / mkt['mkt_wage_clerk']
    staff_quality = (wage_quality_pharm + wage_quality_clerk) / 2
    
    # คำนวณ Traffic จริง (Base Traffic จากครู * ปัจจัยต่างๆ)
    actual_traffic = mkt['base_traffic'] * price_sensitivity * service_score * staff_quality
    
    # --- B. Sales Logic ---
    rx_cust = actual_traffic * 0.3
    rx_revenue = (rx_cust * 20) * (1 + decisions['rx_markup']/100) + (rx_cust * decisions['rx_fee'])
    cogs_rx = rx_cust * 20
    
    otc_cust = actual_traffic * 0.7
    otc_revenue = (otc_cust * 10) * (1 + decisions['otc_markup']/100)
    cogs_otc = otc_cust * 10
    
    # --- C. Expenses Logic ---
    # ค่าใช้จ่ายคงที่ ดึงมาจากที่ครูตั้ง
    total_wages = (decisions['n_pharm']*160*decisions['wage_pharm']) + \
                  (decisions['n_clerk']*160*decisions['wage_clerk'])
    
    expenses = mkt['owner_salary'] + mkt['rent'] + total_wages + decisions['ads_budget'] + 500
    
    # --- D. Profit & Closing ---
    gross_margin = (rx_revenue + otc_revenue) - (cogs_rx + cogs_otc)
    net_profit_before_tax = gross_margin - expenses
    
    # หักภาษี (ตามอัตราที่ครูตั้ง)
    tax = net_profit_before_tax * (mkt['tax_rate']/100) if net_profit_before_tax > 0 else 0
    net_profit = net_profit_before_tax - tax
    
    # Update Cash
    fin['cash'] += (rx_revenue + otc_revenue) - (decisions['buy_rx'] + decisions['buy_otc'] + expenses + tax)
    fin['inv_rx'] += decisions['buy_rx'] - cogs_rx
    fin['inv_otc'] += decisions['buy_otc'] - cogs_otc
    
    # Save Log
    st.session_state.history.append({
        "Period": st.session_state.period,
        "Total Sales": rx_revenue + otc_revenue,
        "Net Profit": net_profit,
        "Cash": fin['cash'],
        "Mkt Traffic Used": mkt['base_traffic'] # บันทึกไว้ดูว่าตอนนั้นครูตั้งค่าเท่าไหร่
    })
    st.session_state.period += 1

# ==========================================
# 3. Sidebar (Login System)
# ==========================================
with st.sidebar:
    st.header("🔐 Access Control")
    user_role = st.radio("เลือกโหมดการใช้งาน:", ["Student (นักเรียน)", "Instructor (อาจารย์)"])
    
    is_admin = False
    if user_role == "Instructor (อาจารย์)":
        password = st.text_input("Admin Password:", type="password")
        if password == "admin":  # <--- รหัสผ่านคือ admin
            is_admin = True
            st.success("Access Granted ✅")
        elif password:
            st.error("Wrong Password ❌")
    
    st.divider()
    if st.button("Reset Game (เริ่มใหม่)"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 4. Main Content (Switch Views)
# ==========================================

if is_admin:
    # ----------------------------------
    # 👨‍🏫 VIEW: INSTRUCTOR PANEL
    # ----------------------------------
    st.title("👨‍🏫 Instructor Configuration Panel")
    st.warning("⚠️ การเปลี่ยนค่าตรงนี้ จะมีผลต่อการคำนวณของนักเรียนทันที")
    
    with st.form("admin_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. สภาพตลาด (Market Conditions)")
            new_traffic = st.number_input("Base Traffic (ลูกค้าพื้นฐาน/เดือน)", 500, 5000, st.session_state.market_params['base_traffic'])
            new_rx_fee = st.number_input("Market Rx Fee ($)", 0.0, 20.0, st.session_state.market_params['mkt_rx_fee'])
            
            st.subheader("2. ค่าแรงมาตรฐาน (Market Wages)")
            new_w_pharm = st.number_input("Avg. Pharm Wage ($/hr)", 10.0, 100.0, st.session_state.market_params['mkt_wage_pharm'])
            new_w_clerk = st.number_input("Avg. Clerk Wage ($/hr)", 1.0, 50.0, st.session_state.market_params['mkt_wage_clerk'])

        with col2:
            st.subheader("3. ค่าใช้จ่ายคงที่ (Fixed Costs)")
            new_rent = st.number_input("Monthly Rent ($)", 0, 10000, st.session_state.market_params['rent'])
            new_salary = st.number_input("Owner's Salary ($)", 0, 20000, st.session_state.market_params['owner_salary'])
            
            st.subheader("4. เศรษฐศาสตร์ (Economics)")
            new_tax = st.number_input("Corporate Tax Rate (%)", 0, 50, st.session_state.market_params['tax_rate'])
            new_interest = st.number_input("Interest Rate (%)", 0, 30, st.session_state.market_params['interest_rate'])
            
        if st.form_submit_button("💾 Save Configuration"):
            st.session_state.market_params.update({
                'base_traffic': new_traffic, 'mkt_rx_fee': new_rx_fee,
                'mkt_wage_pharm': new_w_pharm, 'mkt_wage_clerk': new_w_clerk,
                'rent': new_rent, 'owner_salary': new_salary,
                'tax_rate': new_tax, 'interest_rate': new_interest
            })
            st.success("บันทึกค่าตัวแปรระบบเรียบร้อยแล้ว!")
            st.json(st.session_state.market_params)

else:
    # ----------------------------------
    # 🎓 VIEW: STUDENT (GAMEPLAY)
    # ----------------------------------
    st.title(f"🏥 Communi-Pharm: Period {st.session_state.period}")
    
    # แสดงสถานะปัจจุบัน (Inventory / Cash)
    fin = st.session_state.financials
    c1, c2, c3 = st.columns(3)
    c1.metric("Cash (เงินสด)", f"${fin['cash']:,.2f}")
    c2.metric("Rx Inventory", f"${fin['inv_rx']:,.2f}")
    c3.metric("OTC Inventory", f"${fin['inv_otc']:,.2f}")
    
    # Form การตัดสินใจ (Decision Form)
    with st.form("student_decision"):
        st.header("📝 แบบฟอร์มตัดสินใจ")
        
        col_A, col_B = st.columns(2)
        with col_A:
            st.subheader("Pricing & Promo")
            in_rx_markup = st.number_input("Rx Markup (%)", 0.0, 100.0, 25.0)
            in_rx_fee = st.number_input("Rx Fee ($)", 0.0, 20.0, 4.0)
            in_otc_markup = st.number_input("OTC Markup (%)", 0.0, 100.0, 50.0)
            in_ads = st.number_input("Ad Budget ($)", 0, 20000, 500)
            
        with col_B:
            st.subheader("Operations & Staff")
            in_n_pharm = st.number_input("# Pharmacists", 1, 10, 1)
            in_wage_pharm = st.number_input("Pharm Wage ($/hr)", 10.0, 60.0, 22.0)
            in_n_clerk = st.number_input("# Clerks", 0, 10, 2)
            in_wage_clerk = st.number_input("Clerk Wage ($/hr)", 4.0, 20.0, 6.5)
            
        st.subheader("Purchasing (ซื้อของเติม)")
        c_buy1, c_buy2 = st.columns(2)
        in_buy_rx = c_buy1.number_input("Buy Rx ($)", 0, 100000, 15000)
        in_buy_otc = c_buy2.number_input("Buy OTC ($)", 0, 100000, 20000)
        
        # Hidden inputs for simplified demo
        in_del, in_rec = False, False
        
        if st.form_submit_button("🚀 Submit Decisions"):
            decisions = {
                'rx_markup': in_rx_markup, 'rx_fee': in_rx_fee, 'otc_markup': in_otc_markup,
                'ads_budget': in_ads, 'delivery': in_del, 'records': in_rec,
                'n_pharm': in_n_pharm, 'wage_pharm': in_wage_pharm,
                'n_clerk': in_n_clerk, 'wage_clerk': in_wage_clerk,
                'buy_rx': in_buy_rx, 'buy_otc': in_buy_otc
            }
            run_period(decisions)
            st.rerun()

    # History Report
    if st.session_state.history:
        st.divider()
        st.subheader("📊 ผลประกอบการย้อนหลัง")
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df.style.format({"Total Sales": "${:,.2f}", "Net Profit": "${:,.2f}", "Cash": "${:,.2f}"}))
