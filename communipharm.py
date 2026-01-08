import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. การตั้งค่าระบบและตัวแปรคงที่ (Config)
# ==========================================
st.set_page_config(page_title="Thai Pharmacy Sim (Pro)", layout="wide")

# ค่าเฉลี่ยตลาด (Market Averages) เพื่อใช้เปรียบเทียบ
MARKET_AVG = {
    'rx_fee': 120,          # ค่าวิชาชีพ/บริการต่อเคส
    'rx_markup': 20,        # % กำไรยา
    'other_markup': 40,     # % กำไรสินค้าหน้าร้าน
    'wage_pharm': 250,      # ค่าแรงเภสัช/ชม.
    'wage_clerk': 60,       # ค่าแรงผู้ช่วย/ชม.
    'base_traffic': 1000,   # จำนวนลูกค้าเข้าร้านพื้นฐาน
}

# เริ่มต้นตัวแปร (Session State)
if 'turn' not in st.session_state:
    st.session_state.turn = 1
    st.session_state.max_turn = 8 # เล่นได้ 7 รอบ (เริ่มรอบ 2-8 ตามต้นฉบับ)
    st.session_state.game_over = False
    
    # สถานะการเงินเริ่มต้น (Balance Sheet Init)
    st.session_state.financials = {
        'cash': 800000,             # เงินสด
        'inventory_rx': 200000,     # มูลค่าสต็อกยา
        'inventory_other': 300000,  # มูลค่าสต็อกหน้าร้าน
        'loans': 0                  # หนี้สิน
    }
    
    # เก็บประวัติเพื่อทำกราฟ
    st.session_state.history_reports = []

# ==========================================
# 2. Logic การคำนวณ (Simulation Engine) 🧠
# ==========================================
def run_simulation(inputs):
    fin = st.session_state.financials
    
    # --- A. คำนวณปัจจัย (Factors) ---
    
    # 1. Price Factor (ราคาเทียบกับตลาด)
    # ราคายา = ทุน + Markup + Fee
    # ยิ่งแพง ลูกค้ายิ่งหนี (Elasticity)
    price_score_rx = 1.0 - ((inputs['rx_markup'] - MARKET_AVG['rx_markup'])/100) 
    price_score_other = 1.0 - ((inputs['other_markup'] - MARKET_AVG['other_markup'])/50)
    
    # 2. Service Factor (คุณภาพบริการ)
    # มาจาก: เวลาเปิดร้าน + ค่าจ้าง (จ้างแพง=บริการดี) + บริการเสริม
    service_score = 0
    if inputs['delivery']: service_score += 0.1
    if inputs['patient_record']: service_score += 0.15
    if inputs['credit']: service_score += 0.05
    
    # Wage incentive (ถ้าจ้างแพงกว่าตลาด พนักงานจะขยัน)
    wage_factor = (inputs['wage_pharm'] / MARKET_AVG['wage_pharm']) * 0.5 + \
                  (inputs['wage_clerk'] / MARKET_AVG['wage_clerk']) * 0.5
    service_score *= wage_factor

    # 3. Marketing Factor (การตลาด)
    # ใช้ Log function (เงินช่วงแรกเห็นผลเยอะ ใส่เยอะมากๆ ผลเริ่มนิ่ง)
    marketing_impact = np.log1p(inputs['promo_budget']) / 10  # log1p คือ log(x+1)
    
    # --- B. คำนวณยอดขาย (Demand & Sales) ---
    
    # 1. Rx Sales (ยาใบสั่ง/ยาอันตราย) - เน้นความเชื่อถือ (Service)
    # สูตร: Base * Service * (Marketing นิดหน่อย)
    potential_rx_cust = MARKET_AVG['base_traffic'] * 0.3 * (1 + service_score) * (1 + marketing_impact*0.2)
    # เช็คว่ามีของขายไหม (Inventory Constraint)
    # สมมติทุนเฉลี่ยต่อหน่วย Rx = 500 บาท
    max_rx_sales_units = fin['inventory_rx'] / 500
    actual_rx_units = min(potential_rx_cust, max_rx_sales_units)
    
    # คำนวณรายได้ Rx
    # ราคาขายเฉลี่ย = 500 * (1+Markup) + Fee
    avg_price_rx = 500 * (1 + inputs['rx_markup']/100) + inputs['rx_fee']
    revenue_rx = actual_rx_units * avg_price_rx
    cogs_rx = actual_rx_units * 500 # ต้นทุนขาย
    
    # 2. Other Sales (OTC/ของหน้าร้าน) - เน้นราคาและการโฆษณา
    # สูตร: Base * PriceFactor * Marketing
    potential_other_cust = MARKET_AVG['base_traffic'] * 0.7 * price_score_other * (1 + marketing_impact)
    # เช็คของ
    # สมมติทุนเฉลี่ยต่อหน่วย Other = 100 บาท
    max_other_sales_units = fin['inventory_other'] / 100
    actual_other_units = min(potential_other_cust, max_other_sales_units)
    
    # คำนวณรายได้ Other
    avg_price_other = 100 * (1 + inputs['other_markup']/100)
    revenue_other = actual_other_units * avg_price_other
    cogs_other = actual_other_units * 100
    
    # --- C. คำนวณค่าใช้จ่าย (Expenses) ---
    
    total_hours_pharm = inputs['num_pharm'] * 160 # 4 weeks * 40 hrs
    total_hours_clerk = inputs['num_clerk'] * 160
    
    cost_wages = (total_hours_pharm * inputs['wage_pharm']) + \
                 (total_hours_clerk * inputs['wage_clerk'])
                 
    fixed_cost = 25000 # ค่าเช่า + น้ำไฟ
    delivery_cost = 5000 if inputs['delivery'] else 0
    
    total_expenses = cost_wages + inputs['promo_budget'] + fixed_cost + delivery_cost
    
    # --- D. สรุปผลลัพธ์ (Financial Closing) ---
    
    gross_margin = (revenue_rx + revenue_other) - (cogs_rx + cogs_other)
    net_profit = gross_margin - total_expenses
    
    # อัปเดตงบดุล (Balance Sheet Update)
    # เงินสดรับ = ยอดขาย - ซื้อของเติมสต็อก - จ่ายค่าใช้จ่าย
    cash_flow = (revenue_rx + revenue_other) - inputs['buy_rx'] - inputs['buy_other'] - total_expenses
    
    fin['cash'] += cash_flow
    fin['inventory_rx'] = fin['inventory_rx'] - cogs_rx + inputs['buy_rx']
    fin['inventory_other'] = fin['inventory_other'] - cogs_other + inputs['buy_other']
    
    # บันทึกข้อมูล
    report = {
        "Period": st.session_state.turn,
        "Total Sales": revenue_rx + revenue_other,
        "Rx Sales": revenue_rx,
        "Other Sales": revenue_other,
        "COGS": cogs_rx + cogs_other,
        "Gross Profit": gross_margin,
        "Expenses": total_expenses,
        "Net Profit": net_profit,
        "Cash End": fin['cash']
    }
    st.session_state.history_reports.append(report)
    st.session_state.turn += 1

