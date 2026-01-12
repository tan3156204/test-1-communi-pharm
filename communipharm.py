import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V5.5 (Instructor Summary)", layout="wide")
ADMIN_PASSWORD = "admin1234"

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
        team_id = f"Team {i}"
        inputs = [0.0] * 36
        # Defaults
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=20.0; inputs[19]=6.0; inputs[20]=8000.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Pharmacy {i}",
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 'acct_receivable': 2000.0,
                'inventory_rx': 20000.0, 'inventory_otc': 15000.0,
                'fixed_assets': 50000.0, 'acct_payable': 5000.0,
                'notes_payable': 0.0, 'long_term_debt': 30000.0,
                'retained_earnings': 92000.0 
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Engine
# ==========================================
def process_period():
    # 1. Calculate for each player
    city_total_sales = 0
    
    for t, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        inp = p['inputs']
        fin = p['financials']
        
        # --- Revenue ---
        rx_markup = inp[0] if inp[0] > 0 else 1
        promo_impact = 1 + (inp[7] / 10000)
        service_impact = 1 + (sum([inp[3], inp[4], inp[5], inp[32], inp[33], inp[34]]) * 0.03)
        
        base_sales = (45000 + 25000) * promo_impact * service_impact
        total_sales = base_sales
        rx_sales = total_sales * 0.65
        otc_sales = total_sales * 0.35
        
        city_total_sales += total_sales
        
        # --- COGS ---
        cost_rx = rx_sales / (1 + (rx_markup/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cost_rx + cost_otc
        
        fin['inventory_rx'] += inp[14] - cost_rx
        fin['inventory_otc'] += inp[15] - cost_otc
        
        # --- Expenses ---
        weeks = 13; hours = inp[6]
        payroll = (inp[16]*inp[17] + inp[18]*inp[19])*hours*weeks + inp[20]
        
        exp_rent = inp[23] if inp[23] > 0 else 2500.0
        # Sum estimated ops
        other_ops = 800+300+400+350+500+400 
        exp_ads = inp[7]
        exp_depr = fin['fixed_assets'] * 0.02
        exp_int = (fin['long_term_debt'] * 0.02)
        
        total_exp = payroll + exp_rent + other_ops + exp_ads + exp_depr + exp_int
        
        # Profit
        gross_margin = total_sales - total_cogs
        net_profit = gross_margin - total_exp
        
        # Cash Flow
        cash_in = total_sales * 0.95 + inp[29]
        cash_out = (total_exp - exp_depr) + (inp[14]+inp[15]) + (inp[28]+inp[30])
        fin['cash'] += (cash_in - cash_out)
        fin['retained_earnings'] += net_profit
        
        if fin['cash'] < 0:
            loan = abs(fin['cash']) + 1000
            fin['notes_payable'] += loan
            fin['cash'] += loan
            
        # Calc Avg Rx Price (Simulation)
        # Assume avg Rx cost around $10 -> Price = 10 * markup + fee
        avg_rx_price = 10.0 * (1 + rx_markup/100) + inp[1]

        p['history'].append({
            "Period": st.session_state.global_period,
            "Total Sales": total_sales,
            "Rx Sales": rx_sales,
            "Other Sales": otc_sales,
            "Total COGS": total_cogs,
            "Gross Margin": gross_margin,
            "Total Expenses": total_exp,
            "Net Profit": net_profit,
            "Cash": fin['cash'],
            "Total Assets": fin['cash'] + fin['acct_receivable'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'],
            "Net Worth": fin['retained_earnings'],
            "Avg Rx Price": avg_rx_price
        })
        p['status'] = 'Thinking'
        p['period'] += 1

    # Update Market Share
    for t, p in st.session_state.players.items():
        if p['history']:
            last = p['history'][-1]
            share = (last['Total Sales'] / city_total_sales * 100) if city_total_sales > 0 else 0
            last['Market Share'] = share

    st.session_state.global_period += 1

# ==========================================
# 4. UI Dashboard
# ==========================================
def format_money(val):
    return f"{val:,.0f}"

with st.sidebar:
    st.title("💊 Communi-Pharm V5.5")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team_key = st.selectbox("Select Team", options=list(st.session_state.players.keys()))
        p = st.session_state.players[team_key]
        st.markdown("---")
        new_name = st.text_input("✏️ Shop Name", value=p['shop_name'])
        if new_name != p['shop_name']:
            p['shop_name'] = new_name; st.rerun()
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

# --- STUDENT VIEW (เหมือนเดิม V5.2) ---
if role == "Student":
    p = st.session_state.players[team_key]
    st.header(f"🏥 {p['shop_name']}")
    st.markdown(f"**Period:** {st.session_state.global_period} | **Status:** {p['status']}")
    
    if p['history']:
        last = p['history'][-1]
        hist_df = pd.DataFrame(p['history'])
        to_date = hist_df.sum(numeric_only=True)
        
        st.markdown("### 📄 OPERATING STATEMENT")
        op_data = [
            ["**SALES**", "", ""],
            ["Prescription", format_money(last['Rx Sales']), format_money(to_date['Rx Sales'])],
            ["Other", format_money(last['Other Sales']), format_money(to_date['Other Sales'])],
            ["**TOTAL SALES**", f"**{format_money(last['Total Sales'])}**", f"**{format_money(to_date['Total Sales'])}**"],
            ["", "", ""],
            ["**NET PROFIT**", f"**{format_money(last['Net Profit'])}**", f"**{format_money(to_date['Net Profit'])}**"]
        ]
        st.table(pd.DataFrame(op_data, columns=["ITEM", "THIS PERIOD", "TO DATE"]))
    
    # Input Form
    if p['status'] == 'Thinking':
        with st.expander("📝 Decision Form (36 Items)", expanded=True):
            with st.form("form_36"):
                inputs = p['inputs']
                c1, c2, c3 = st.columns(3)
                for i in range(36):
                    col = [c1, c2, c3][i // 12]
                    if i in [3,4,5,32,33,34]:
                        inputs[i] = col.selectbox(INPUT_LABELS[i], [0,1], index=int(inputs[i]))
                    else:
                        inputs[i] = col.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                if st.form_submit_button("Submit"):
                    p['inputs'] = inputs; p['status'] = 'Submitted'; st.rerun()

# --- INSTRUCTOR VIEW (NEW SUMMARY TABLE) ---
elif role == "Instructor" and is_admin:
    st.title("👨‍🏫 INSTRUCTOR'S SUMMARY")
    st.markdown(f"**Current Period:** {st.session_state.global_period}")

    # ปุ่ม Run Process
    if st.button("🚀 Process Period (ประมวลผลรอบปัจจุบัน)"):
        process_period()
        st.success("Simulation Complete!")
        st.rerun()

    st.markdown("---")
    
    # 1. เช็คว่ามีข้อมูล History หรือไม่
    has_history = any(len(p['history']) > 0 for p in st.session_state.players.values())
    
    if has_history:
        # เตรียมข้อมูลสำหรับตาราง Summary
        # Rows = รายการบัญชี (Sales, Profit, etc.)
        # Cols = ชื่อร้าน (Team 1, Team 2...)
        
        summary_dict = {}
        
        # รายการที่จะแสดงในแถว (Row Labels) - เรียงตาม PDF ตัวอย่าง
        metrics = [
            "Total Sales", "Rx Sales", "Other Sales",
            "Total COGS", "Gross Margin", "Total Expenses", "Net Profit",
            "Cash", "Total Assets", "Net Worth", "Avg Rx Price", "Market Share"
        ]
        
        for team_id, p in st.session_state.players.items():
            if p['history']:
                last = p['history'][-1]
                # สร้าง Column สำหรับทีมนี้
                col_name = f"{p['shop_name']} ({team_id})"
                
                # ดึงค่าตาม Metrics
                team_values = []
                for m in metrics:
                    val = last.get(m, 0)
                    # Format
                    if m == "Avg Rx Price":
                        team_values.append(f"${val:,.2f}")
                    elif m == "Market Share":
                        team_values.append(f"{val:,.1f}%")
                    else:
                        team_values.append(f"${val:,.0f}")
                
                summary_dict[col_name] = team_values
        
        # สร้าง DataFrame
        df_summary = pd.DataFrame(summary_dict, index=metrics)
        
        st.subheader(f"📊 CITY SUMMARY STATISTICS (Period {st.session_state.global_period - 1})")
        # แสดงผลตาราง
        st.dataframe(df_summary, use_container_width=True)
        
        st.markdown("""
        **Note:** ตารางนี้แสดงผลเปรียบเทียบทุกร้านในเมือง (City) 
        เพื่อให้เห็นยอดขายและสถานะทางการเงินเทียบกัน (เหมือนหน้า 2 ของไฟล์รายงาน)
        """)

    else:
        st.info("ยังไม่มีข้อมูลการเล่น (No simulation data yet)")
        
    # Status Table (ใครส่งแล้วบ้าง)
    st.markdown("---")
    st.subheader("สถานะการส่งข้อมูล (Submission Status)")
    status_data = [
        {"Team": t, "Name": p['shop_name'], "Status": "✅ READY" if p['status']=='Submitted' else "⏳ Thinking"}
        for t,p in st.session_state.players.items()
    ]
    st.dataframe(pd.DataFrame(status_data), hide_index=True)
