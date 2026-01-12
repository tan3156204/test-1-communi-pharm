import streamlit as st
import pandas as pd
import numpy as np
import random

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V6.2", layout="wide")
ADMIN_PASSWORD = "admin"

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    # สร้าง 7 ทีม (ใช้ Key เป็น ID ถาวร แต่ Shop Name เปลี่ยนได้)
    for i in range(1, 8):
        team_id = f"team_{i}" 
        # Default Values
        inputs = [0.0] * 36
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=20.0; inputs[19]=6.0; inputs[20]=8000.0
        inputs[23]=40.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}", # ชื่อเริ่มต้น
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
# 3. Game Logic (Demo Generator)
# ==========================================
def generate_demo_data():
    st.session_state.global_period = 5
    for t_id, p in st.session_state.players.items():
        # Random Data Logic
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
            # Operational Stats
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

# ==========================================
# 4. UI Dashboard
# ==========================================
def format_money(val): return f"${val:,.0f}"

with st.sidebar:
    st.title("💊 Communi-Pharm V6.2")
    role = st.selectbox("Select Role", ["Instructor", "Student"])
    
    # --- ส่วนเลือกทีม (แก้ไขให้โชว์ชื่อร้าน) ---
    if role == "Student":
        # ดึงรายชื่อ ID ทั้งหมด
        team_ids = list(st.session_state.players.keys())
        
        # ฟังก์ชันแปลง ID -> ชื่อร้าน เพื่อแสดงใน Dropdown
        def get_shop_name(tid):
            return st.session_state.players[tid]['shop_name']
        
        # Selectbox ใช้ format_func
        selected_id = st.selectbox(
            "เลือกร้านของคุณ (Select Store)", 
            options=team_ids, 
            format_func=get_shop_name 
        )
        
        # --- ฟีเจอร์เปลี่ยนชื่อร้าน ---
        p = st.session_state.players[selected_id]
        st.markdown("---")
        st.caption("ตั้งชื่อร้านของคุณที่นี่:")
        new_name_input = st.text_input("✏️ Shop Name", value=p['shop_name'])
        
        # ถ้ามีการแก้ไขชื่อ ให้บันทึกและ Rerun หน้าจอ
        if new_name_input != p['shop_name']:
            p['shop_name'] = new_name_input
            st.rerun()

    else:
        # Instructor Login
        st.info("Password: admin")
        pwd = st.text_input("Password", type="password")

# --- INSTRUCTOR VIEW ---
if role == "Instructor":
    if pwd == ADMIN_PASSWORD:
        st.header("👨‍🏫 INSTRUCTOR'S SUMMARY")
        
        if st.button("🎲 Generate Demo Data (สร้างข้อมูลตัวอย่าง)"):
            generate_demo_data()
            st.rerun()

        # เช็คว่ามีข้อมูลไหม
        has_data = any(len(p['history']) > 0 for p in st.session_state.players.values())
        
        if has_data:
            # 1. Financial Matrix
            st.subheader("1. Financial Summary")
            row_labels = ["TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "TOT COGS", "GROSS MARGIN", "TOT EXPENSES", "NET PROFIT", "CASH", "NET WORTH"]
            
            matrix_data = {}
            # วนลูปดึงข้อมูล โดยใช้ชื่อร้าน (shop_name) เป็นหัวตาราง
            for tid, data in st.session_state.players.items():
                if data['history']:
                    last = data['history'][-1]
                    col_name = data['shop_name'] # <--- ใช้ชื่อร้านเป็นหัวตาราง
                    
                    vals = []
                    for lbl in row_labels:
                        v = last.get(lbl, 0)
                        if lbl == "Avg Rx Pr": vals.append(f"${v:,.2f}")
                        else: vals.append(f"${v:,.0f}")
                    matrix_data[col_name] = vals
            
            st.table(pd.DataFrame(matrix_data, index=row_labels))
            
            # 2. Stats
            st.subheader("2. City Summary Statistics")
            stats_rows = []
            for tid, data in st.session_state.players.items():
                if data['history']:
                    last = data['history'][-1]
                    stats_rows.append({
                        "Store Name": data['shop_name'], # <--- ใช้ชื่อร้านในตาราง
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
            st.warning("No data yet. Click 'Generate Demo Data'.")
            
# --- STUDENT VIEW ---
elif role == "Student":
    # p ถูก define ไว้ข้างบนแล้วจาก sidebar
    st.title(f"🏥 {p['shop_name']}") # หัวข้อเป็นชื่อร้าน
    
    if p['history']:
        st.success(f"ผลลัพธ์รอบที่ {p['history'][-1]['Period']}")
        st.metric("Net Profit", f"${p['history'][-1]['NET PROFIT']:,.0f}")
    else:
        st.info("รอผลการรัน (Waiting for results)")
