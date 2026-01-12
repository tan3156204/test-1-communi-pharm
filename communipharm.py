import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V4.1 (Dashboard)", layout="wide")
ADMIN_PASSWORD = "admin1234"

# รายชื่อตัวแปร 36 ข้อ (Labels)
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
                'cash': 40000.0, 
                'inventory_rx': 20000.0, 'inventory_otc': 15000.0,
                'investments': 0.0, 'emergency_loan': 0.0,
                'long_term_debt': 0.0, 'accounts_payable': 0.0
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
        
        # --- Mapping ---
        rx_markup = inp[0]
        promo_total = inp[7]
        service_score = inp[3] + inp[4] + inp[5] + inp[32] + inp[33] + inp[34]
        
        # --- Revenue ---
        base_sales = 60000 
        price_factor = (50 / rx_markup) * 1.05 if rx_markup > 0 else 0
        promo_factor = 1 + (promo_total / 8000)
        service_factor = 1 + (service_score * 0.05)
        
        total_revenue = base_sales * price_factor * promo_factor * service_factor
        rx_sales = total_revenue * 0.65
        otc_sales = total_revenue * 0.35
        
        # --- Expenses ---
        # COGS
        cogs_rx = rx_sales / (1 + (rx_markup/100))
        cogs_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cogs_rx + cogs_otc
        
        # Wages
        weeks = 13
        hours = inp[6]
        wages = ((inp[16]*inp[17]) + (inp[18]*inp[19])) * hours * weeks
        mgr_sal = inp[20]
        
        # Ops
        rent_mortgage = inp[23]
        promo_exp = inp[7]
        other_exp = 3000.0 # Fixed Estimate
        interest = (fin['long_term_debt'] * 0.02) + (fin['emergency_loan'] * 0.05)
        
        total_expenses = wages + mgr_sal + rent_mortgage + promo_exp + other_exp + interest
        
        # Profit
        gross_margin = total_revenue - total_cogs
        net_profit = gross_margin - total_expenses
        
        # --- Cash Flow ---
        cash_in = total_revenue + inp[11]
        cash_out_ops = total_expenses
        cash_out_purchases = inp[14] + inp[15]
        cash_out_invest = inp[9]
        cash_out_debt = inp[28] + inp[30] + inp[35] # AP + Debt + HMO
        
        total_cash_out = cash_out_ops + cash_out_purchases + cash_out_invest + cash_out_debt
        fin['cash'] += (cash_in - total_cash_out)
        
        # Update Assets/Liabilities
        fin['inventory_rx'] += (inp[14] - cogs_rx)
        fin['inventory_otc'] += (inp[15] - cogs_otc)
        fin['investments'] += (inp[9] - inp[11])
        fin['long_term_debt'] -= inp[30]
        
        # Emergency Loan
        if fin['cash'] < 0:
            loan = abs(fin['cash']) + 2000
            fin['emergency_loan'] += loan
            fin['cash'] += loan
            
        # บันทึกข้อมูลละเอียดเพื่อทำ Report สวยๆ
        report_data = {
            "Period": st.session_state.global_period,
            "Sales (Total)": total_revenue,
            "Sales (Rx)": rx_sales,
            "Sales (OTC)": otc_sales,
            "COGS": total_cogs,
            "Gross Margin": gross_margin,
            "Expenses (Total)": total_expenses,
            "Wages": wages + mgr_sal,
            "Rent/Mortgage": rent_mortgage,
            "Promo": promo_exp,
            "Interest": interest,
            "Net Profit": net_profit,
            "Cash": fin['cash'],
            "Inventory": fin['inventory_rx'] + fin['inventory_otc'],
            "Emergency Loan": fin['emergency_loan']
        }
        
        p['history'].append(report_data)
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI Dashboard (Beautiful Output)
# ==========================================
def format_team_name(team_id):
    return f"{st.session_state.players[team_id]['shop_name']} ({team_id})"

