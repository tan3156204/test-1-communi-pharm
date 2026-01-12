import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V3.2 (Exact Form Match)", layout="wide")
ADMIN_PASSWORD = "admin1234"

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    # สร้างข้อมูลเริ่มต้น 7 ทีม
    for i in range(1, 8):
        team_id = f"Team {i}"
        
        # สร้าง List ว่าง 37 ช่อง (ใช้ Index 1-36)
        # เพื่อให้ตรงกับ Item 1 - Item 36 ในแบบฟอร์ม
        inputs = [0.0] * 37 
        
        # --- กำหนดค่าเริ่มต้น (Default Values) ---
        inputs[1] = float(i)    # Item 1: Store ID
        inputs[2] = 1.0         # Item 2: Period
        inputs[3] = 1.0         # Item 3: Location Code
        inputs[4] = 3.0         # Item 4: Prof Fee
        inputs[5] = 50.0        # Item 5: Rx Markup %
        inputs[6] = 45.0        # Item 6: OTC Markup %
        inputs[12] = 1.0        # Item 12: Pharmacists
        inputs[13] = 20.0       # Item 13: Pharm Wage
        inputs[14] = 1.0        # Item 14: Clerks
        inputs[15] = 6.0        # Item 15: Clerk Wage
        inputs[16] = 8000.0     # Item 16: Manager Salary
        inputs[17] = 50.0       # Item 17: Hours Weekday
        inputs[23] = 20000.0    # Item 23: Purchase Rx
        inputs[24] = 10000.0    # Item 24: Purchase OTC
        inputs[30] = 1500.0     # Item 30: Utilities
        inputs[31] = 400.0      # Item 31: Insurance
        inputs[32] = 200.0      # Item 32: Licenses

        st.session_state.players[team_id] = {
            'shop_name': f"ร้านยา Team {i}", 
            'status': 'Thinking',
            'inputs': inputs, # เก็บค่า Item01-36 ไว้ในนี้
            'financials': {
                'cash': 40000.0, 
                'inventory_rx': 20000.0, 
                'inventory_otc': 15000.0,
                'long_term_debt': 0.0, 
                'emergency_loan': 0.0
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Engine (Simulation Logic)
# ==========================================
def process_period():
    for t, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        
        # ดึงค่า Input ออกมาเป็นตัวแปร (unpack) เพื่อความชัดเจนในการคำนวณ
        inp = p['inputs']
        fin = p['financials']
        
        # --- 1. MAPPING VARIABLES (ให้ตรงกับ Logic คู่มือ) ---
        item05_rx_markup = inp[5]
        item06_otc_markup = inp[6]
        
        # Service Score (Item 8,9,10,11)
        service_score = inp[8] + inp[9] + inp[10] + inp[11]
        
        # Total Promo (Item 19,20,21,22)
        total_promo = inp[19] + inp[20] + inp[21] + inp[22]
        
        # Wages Calculation
        # (Pharmacists * Wage) + (Clerks * Wage) * Hours * 13 weeks
        weekly_hours = inp[17] # Item 17
        wage_cost = ((inp[12] * inp[13]) + (inp[14] * inp[15])) * weekly_hours * 13
        
        # --- 2. SALES CALCULATION ---
        # Logic อย่างง่าย: ถ้าราคาถูก + โปรเยอะ + บริการดี = ขายดี
        base_sales = 50000 
        price_factor = (50 / item05_rx_markup) * 1.05 if item05_rx_markup > 0 else 0
        promo_factor = 1 + (total_promo / 5000)
        service_factor = 1 + (service_score * 0.05)
        
        total_revenue = base_sales * price_factor * promo_factor * service_factor
        
        # --- 3. EXPENSES (P&L) ---
        cogs = total_revenue * 0.65 # ต้นทุนสินค้าขายประมาณ 65%
        
        # รวมค่าใช้จ่ายดำเนินงาน (Item 29 - 36) ที่ผู้เล่นกรอกมา
        operating_fixed_costs = sum(inp[29:37]) # Sum Item 29 to 36
        
        total_expenses = wage_cost + inp[16] + operating_fixed_costs + total_promo
        
        # Net Profit
        net_profit = (total_revenue - cogs) - total_expenses
        
        # --- 4. CASH FLOW ---
        # Cash In
        cash_in = total_revenue
        
        # Cash Out (Expenses + Purchases + Debt Payments)
        # Note: Wages & Fixed Costs are paid in cash
        cash_out_expenses = total_expenses # สมมติจ่ายสดทั้งหมด
        cash_out_purchases = inp[23] + inp[24] # Item 23, 24
        cash_out_debt = inp[25] + inp[26]      # Item 25 (AP), 26 (Notes)
        
        total_cash_out = cash_out_expenses + cash_out_purchases + cash_out_debt
        
        fin['cash'] += (cash_in - total_cash_out)
        
        # Emergency Loan Check
        if fin['cash'] < 0:
            loan_needed = abs(fin['cash']) + 1000
            fin['emergency_loan'] += loan_needed
            fin['cash'] += loan_needed
        
        # --- 5. UPDATE HISTORY ---
        p['history'].append({
            "Period": st.session_state.global_period,
            "Sales": total_revenue,
            "Net Profit": net_profit,
            "Cash": fin['cash']
        })
        
        # Reset Status
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. User Interface
# ==========================================
def format_team_name(team_id):
    shop_name = st.session_state.players[team_id].get('shop_name', team_id)
    return f"{shop_name} ({team_id})"

with st.sidebar:
    st.title("💊 Communi-Pharm V3.2")
    role = st.selectbox("Login Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Select Team", options=list(st.session_state.players.keys()), format_func=format_team_name)
    else:
        pwd = st.text_input("Admin Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    
    # --- Sidebar: Shop Name ---
    with st.sidebar:
        st.markdown("---")
        st.subheader("🏷️ Shop Identity")
        new_name = st.text_input("Shop Name", value=p['shop_name'])
        if st.button("Save Name"):
            p['shop_name'] = new_name
            st.rerun()

    # --- Dashboard ---
    st.title(f"🏥 {p['shop_name']}")
    st.caption(f"Team: {team} | Current Period: {st.session_state.global_period}")
    
    if p['history']:
        last = p['history'][-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Sales", f"${last['Sales']:,.0f}")
        c2.metric("Net Profit", f"${last['Net Profit']:,.0f}")
        c3.metric("Cash Balance", f"${last['Cash']:,.0f}")

    if p['status'] == 'Submitted':
        st.success("✅ Input Submitted. Waiting for processing.")
        if st.button("Edit Inputs"):
            p['status'] = 'Thinking'; st.rerun()
    else:
        # ==========================================
        # FORM INPUT: EXACT MATCH WITH MANUAL
        # ==========================================
        with st.form("decision_form_36_items"):
            st.subheader("📝 Decision Input Form (36 Items)")
            st.info("กรุณากรอกข้อมูลให้ตรงกับใบส่งคำตอบ (Item 1 - 36)")
            
            # โหลดค่าเดิมจาก Memory
            saved = p['inputs'] 
            
            # แบ่ง 3 คอลัมน์เหมือนหน้ากระดาษ
            col1, col2, col3 = st.columns(3)
            
            # --- COLUMN 1: Items 1 - 12 ---
            with col1:
                st.markdown("### Section 1")
                item01_store_id = st.number_input("Item 1: Store ID", value=int(saved[1]), disabled=True)
                item02_period   = st.number_input("Item 2: Period", value=st.session_state.global_period, disabled=True)
                item03_location = st.number_input("Item 3: Location Code", value=int(saved[3]))
                item04_prof_fee = st.number_input("Item 4: Prof Fee ($)", value=saved[4])
                item05_rx_markup= st.number_input("Item 5: Rx Markup (%)", value=saved[5])
                item06_otc_mark = st.number_input("Item 6: OTC Markup (%)", value=saved[6])
                item07_discount = st.number_input("Item 7: Special Disc (%)", value=saved[7])
                
                st.markdown("---")
                st.caption("Service Policy (0=No, 1=Yes)")
                item08_delivery = st.number_input("Item 8: Delivery", 0, 1, int(saved[8]))
                item09_records  = st.number_input("Item 9: Patient Records", 0, 1, int(saved[9]))
                item10_charge   = st.number_input("Item 10: Charge Acct", 0, 1, int(saved[10]))
                item11_consult  = st.number_input("Item 11: Consulting", 0, 1, int(saved[11]))
                item12_n_pharm  = st.number_input("Item 12: No. Pharmacists", value=saved[12])

            # --- COLUMN 2: Items 13 - 24 ---
            with col2:
                st.markdown("### Section 2")
                item13_w_pharm  = st.number_input("Item 13: Pharm Wage ($)", value=saved[13])
                item14_n_clerk  = st.number_input("Item 14: No. Clerks", value=saved[14])
                item15_w_clerk  = st.number_input("Item 15: Clerk Wage ($)", value=saved[15])
                item16_mgr_sal  = st.number_input("Item 16: Manager Salary", value=saved[16])
                item17_hrs_wk   = st.number_input("Item 17: Hours (Week)", value=saved[17])
                item18_hrs_sun  = st.number_input("Item 18: Hours (Sun)", value=saved[18])
                
                st.markdown("---")
                st.caption("Advertising ($)")
                item19_ads_news = st.number_input("Item 19: Newspaper", value=saved[19])
                item20_ads_rad  = st.number_input("Item 20: Radio", value=saved[20])
                item21_ads_tv   = st.number_input("Item 21: TV", value=saved[21])
                item22_ads_mail = st.number_input("Item 22: Direct Mail", value=saved[22])
                
                st.markdown("---")
                item23_buy_rx   = st.number_input("Item 23: Purchase Rx ($)", value=saved[23])
                item24_buy_otc  = st.number_input("Item 24: Purchase OTC ($)", value=saved[24])

            # --- COLUMN 3: Items 25 - 36 ---
            with col3:
                st.markdown("### Section 3")
                item25_pay_ap   = st.number_input("Item 25: Pay A/P ($)", value=saved[25])
                item26_pay_note = st.number_input("Item 26: Pay Notes ($)", value=saved[26])
                item27_new_note = st.number_input("Item 27: New Note ($)", value=saved[27])
                item28_div      = st.number_input("Item 28: Dividends ($)", value=saved[28])
                
                st.markdown("---")
                st.caption("Operating Expenses (Fill from Report)")
                item29_rent     = st.number_input("Item 29: Rent", value=saved[29])
                item30_util     = st.number_input("Item 30: Utilities", value=saved[30])
                item31_ins      = st.number_input("Item 31: Insurance", value=saved[31])
                item32_lic      = st.number_input("Item 32: Taxes/License", value=saved[32])
                item33_repair   = st.number_input("Item 33: Repairs", value=saved[33])
                item34_supply   = st.number_input("Item 34: Supplies", value=saved[34])
                item35_acct     = st.number_input("Item 35: Acct/Legal", value=saved[35])
                item36_other    = st.number_input("Item 36: Other Exp", value=saved[36])

            submitted = st.form_submit_button("✅ Submit Decisions (ส่งคำตอบ)")
            
            if submitted:
                # สร้าง List ใหม่เพื่อบันทึกกลับ (Map ตัวแปรเข้า Array Index)
                new_inputs = [0.0] * 37
                
                # Assign values back to specific indexes
                new_inputs[1] = item01_store_id
                new_inputs[2] = item02_period
                new_inputs[3] = item03_location
                new_inputs[4] = item04_prof_fee
                new_inputs[5] = item05_rx_markup
                new_inputs[6] = item06_otc_mark
                new_inputs[7] = item07_discount
                new_inputs[8] = item08_delivery
                new_inputs[9] = item09_records
                new_inputs[10] = item10_charge
                new_inputs[11] = item11_consult
                new_inputs[12] = item12_n_pharm
                new_inputs[13] = item13_w_pharm
                new_inputs[14] = item14_n_clerk
                new_inputs[15] = item15_w_clerk
                new_inputs[16] = item16_mgr_sal
                new_inputs[17] = item17_hrs_wk
                new_inputs[18] = item18_hrs_sun
                new_inputs[19] = item19_ads_news
                new_inputs[20] = item20_ads_rad
                new_inputs[21] = item21_ads_tv
                new_inputs[22] = item22_ads_mail
                new_inputs[23] = item23_buy_rx
                new_inputs[24] = item24_buy_otc
                new_inputs[25] = item25_pay_ap
                new_inputs[26] = item26_pay_note
                new_inputs[27] = item27_new_note
                new_inputs[28] = item28_div
                new_inputs[29] = item29_rent
                new_inputs[30] = item30_util
                new_inputs[31] = item31_ins
                new_inputs[32] = item32_lic
                new_inputs[33] = item33_repair
                new_inputs[34] = item34_supply
                new_inputs[35] = item35_acct
                new_inputs[36] = item36_other
                
                # Save to session state
                p['inputs'] = new_inputs
                p['status'] = 'Submitted'
                st.rerun()

elif role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Control Center")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Player Status")
        status_data = []
        for t, p in st.session_state.players.items():
            status_data.append({
                "Team": t,
                "Shop Name": p['shop_name'],
                "Status": "✅ READY" if p['status'] == 'Submitted' else "⏳ Thinking",
                "Cash": f"${p['financials']['cash']:,.0f}"
            })
        st.dataframe(pd.DataFrame(status_data), hide_index=True)
    
    with col2:
        if st.button("🚀 PROCESS PERIOD", type="primary"):
            process_period()
            st.success("Simulation Computed!")
            st.rerun()
