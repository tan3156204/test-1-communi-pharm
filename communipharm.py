import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V3.1", layout="wide")
ADMIN_PASSWORD = "admin1234"

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_id = f"Team {i}"
        # สร้าง Array เก็บค่า Input 36 ช่อง (เริ่มต้นเป็น 0)
        default_inputs = [0.0] * 37
        
        # Set Defaults
        default_inputs[1] = i      # Store ID
        default_inputs[2] = 1      # Period
        default_inputs[4] = 3.0    # Prof Fee
        default_inputs[5] = 50.0   # Rx Markup
        default_inputs[6] = 45.0   # OTC Markup
        
        st.session_state.players[team_id] = {
            'shop_name': f"ร้านยา Team {i}", # ชื่อเริ่มต้น
            'status': 'Thinking',
            'inputs': default_inputs,
            'financials': {
                'cash': 40000.0, 'inventory_rx': 20000.0, 'inventory_otc': 15000.0,
                'accounts_payable': 0.0, 'long_term_debt': 0.0, 'emergency_loan': 0.0,
                'last_market_share': 14.28
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
        
        inp = p['inputs']
        fin = p['financials']
        
        # --- Mapping Inputs ---
        rx_markup = inp[5] if inp[5] > 0 else 50
        service_score = inp[8] + inp[9] + inp[10] + inp[11]
        total_promo = inp[19] + inp[20] + inp[21] + inp[22]
        
        # --- Simplified Calculation Model ---
        base_sales = 50000 
        price_factor = (50 / rx_markup) * 1.1
        promo_factor = 1 + (total_promo / 5000)
        service_factor = 1 + (service_score * 0.05)
        
        total_rev = base_sales * price_factor * promo_factor * service_factor
        
        # Expenses & COGS
        cogs = total_rev * 0.65
        wages = (inp[12]*inp[13] + inp[14]*inp[15]) * 50 * 13 # Approx wage cost
        other_expenses = sum(inp[29:37]) # Fixed costs user entered
        
        total_exp = wages + other_expenses + total_promo
        net_profit = (total_rev - cogs) - total_exp
        
        # Cash Flow
        cash_in = total_rev
        cash_out = total_exp + inp[23] + inp[24] + inp[25] + inp[26]
        
        fin['cash'] += (cash_in - cash_out)
        
        # Emergency Loan Check
        if fin['cash'] < 0:
            loan = abs(fin['cash']) + 1000
            fin['emergency_loan'] += loan
            fin['cash'] += loan
            
        p['history'].append({
            "Period": st.session_state.global_period,
            "Sales": total_rev,
            "Net Profit": net_profit,
            "Cash": fin['cash']
        })
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. User Interface
# ==========================================

# ฟังก์ชันช่วยแสดงชื่อใน Dropdown
def format_team_name(team_id):
    shop_name = st.session_state.players[team_id].get('shop_name', team_id)
    return f"{shop_name} ({team_id})"

with st.sidebar:
    st.title("💊 Communi-Pharm V3.1")
    role = st.selectbox("Login Role", ["Student", "Instructor"])
    
    if role == "Student":
        # --- [จุดที่แก้ไข] Dropdown แสดงชื่อร้าน ---
        # ใช้ format_func เพื่อแปลง Key (Team 1) ให้โชว์เป็นชื่อร้าน
        team = st.selectbox(
            "เลือกทีมของคุณ (Select Team)", 
            options=list(st.session_state.players.keys()),
            format_func=format_team_name
        )
    else:
        pwd = st.text_input("Admin Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    
    # --- Sidebar ตั้งชื่อร้าน ---
    with st.sidebar:
        st.markdown("---")
        st.subheader("🏷️ ตั้งชื่อร้าน (Shop Name)")
        new_name = st.text_input("ชื่อร้าน:", value=p['shop_name'])
        if st.button("บันทึกชื่อ"):
            p['shop_name'] = new_name
            st.success("เปลี่ยนชื่อเรียบร้อย!")
            st.rerun()

    # --- Main Dashboard ---
    st.title(f"🏥 {p['shop_name']}")
    st.caption(f"Team ID: {team} | Period: {st.session_state.global_period}")
    
    # Show Last Period Stats
    if p['history']:
        last = p['history'][-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("ยอดขาย (Sales)", f"${last['Sales']:,.0f}")
        c2.metric("กำไรสุทธิ (Net Profit)", f"${last['Net Profit']:,.0f}")
        c3.metric("เงินสด (Cash)", f"${last['Cash']:,.0f}")

    if p['status'] == 'Submitted':
        st.info("✅ ส่งข้อมูลเรียบร้อยแล้ว รออาจารย์ประมวลผล")
        if st.button("แก้ไขข้อมูล"):
            p['status'] = 'Thinking'
            st.rerun()
    else:
        with st.form("input_36_form"):
            st.subheader("📝 แบบฟอร์มตัดสินใจ (36 ข้อ)")
            
            # Layout 3 Columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("##### 1. ข้อมูลทั่วไป & นโยบาย")
                val_01 = st.number_input("01. รหัสร้าน", value=int(p['inputs'][1]))
                val_02 = st.number_input("02. งวดที่", value=st.session_state.global_period, disabled=True)
                val_03 = st.number_input("03. รหัสทำเล", value=int(p['inputs'][3]))
                val_04 = st.number_input("04. ค่าวิชาชีพ ($)", value=p['inputs'][4])
                val_05 = st.number_input("05. Rx Markup (%)", value=p['inputs'][5])
                val_06 = st.number_input("06. OTC Markup (%)", value=p['inputs'][6])
                val_07 = st.number_input("07. ส่วนลดพิเศษ (%)", value=p['inputs'][7])
                st.markdown("**บริการ (1=มี, 0=ไม่มี)**")
                val_08 = st.number_input("08. ส่งของ", 0, 1, int(p['inputs'][8]))
                val_09 = st.number_input("09. ประวัติผู้ป่วย", 0, 1, int(p['inputs'][9]))
                val_10 = st.number_input("10. ให้เครดิต", 0, 1, int(p['inputs'][10]))
                val_11 = st.number_input("11. ให้คำปรึกษา", 0, 1, int(p['inputs'][11]))
                val_12 = st.number_input("12. จำนวนเภสัชกร", value=p['inputs'][12])

            with col2:
                st.markdown("##### 2. ดำเนินงาน & การตลาด")
                val_13 = st.number_input("13. ค่าแรงเภสัช ($/hr)", value=p['inputs'][13])
                val_14 = st.number_input("14. จำนวนผู้ช่วย", value=p['inputs'][14])
                val_15 = st.number_input("15. ค่าแรงผู้ช่วย ($/hr)", value=p['inputs'][15])
                val_16 = st.number_input("16. เงินเดือน ผจก.", value=8000.0)
                val_17 = st.number_input("17. เปิดร้าน (วันธรรมดา)", value=p['inputs'][17])
                val_18 = st.number_input("18. เปิดร้าน (วันอาทิตย์)", value=p['inputs'][18])
                st.markdown("**งบโฆษณา ($)**")
                val_19 = st.number_input("19. นสพ.", value=p['inputs'][19])
                val_20 = st.number_input("20. วิทยุ", value=p['inputs'][20])
                val_21 = st.number_input("21. ทีวี", value=p['inputs'][21])
                val_22 = st.number_input("22. ไปรษณีย์", value=p['inputs'][22])
                st.markdown("---")
                val_23 = st.number_input("23. ซื้อยา Rx ($)", value=p['inputs'][23])
                val_24 = st.number_input("24. ซื้อยา OTC ($)", value=p['inputs'][24])

            with col3:
                st.markdown("##### 3. การเงิน & ค่าใช้จ่าย")
                val_25 = st.number_input("25. จ่ายเจ้าหนี้ ($)", value=p['inputs'][25])
                val_26 = st.number_input("26. จ่ายเงินกู้ ($)", value=p['inputs'][26])
                val_27 = st.number_input("27. กู้เพิ่ม ($)", value=p['inputs'][27])
                val_28 = st.number_input("28. จ่ายปันผล ($)", value=p['inputs'][28])
                st.markdown("**ค่าใช้จ่ายดำเนินงาน (กรอกตามจริง)**")
                val_29 = st.number_input("29. ค่าเช่า", value=p['inputs'][29])
                val_30 = st.number_input("30. ค่าน้ำไฟ", value=1500.0)
                val_31 = st.number_input("31. ค่าประกัน", value=400.0)
                val_32 = st.number_input("32. ค่าใบอนุญาต", value=200.0)
                val_33 = st.number_input("33. ค่าซ่อมแซม", value=p['inputs'][33])
                val_34 = st.number_input("34. วัสดุสิ้นเปลือง", value=p['inputs'][34])
                val_35 = st.number_input("35. ค่าบัญชี/กม.", value=p['inputs'][35])
                val_36 = st.number_input("36. อื่นๆ", value=p['inputs'][36])

            if st.form_submit_button("✅ ยืนยันข้อมูล (Submit)"):
                # Save data back to array
                new_inputs = [0.0]*37
                # Map inputs
                new_inputs[1]=val_01; new_inputs[3]=val_03; new_inputs[4]=val_04; new_inputs[5]=val_05
                new_inputs[6]=val_06; new_inputs[7]=val_07; new_inputs[8]=val_08; new_inputs[9]=val_09
                new_inputs[10]=val_10; new_inputs[11]=val_11; new_inputs[12]=val_12; new_inputs[13]=val_13
                new_inputs[14]=val_14; new_inputs[15]=val_15; new_inputs[16]=val_16; new_inputs[17]=val_17
                new_inputs[18]=val_18; new_inputs[19]=val_19; new_inputs[20]=val_20; new_inputs[21]=val_21
                new_inputs[22]=val_22; new_inputs[23]=val_23; new_inputs[24]=val_24; new_inputs[25]=val_25
                new_inputs[26]=val_26; new_inputs[27]=val_27; new_inputs[28]=val_28; new_inputs[29]=val_29
                new_inputs[30]=val_30; new_inputs[31]=val_31; new_inputs[32]=val_32; new_inputs[33]=val_33
                new_inputs[34]=val_34; new_inputs[35]=val_35; new_inputs[36]=val_36
                
                p['inputs'] = new_inputs
                p['status'] = 'Submitted'
                st.rerun()

elif role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Control")
    
    # Status Table
    st.subheader("สถานะผู้เล่น")
    status_rows = []
    for t_id, p in st.session_state.players.items():
        status_rows.append({
            "Team ID": t_id,
            "Shop Name": p['shop_name'],
            "Status": "✅ ส่งแล้ว" if p['status']=='Submitted' else "⏳ กำลังคิด",
            "Cash": f"${p['financials']['cash']:,.0f}"
        })
    st.dataframe(pd.DataFrame(status_rows), hide_index=True)

    if st.button("🚀 ประมวลผลรอบนี้ (Run Period)"):
        process_period()
        st.success("ประมวลผลเสร็จสิ้น!")
        st.rerun()
