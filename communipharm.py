import streamlit as st
import pandas as pd
import numpy as np
import random

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V6.3 (Full)", layout="wide")
ADMIN_PASSWORD = "admin"

# 36 Input Labels
INPUT_LABELS = [
    "1. Prescription Markup (%)", "2. Prescription Professional Fee ($)", "3. Copayment Discount ($)",
    "4. Delivery Service (0=No, 1=Yes)", "5. Patient Records (0=No, 1=Yes)", "6. Store Offers Credit (0=No, 1=Yes)",
    "7. Hours Pharmacy Open Per Week", "8. Promotional Expenditures ($)", "9. % Promotion on Rx Dept (%)",
    "10. Current Period’s Investment ($)", "11. Investment Project Number", "12. Investment Withdrawal ($)",
    "13. Investment Withdrawal Project Number", "14. Markup on Other Items (%)", "15. Prescription Inv Purchases ($)",
    "16. Other Inv Purchases ($)", "17. Number Pharmacists", "18. Pharmacist’s Hourly Pay ($)",
    "19. Number Sales Clerks", "20. Sales Clerk’s Hourly Pay ($)", "21. Manager’s Salary ($)",
    "22. Manager’s % Time Rx", "23. Manager Hours/Week", "24. Mortgage Payment ($)",
    "25. Collection Agency ($)", "26. Minimum Cash Balance ($)", "27. Rx Inv Returned ($)",
    "28. Other Inv Returned ($)", "29. Payment on A/P ($)", "30. Long Term Debt Written ($)",
    "31. Long Term Debt Payment ($)", "32. Interest Rate A/R (%)", "33. Benefits: Life Ins (0/1)",
    "34. Benefits: Health Ins (0/1)", "35. Third-Party Rx (0/1)", "36. Bid for HMO Contract ($)"
]

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_id = f"team_{i}" 
        # Default Inputs
        inputs = [0.0] * 36
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=20.0; inputs[19]=6.0; inputs[20]=8000.0
        inputs[23]=40.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}", 
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 'retained_earnings': 92000.0,
                'fixed_assets': 50000.0
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Logic (Demo & Process)
# ==========================================
def generate_demo_data():
    st.session_state.global_period = 5
    for t_id, p in st.session_state.players.items():
        sales = random.randint(150000, 500000)
        p['history'] = [{
            "Period": 5,
            "TOT SALES": sales,
            "Rx SALES": sales * 0.6,
            "OTH SALES": sales * 0.4,
            "Avg Rx Pr": 20.0 + random.uniform(-2, 5),
            "TOT COGS": sales * 0.65,
            "GROSS MARGIN": sales * 0.35,
            "TOT EXPENSES": sales * 0.30,
            "NET PROFIT": sales * 0.05,
            "CASH": 50000 + (sales * 0.05),
            "NET WORTH": 92000 + (sales * 0.05),
            # Stats
            "Wage/Hr": 20.0 + random.uniform(0, 50),
            "Hrs Wked": random.choice([40, 50, 60, 80]),
            "Pt Rec": random.choice([0, 1]),
            "Del Ser": random.choice([0, 1]),
            "Store Credit": random.choice([0, 1]),
            "Copay Dsct": random.choice([0.0, 0.3, 0.5]),
            "Hrs Open": random.choice([50, 60, 80]),
            "ROI": 0.15,
            "Life Ins": random.choice([0, 1]),
            "Hlt Ins": random.choice([0, 1])
        }]
        p['status'] = 'Submitted'

def process_period():
    # ในการใช้งานจริง โค้ดส่วนนี้จะคำนวณจาก Input
    # แต่ในโหมด Demo นี้ผมจะเรียก generate_demo_data แทน
    generate_demo_data()

# ==========================================
# 4. UI Dashboard
# ==========================================
def format_money(val): return f"${val:,.0f}"

with st.sidebar:
    st.title("💊 Communi-Pharm V6.3")
    role = st.selectbox("Select Role", ["Student", "Instructor"])
    
    if role == "Student":
        team_ids = list(st.session_state.players.keys())
        def get_shop_name(tid):
            return st.session_state.players[tid]['shop_name']
        
        selected_id = st.selectbox("เลือกร้านของคุณ", options=team_ids, format_func=get_shop_name)
        
        # --- Rename Feature ---
        p = st.session_state.players[selected_id]
        st.markdown("---")
        st.caption("ตั้งชื่อร้าน:")
        new_name_input = st.text_input("✏️ Shop Name", value=p['shop_name'])
        if new_name_input != p['shop_name']:
            p['shop_name'] = new_name_input
            st.rerun()

    else:
        st.info("Password: admin")
        pwd = st.text_input("Password", type="password")