# ==========================================
# 3. User Interface (UI)
# ==========================================

# Header
st.title(f"🏥 Professional Pharmacy Simulation - Period {st.session_state.turn}/7")

# เช็คจบเกม
if st.session_state.turn > 7:
    st.success("🎉 จบการจำลองสถานการณ์แล้ว! นี่คือผลประกอบการของคุณ")
    st.dataframe(pd.DataFrame(st.session_state.history_reports).set_index("Period"))
    if st.button("เริ่มเกมใหม่"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# Layout แบ่ง 2 คอลัมน์ (ซ้าย=Input, ขวา=Report)
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.info(f"💰 เงินสดในมือ: {st.session_state.financials['cash']:,.0f} บาท")
    
    with st.form("decision_form"):
        st.header("📝 แบบฟอร์มการตัดสินใจ")
        
        # ใช้ Tabs แบ่งหมวดหมู่ให้เหมือน GameForms.pdf
        tab1, tab2, tab3, tab4 = st.tabs(["💵 การตั้งราคา", "📢 การตลาด", "📦 การสั่งซื้อ", "👥 บุคลากร"])
        
        with tab1: # Pricing Strategy
            st.subheader("1. นโยบายราคา (Pricing)")
            in_rx_markup = st.number_input("Rx: % กำไร (Markup %)", 0, 100, 20)
            in_rx_fee = st.number_input("Rx: ค่าวิชาชีพ (Professional Fee)", 0, 500, 120)
            in_other_markup = st.number_input("Other: % กำไร (Markup %)", 0, 100, 40)
            st.caption("*Markup สินค้าหน้าร้านทั่วไป")

        with tab2: # Marketing & Service
            st.subheader("2. การตลาดและบริการ")
            in_promo = st.number_input("งบโฆษณา (บาท)", 0, 100000, 5000)
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                in_delivery = st.checkbox("บริการส่งยา (Delivery)")
                in_records = st.checkbox("ทำประวัติคนไข้ (Patient Records)")
            with col_m2:
                in_credit = st.checkbox("ให้เครดิตการค้า (Credit)")
            
            in_open_hours = st.slider("เวลาเปิดร้าน (ชม./สัปดาห์)", 40, 100, 60)

        with tab3: # Purchasing
            st.subheader("3. การเติมสต็อก (Purchasing)")
            st.write(f"Rx คงเหลือ: {st.session_state.financials['inventory_rx']:,.0f}")
            in_buy_rx = st.number_input("ซื้อยา Rx เพิ่ม (บาท)", 0, 1000000, 100000)
            
            st.write(f"หน้าร้าน คงเหลือ: {st.session_state.financials['inventory_other']:,.0f}")
            in_buy_other = st.number_input("ซื้อของหน้าร้านเพิ่ม (บาท)", 0, 1000000, 150000)

        with tab4: # Personnel
            st.subheader("4. บุคลากร (Personnel)")
            c1, c2 = st.columns(2)
            with c1:
                in_n_pharm = st.number_input("จำนวนเภสัชกร", 1, 5, 1)
                in_w_pharm = st.number_input("ค่าแรงเภสัช (บาท/ชม.)", 150, 500, 250)
            with c2:
                in_n_clerk = st.number_input("จำนวนผู้ช่วย", 0, 5, 2)
                in_w_clerk = st.number_input("ค่าแรงผู้ช่วย (บาท/ชม.)", 40, 150, 60)
            
            # คำนวณ Coverage ให้ดูสดๆ
            total_man_hours = (in_n_pharm + in_n_clerk) * 40
            req_hours = in_open_hours
            if total_man_hours < req_hours:
                st.warning(f"⚠️ คนไม่พอ! ต้องการ {req_hours} ชม. แต่มีแค่ {total_man_hours} ชม.")

        # Submit Button
        submitted = st.form_submit_button("✅ ส่งผลการตัดสินใจ (Run Period)", type="primary")
        
        if submitted:
            # แพ็คข้อมูลเป็น Dictionary
            inputs = {
                'rx_markup': in_rx_markup,
                'rx_fee': in_rx_fee,
                'other_markup': in_other_markup,
                'promo_budget': in_promo,
                'delivery': in_delivery,
                'patient_record': in_records,
                'credit': in_credit,
                'open_hours': in_open_hours,
                'buy_rx': in_buy_rx,
                'buy_other': in_buy_other,
                'num_pharm': in_n_pharm,
                'wage_pharm': in_w_pharm,
                'num_clerk': in_n_clerk,
                'wage_clerk': in_w_clerk
            }
            run_simulation(inputs)
            st.rerun()

with right_col:
    # แสดงผลลัพธ์ (Output Dashboard)
    if len(st.session_state.history_reports) > 0:
        last_report = st.session_state.history_reports[-1]
        
        st.subheader("📊 ผลประกอบการรอบล่าสุด")
        
        # 1. Income Statement (งบกำไรขาดทุน)
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px;">
            <h4>งบกำไรขาดทุน (Income Statement)</h4>
            <p>ยอดขายรวม: <b>{last_report['Total Sales']:,.2f}</b></p>
            <ul>
                <li>ยอดขาย Rx: {last_report['Rx Sales']:,.2f}</li>
                <li>ยอดขายหน้าร้าน: {last_report['Other Sales']:,.2f}</li>
            </ul>
            <p style="color:red;">หัก ต้นทุนขาย (COGS): -{last_report['COGS']:,.2f}</p>
            <hr>
            <p><b>กำไรขั้นต้น (Gross Profit): {last_report['Gross Profit']:,.2f}</b></p>
            <p style="color:red;">หัก ค่าใช้จ่ายดำเนินงาน: -{last_report['Expenses']:,.2f}</p>
            <hr>
            <h3>กำไรสุทธิ (Net Profit): <span style="color:{'green' if last_report['Net Profit']>0 else 'red'}">{last_report['Net Profit']:,.2f}</span></h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Trend Graph
        st.write("---")
        st.subheader("📈 แนวโน้มกำไรสะสม")
        df_hist = pd.DataFrame(st.session_state.history_reports)
        st.line_chart(df_hist.set_index("Period")[['Net Profit', 'Total Sales']])
        
    else:
        st.info("👈 กรุณากรอกข้อมูลทางซ้ายมือ แล้วกดปุ่ม 'ส่งผลการตัดสินใจ' เพื่อเริ่มเล่นรอบที่ 1")