with st.sidebar:
    st.title("💊 Communi-Pharm V4.1")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Select Team", options=list(st.session_state.players.keys()), format_func=format_team_name)
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    
    # --- Header ---
    st.markdown(f"## 🏥 {p['shop_name']}")
    st.markdown(f"**Period:** {st.session_state.global_period} | **Status:** {'✅ Submitted' if p['status']=='Submitted' else '✏️ Thinking'}")

    # --- ส่วนแสดงผล (OUTPUT SECTION) ---
    if p['history']:
        last = p['history'][-1]
        
        # 1. Top KPIs (ตัวเลขใหญ่ๆ ดูง่าย)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("ยอดขายรวม (Total Sales)", f"${last['Sales (Total)']:,.0f}", delta=None)
        kpi2.metric("กำไรสุทธิ (Net Profit)", f"${last['Net Profit']:,.0f}", delta_color="normal")
        kpi3.metric("เงินสดคงเหลือ (Cash)", f"${last['Cash']:,.0f}")
        kpi4.metric("หนี้ฉุกเฉิน (Emerg. Loan)", f"${last['Emergency Loan']:,.0f}", delta_color="inverse")
        
        if last['Emergency Loan'] > 0:
            st.warning(f"⚠️ คำเตือน: คุณมีหนี้สินฉุกเฉินจำนวน ${last['Emergency Loan']:,.0f} (ดอกเบี้ยสูง!)")

        st.markdown("---")

        # 2. Detailed Reports (Tabs)
        tab1, tab2, tab3 = st.tabs(["💰 งบกำไรขาดทุน (Income Statement)", "⚖️ งบดุล (Balance Sheet)", "📈 กราฟแนวโน้ม (Trends)"])
        
        with tab1:
            # สร้างตาราง P&L แบบสวยงาม
            st.subheader("Income Statement")
            
            # เตรียมข้อมูลลง DataFrame
            pl_data = {
                "รายการ (Items)": [
                    "Revenue (รายได้รวม)", 
                    "   - Rx Sales", 
                    "   - OTC Sales",
                    "Cost of Goods Sold (ต้นทุนขาย)",
                    "GROSS MARGIN (กำไรขั้นต้น)",
                    "Expenses (ค่าใช้จ่ายดำเนินงาน)",
                    "   - Wages & Salaries",
                    "   - Rent / Mortgage",
                    "   - Advertising",
                    "   - Interest Expense",
                    "   - Other Expenses",
                    "NET PROFIT (กำไรสุทธิ)"
                ],
                "จำนวนเงิน ($)": [
                    last['Sales (Total)'],
                    last['Sales (Rx)'],
                    last['Sales (OTC)'],
                    -last['COGS'],  # ใส่ลบเพื่อให้รู้ว่าเป็นต้นทุน
                    last['Gross Margin'],
                    None, # หัวข้อ
                    -last['Wages'],
                    -last['Rent/Mortgage'],
                    -last['Promo'],
                    -last['Interest'],
                    -3000.0,
                    last['Net Profit']
                ]
            }
            df_pl = pd.DataFrame(pl_data)
            # Format ตัวเลขให้สวยงาม
            st.dataframe(
                df_pl.style.format({"จำนวนเงิน ($)": "${:,.2f}"}, na_rep=""), 
                use_container_width=True, 
                hide_index=True
            )

        with tab2:
            st.subheader("Balance Sheet (Simplified)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Assets (สินทรัพย์)")
                assets = {
                    "Cash": last['Cash'],
                    "Inventory": last['Inventory'],
                    "Investments": p['financials']['investments']
                }
                df_ast = pd.DataFrame(list(assets.items()), columns=["รายการ", "มูลค่า ($)"])
                st.dataframe(df_ast.style.format({"มูลค่า ($)": "${:,.2f}"}), hide_index=True)
                st.info(f"**Total Assets:** ${sum(assets.values()):,.2f}")
                
            with c2:
                st.markdown("#### Liabilities (หนี้สิน)")
                liabilities = {
                    "Emergency Loan": last['Emergency Loan'],
                    "Long Term Debt": p['financials']['long_term_debt'],
                    "Accounts Payable": 0.0 # (Simplified logic)
                }
                df_lia = pd.DataFrame(list(liabilities.items()), columns=["รายการ", "มูลค่า ($)"])
                st.dataframe(df_lia.style.format({"มูลค่า ($)": "${:,.2f}"}), hide_index=True)
                st.error(f"**Total Liabilities:** ${sum(liabilities.values()):,.2f}")

        with tab3:
            st.subheader("Performance Trend")
            # ดึงประวัติทั้งหมดมาทำกราฟ
            if len(p['history']) > 0:
                hist_df = pd.DataFrame(p['history'])
                st.line_chart(hist_df, x="Period", y=["Sales (Total)", "Net Profit", "Cash"])
            else:
                st.write("ยังไม่มีข้อมูลประวัติ")

    # --- ส่วนกรอกข้อมูล (INPUT SECTION) ---
    if p['status'] == 'Thinking':
        st.markdown("---")
        with st.expander("📝 กรอกแบบฟอร์มตัดสินใจ (Decision Form)", expanded=True):
            with st.form("form_exact_36_dash"):
                st.info("กรอกข้อมูล 36 ข้อตามคู่มือ")
                
                inputs = p['inputs']
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("##### Section 1")
                    for i in range(0, 12):
                        if i in [3, 4, 5]: # Yes/No items
                            inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]), key=f"in_{i}")
                        else:
                            inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]), key=f"in_{i}")

                with c2:
                    st.markdown("##### Section 2")
                    for i in range(12, 24):
                        inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]), key=f"in_{i}")

                with c3:
                    st.markdown("##### Section 3")
                    for i in range(24, 36):
                        if i in [32, 33, 34]: # Yes/No items
                            inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]), key=f"in_{i}")
                        else:
                            inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]), key=f"in_{i}")

                if st.form_submit_button("✅ Submit Decisions"):
                    p['inputs'] = inputs
                    p['status'] = 'Submitted'
                    st.rerun()

    elif p['status'] == 'Submitted':
        if st.button("แก้ไขข้อมูล (Edit)"):
            p['status'] = 'Thinking'
            st.rerun()

elif role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Panel")
    if st.button("🚀 Process Period"):
        process_period()
        st.success("Processed!")
        st.rerun()
    
    st.dataframe(pd.DataFrame([
        {"Team": t, "Shop": p['shop_name'], "Status": p['status'], "Cash": f"${p['financials']['cash']:,.0f}"} 
        for t,p in st.session_state.players.items()
    ]))
