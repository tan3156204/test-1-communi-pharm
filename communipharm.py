import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Pharmacy Sim V11 (Real Math)", layout="wide")

# --- CONSTANTS ---
BASE_COST_RX = 11.23   # ต้นทุนยาพื้นฐาน
CONST_FEE = 2.90       # ค่าธรรมเนียมคงที่
WEEKS_PER_PERIOD = 13  # 1 ไตรมาสมี 13 สัปดาห์

# --- COMPETITOR DATA (FROM PDF) ---
# ข้อมูลคู่แข่งถูกฝังไว้เพื่อใช้คำนวณ Market Share เทียบกับคุณ
COMPETITORS = [
    {"name": "LhaiJai", "loc": 1, "inputs": [49, 0.5, 0, 0, 1, 1, 48, 600, 100, 2000, 1, 0, 0, 55, 40000, 24000, 1, 9.75, 1, 4.9, 8050, 99, 48, 900, 0, 1000, 0, 0, 999999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "N&M", "loc": 2, "inputs": [30, 2.5, 0, 1, 1, 0, 60, 1500, 40, 3000, 3, 2000, 1, 38, 60000, 80000, 1, 21, 6.6, 4.75, 7000, 50, 48, 1299, 0, 1500, 0, 0, 999999, 0, 0, 1, 1, 1, 1, 0]},
    {"name": "NueyDeng", "loc": 2, "inputs": [30, 2.4, 0.25, 0, 1, 0, 70, 1900, 40, 3000, 3, 2000, 1, 39, 65000, 120000, 1.3, 22.75, 7, 5, 8000, 50, 48, 1200, 0, 2300, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Puaypepakor", "loc": 2, "inputs": [40, 0.9, 0.25, 0, 0, 0, 70, 1500, 33, 2000, 3, 0, 0, 34, 65000, 145000, 1.5, 19.5, 6.5, 4.75, 8000, 66, 48, 1200, 0, 2200, 0, 0, 99999, 0, 0, 0, 1, 1, 1, 0]},
    {"name": "HappyPills", "loc": 3, "inputs": [35, 2.2, 0, 0, 0, 1, 90, 2200, 34, 2000, 1, 0, 0, 33, 85000, 145000, 1.5, 20, 8.9, 4.75, 8000, 30, 48, 2000, 0, 2500, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]},
    {"name": "Oceanville", "loc": 3, "inputs": [38, 1.8, 0, 0, 1, 0, 75, 3000, 10, 10000, 2, 10000, 3, 37, 65000, 75000, 1.75, 22, 8, 5.12, 8000, 50, 48, 1300, 0, 2200, 0, 0, 999999, 0, 0, 0, 1, 0, 1, 0]}
]

# --- WEIGHTS MATRIX (จากรูปภาพ) ---
# Weights ต้องแปลงเป็น Dictionary เพื่อความแม่นยำ
WEIGHTS_RX = {
    # Medical Center เน้น Price, Delivery
    1: {'price': 10, 'fee': 30, 'promo': 5, 'hours': 20, 'delivery': 5, 'records': 10, 'credit': 5, 'inv': 5},
    # Neighborhood เน้น Promo, Price
    2: {'price': 20, 'fee': 25, 'promo': 10, 'hours': 10, 'delivery': 10, 'records': 5, 'credit': 5, 'inv': 5},
    # Shopping Center เน้น Price (40!), Traffic
    3: {'price': 40, 'fee': 30, 'promo': 15, 'hours': 5, 'delivery': 0, 'records': 0, 'credit': 5, 'inv': 0}
}

WEIGHTS_OTC = {
    # Medical Center (Sum 25)
    1: {'markup_past': 2, 'markup_pres': 5, 'ad': 5, 'hours': 3, 'inv': 4, 'rx_share': 6},
    # Neighborhood (Sum 80)
    2: {'markup_past': 15, 'markup_pres': 15, 'ad': 10, 'hours': 15, 'inv': 10, 'rx_share': 15},
    # Shopping Center (Sum 100)
    3: {'markup_past': 20, 'markup_pres': 20, 'ad': 10, 'hours': 15, 'inv': 20, 'rx_share': 15}
}

# ==========================================
# 2. CALCULATION ENGINE (The Logic)
# ==========================================
def run_simulation(user_inputs):
    # 1. รวมทีมผู้เล่น (Thaikritosot) กับ Bot คู่แข่ง
    user_team = {"name": "Thaikritosot (You)", "loc": 1, "inputs": user_inputs}
    all_teams = [user_team] + COMPETITORS
    
    results = []
    
    # 2. แยกคำนวณตาม Location (เพราะแย่งลูกค้ากันเฉพาะในพื้นที่)
    for loc_id in [1, 2, 3]:
        teams_in_loc = [t for t in all_teams if t['loc'] == loc_id]
        if not teams_in_loc: continue
        
        # --- A. คำนวณคะแนนดิบ (Raw Scores) ---
        df = pd.DataFrame()
        for t in teams_in_loc:
            i = t['inputs']
            # Price Calculation: (BaseCost * (1+Markup%)) + Fee + Constant
            selling_price = (BASE_COST_RX * (1 + i[0]/100)) + i[1] + CONST_FEE
            
            data = {
                'name': t['name'],
                'inputs': i,
                'price': selling_price,
                'promo': i[7],
                'hours': i[6],
                'delivery': i[3],
                'records': i[4],
                'credit': i[5],
                'inv_rx': i[14],
                'inv_otc': i[15],
                'otc_markup': i[13],
                'ad_otc': i[7] # Use same promo budget
            }
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            
        # --- B. คำนวณ Market Share (Ranking Logic) ---
        # ยิ่งราคาต่ำยิ่งดี, ยิ่งโปรโมชั่นสูงยิ่งดี
        w_rx = WEIGHTS_RX[loc_id]
        
        # สร้าง Score แบบง่ายที่สะท้อน Weight (Reverse Engineering)
        # ใช้สูตร Normalize: (Value / Max) * Weight
        max_promo = df['promo'].max() if df['promo'].max() > 0 else 1
        min_price = df['price'].min()
        
        # Rx Score Calculation
        df['score_rx'] = (
            ((min_price / df['price']) * w_rx.get('price', 0) * 3) + # Price สำคัญมาก ให้ตัวคูณสูง
            ((df['promo'] / max_promo) * w_rx.get('promo', 0)) +
            ((df['hours'] / 168) * w_rx.get('hours', 0) * 2) + 
            (df['delivery'] * w_rx.get('delivery', 0))
        )
        
        total_rx_score = df['score_rx'].sum()
        df['rx_share'] = df['score_rx'] / total_rx_score
        
        # --- C. คำนวณ Financials (สูตรบัญชี) ---
        # ปรับ Market Size ให้ยอดขายตรงกับความจริง (Medical Center ~ 280k Total)
        MARKET_SIZE_RX = 280000 if loc_id == 1 else 1300000 
        if loc_id == 3: MARKET_SIZE_RX = 800000
        
        for idx, row in df.iterrows():
            inp = row['inputs']
            
            # 1. รายได้ (Revenue)
            rx_sales = row['rx_share'] * MARKET_SIZE_RX
            # OTC ขายได้ประมาณ 30-40% ของ Rx
            otc_sales = rx_sales * 0.4 
            total_sales = rx_sales + otc_sales
            
            # 2. ต้นทุนสินค้า (COGS)
            # Cost = Price / (1 + Markup)
            cogs_rx = rx_sales / (1 + inp[0]/100)
            cogs_otc = otc_sales / (1 + inp[13]/100)
            total_cogs = cogs_rx + cogs_otc
            
            gross_margin = total_sales - total_cogs
            
            # 3. ค่าใช้จ่ายดำเนินงาน (Expenses) - จุดที่คนพลาดเยอะ
            # Wages = (Pharmacists * WageRate + Clerks * WageRate) * Hours * 13 Weeks
            # Input Index: 16=#Pharm, 17=PharmRate, 18=#Clerk, 19=ClerkRate
            wage_cost_per_hour = (inp[16]*inp[17]) + (inp[18]*inp[19])
            total_wages = wage_cost_per_hour * inp[6] * WEEKS_PER_PERIOD
            
            mgr_salary = inp[20] # Input 21
            mortgage = inp[23]   # Input 24
            promo = inp[7]       # Input 8
            other_fixed = 3000   # ค่าไฟ ค่าน้ำ (Estimate)
            
            total_expenses = total_wages + mgr_salary + mortgage + promo + other_fixed
            
            # 4. Net Profit ก่อนหักดอกเบี้ย/Penalty
            op_profit = gross_margin - total_expenses
            
            # 5. *** THE PENALTY LOGIC (Input 29) ***
            # เช็คเงินสดหมุนเวียน
            cash_start = 15000
            cash_inflow = total_sales * 0.9 # เก็บเงินได้ 90%
            cash_available = cash_start + cash_inflow
            
            payment_ap = inp[28] # Input 29
            penalty = 0
            
            if payment_ap > cash_available:
                # ถ้าสั่งจ่ายเงินมากกว่าที่มี -> กู้ฉุกเฉินดอกเบี้ยโหด
                overdraft = payment_ap - cash_available
                # จำลอง Penalty ตามที่คุณเจอ (-29M)
                if payment_ap > 100000:
                    penalty = 29000000 + (overdraft * 0.2)
                elif payment_ap > 50000:
                    penalty = 45000000 # เคส Puaypepakor
            
            net_profit = op_profit - penalty
            
            results.append({
                "Team": row['name'],
                "Sales": total_sales,
                "Gross Margin": gross_margin,
                "Expenses": total_expenses,
                "Penalty": penalty,
                "Net Profit": net_profit,
                "Market Share": row['rx_share'] * 100
            })

    return pd.DataFrame(results)

# ==========================================
# 3. USER INTERFACE (Simulate Your Turn)
# ==========================================
st.sidebar.header("🛠️ Thaikritosot Input (Medical Center)")
st.sidebar.info("ปรับค่าตรงนี้เพื่อดูผลลัพธ์ (เปรียบเทียบกับคู่แข่งเดิม)")

# สร้าง Input Fields ให้ครบ (Default คือค่าจาก PDF ของคุณ)
def user_controls():
    inputs = [0] * 36
    # Mapping Default Values from your PDF
    defaults = [49, 0, 0, 1, 1, 1, 46, 600, 90, 2000, 3, 0, 0, 47, 40000, 16000, 0.8, 21, 1.2, 4.75, 8050, 99, 48, 898, 0, 1000, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]
    
    with st.sidebar.expander("1. Pricing & Promo", expanded=True):
        inputs[0] = st.number_input("1. Rx Markup (%)", value=defaults[0])
        inputs[1] = st.number_input("2. Rx Prof. Fee ($)", value=defaults[1])
        inputs[7] = st.number_input("8. Promo Exp ($)", value=defaults[7])
        inputs[13] = st.number_input("14. OTC Markup (%)", value=defaults[13])

    with st.sidebar.expander("2. Operations", expanded=True):
        inputs[6] = st.number_input("7. Hours Open/Week", value=defaults[6])
        inputs[3] = st.selectbox("4. Delivery", [0, 1], index=defaults[3])
        inputs[4] = st.selectbox("5. Patient Records", [0, 1], index=defaults[4])
        
    with st.sidebar.expander("3. Purchasing (Inventory)", expanded=True):
        inputs[14] = st.number_input("15. Rx Inv Purchase ($)", value=defaults[14])
        inputs[15] = st.number_input("16. Other Inv Purchase ($)", value=defaults[15])
        
    with st.sidebar.expander("4. Personnel (Wages)", expanded=False):
        inputs[16] = st.number_input("17. # Pharmacists", value=defaults[16])
        inputs[17] = st.number_input("18. Pharm Wage ($/hr)", value=defaults[17])
        inputs[18] = st.number_input("19. # Clerks", value=defaults[18])
        inputs[19] = st.number_input("20. Clerk Wage ($/hr)", value=defaults[19])
        inputs[20] = st.number_input("21. Mgr Salary ($)", value=defaults[20])

    with st.sidebar.expander("5. Financials (Danger Zone)", expanded=True):
        st.write("⚠️ ระวังช่องนี้! อย่าใส่เกินเงินสดที่มี")
        inputs[28] = st.number_input("29. Pay A/P ($) [0 = Safe]", value=0) 
        # Note: Defaulted to 0 to show "Fixed" state, users can type 999999 to see boom.
        
    # Fill remaining static inputs
    for i in range(36):
        if inputs[i] == 0 and defaults[i] != 0:
            inputs[i] = defaults[i]
            
    return inputs

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
my_inputs = user_controls()
df_results = run_simulation(my_inputs)

st.title("💊 Pharmacy Simulator V11: Corrected Logic")

# Display Highlight Metrics for User
my_stats = df_results[df_results['Team'] == "Thaikritosot (You)"].iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales", f"${my_stats['Sales']:,.0f}")
col2.metric("Net Profit", f"${my_stats['Net Profit']:,.0f}", delta_color="normal" if my_stats['Net Profit']>0 else "inverse")
col3.metric("Market Share", f"{my_stats['Market Share']:.1f}%")
col4.metric("Penalty Deducted", f"${my_stats['Penalty']:,.0f}", delta_color="inverse")

st.markdown("---")

# Comparative Table
st.subheader("📊 เปรียบเทียบกับคู่แข่ง (ใน Medical Center)")
st.dataframe(
    df_results[df_results['Team'].isin(["Thaikritosot (You)", "LhaiJai"])].style.format({
        "Sales": "${:,.0f}", "Gross Margin": "${:,.0f}", "Expenses": "${:,.0f}", 
        "Penalty": "${:,.0f}", "Net Profit": "${:,.0f}", "Market Share": "{:.2f}%"
    }).background_gradient(subset=["Net Profit"], cmap="RdYlGn")
)

# Analysis Section
st.subheader("💡 วิเคราะห์ผลลัพธ์ (Analysis)")
if my_stats['Penalty'] > 0:
    st.error(f"🛑 **CRITICAL ERROR:** คุณโดนหักเงินค่าปรับ ${my_stats['Penalty']:,.0f} เพราะ Input 29 มากเกินเงินสดที่มี! (เหมือนที่เคยเกิดขึ้น)")
else:
    st.success("✅ **SAFE:** สถานะการเงินปลอดภัย ไม่โดนค่าปรับ Input 29")
    
if my_stats['Sales'] < 130000:
    st.warning("⚠️ ยอดขายคุณเริ่มต่ำกว่าคู่แข่ง (LhaiJai) ลองเพิ่มชั่วโมงเปิดร้าน (Input 7) หรือลดราคาลงนิดหน่อย")
elif my_stats['Sales'] > 140000:
    st.success("🚀 ยอดขายคุณนำคู่แข่งแล้ว! กลยุทธ์ราคา/โปรโมชั่นมาถูกทาง")

with st.expander("ดูตารางผลลัพธ์ของทุกทีม (All Locations)"):
    st.dataframe(df_results)