# --- INSTRUCTOR VIEW ---
if role == "Instructor":
    if pwd == ADMIN_PASSWORD:
        st.header("👨‍🏫 INSTRUCTOR'S SUMMARY")
        if st.button("🎲 Generate Demo Data"):
            generate_demo_data(); st.rerun()

        has_data = any(len(p['history']) > 0 for p in st.session_state.players.values())
        if has_data:
            # Table 1: Financial Matrix
            st.subheader("1. Financial Summary")
            row_labels = ["TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "TOT COGS", "GROSS MARGIN", "TOT EXPENSES", "NET PROFIT", "CASH", "NET WORTH"]
            matrix_data = {}
            for tid, data in st.session_state.players.items():
                if data['history']:
                    last = data['history'][-1]
                    vals = []
                    for lbl in row_labels:
                        v = last.get(lbl, 0)
                        if lbl == "Avg Rx Pr": vals.append(f"${v:,.2f}")
                        else: vals.append(f"${v:,.0f}")
                    matrix_data[data['shop_name']] = vals # Use Shop Name as Header
            st.table(pd.DataFrame(matrix_data, index=row_labels))
            
            # Table 2: Stats
            st.subheader("2. City Summary Statistics")
            stats_rows = []
            for tid, data in st.session_state.players.items():
                if data['history']:
                    last = data['history'][-1]
                    stats_rows.append({
                        "Store Name": data['shop_name'],
                        "Wage/Hr": f"${last['Wage/Hr']:.2f}",
                        "Hrs Wked": last['Hrs Wked'],
                        "Pt Rec": "Yes" if last['Pt Rec'] else "No",
                        "Del Ser": "Yes" if last['Del Ser'] else "No",
                        "Credit": "Yes" if last['Store Credit'] else "No",
                        "Copay": f"${last['Copay Dsct']:.2f}",
                        "Hrs Open": last['Hrs Open'],
                        "ROI": f"{last['ROI']:.2f}",
                        "Life Ins": "Yes" if last['Life Ins'] else "No",
                        "Hlt Ins": "Yes" if last['Hlt Ins'] else "No"
                    })
            st.table(pd.DataFrame(stats_rows))
        else:
            st.warning("No data yet.")

# --- STUDENT VIEW ---
elif role == "Student":
    st.title(f"🏥 {p['shop_name']}")
    st.markdown(f"**Period:** {st.session_state.global_period} | **Status:** {p['status']}")
    
    # === ส่วน Input Form (ที่นำกลับมาให้แล้ว) ===
    if p['status'] == 'Thinking':
        st.info("กรุณากรอกข้อมูลตัดสินใจให้ครบทั้ง 36 ข้อ")
        with st.form("decision_form_36"):
            c1, c2, c3 = st.columns(3)
            inputs = p['inputs']
            
            # Loop สร้าง Input 36 ช่อง
            for i in range(36):
                col = [c1, c2, c3][i // 12]
                with col:
                    # Logic เลือกประเภท Input (Selectbox หรือ Number)
                    if i in [3, 4, 5, 32, 33, 34]: 
                        inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]), key=f"in_{i}")
                    else:
                        inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]), key=f"in_{i}")

            st.markdown("---")
            if st.form_submit_button("✅ ยืนยันข้อมูล (Submit Decisions)"):
                p['inputs'] = inputs
                p['status'] = 'Submitted'
                st.rerun()

    # === ส่วนแสดงผลลัพธ์ (เมื่อส่งแล้วและอาจารย์รันแล้ว) ===
    elif p['status'] == 'Submitted':
        if p['history']:
            # ถ้ามีประวัติ แสดงผลลัพธ์
            st.success("ผลลัพธ์ออกแล้ว (Results Available)")
            last = p['history'][-1]
            
            # แสดง Operating Statement แบบย่อ
            st.markdown("### 📄 OPERATING STATEMENT (Latest Period)")
            op_data = [
                ["TOT SALES", f"${last['TOT SALES']:,.0f}"],
                ["TOT EXPENSES", f"${last['TOT EXPENSES']:,.0f}"],
                ["NET PROFIT", f"${last['NET PROFIT']:,.0f}"],
                ["CASH BALANCE", f"${last['CASH']:,.0f}"]
            ]
            st.table(pd.DataFrame(op_data, columns=["Item", "Amount"]))
            
            if st.button("แก้ไขการตัดสินใจรอบถัดไป"):
                # ในเกมจริงต้องรอรอบใหม่ แต่ใน Demo กดแก้ได้เลย
                p['status'] = 'Thinking'
                st.rerun()
        else:
            # ถ้าส่งแล้วแต่อาจารย์ยังไม่รัน
            st.warning("⏳ ส่งข้อมูลแล้ว กรุณารออาจารย์ประมวลผล (Waiting for Instructor)")
            if st.button("แก้ไขข้อมูล (Edit)"):
                p['status'] = 'Thinking'
                st.rerun()
