import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V4.0 (Exact 36 Inputs)", layout="wide")
ADMIN_PASSWORD = "admin1234"

# รายชื่อตัวแปร 36 ข้อ (ตามที่คุณระบุมาเป๊ะๆ)
INPUT_LABELS = [
    "1. Prescription Markup (%)",
    "2. Prescription Professional Fee ($)",
    "3. Copayment Discount ($)",
    "4. Delivery Service (0=No, 1=Yes)",
    "5. Patient Records (0=No, 1=Yes)",
    "6. Store Offers Credit (0=No, 1=Yes)",
    "7. Hours Pharmacy Open Per Week",
    "8. Promotional Expenditures ($)",
    "9. % Promotion on Rx Department (%)",
    "10. Current Period’s Investment ($)",
    "11. Investment Project Number",
    "12. Investment Withdrawal ($)",
    "13. Investment Withdrawal Project Number",
    "14. Markup on Other Store Items (%)",
    "15. Prescription Inventory Purchases ($)",
    "16. Other Inventory Purchases ($)",
    "17. Number Pharmacists Employed",
    "18. Pharmacist’s Hourly Pay Rate ($)",
    "19. Number Sales Clerks Employed",
    "20. Sales Clerk’s Hourly Pay Rate ($)",
    "21. Manager’s Salary For Period ($)",
    "22. Manager’s Percent Time Rx Dept (%)",
    "23. Number of Hours Worked by Manager Per Week",
    "24. Mortgage Payment ($)",
    "25. Amount Sent to Collection Agency ($)",
    "26. Minimum Cash Balance ($)",
    "27. Prescription Inventory Returned ($)",
    "28. Other Inventory Returned ($)",
    "29. Payment on Accounts Payable ($)",
    "30. Long Term Debt Written ($)",
    "31. Long Term Debt Payment ($)",
    "32. Interest Rate Charged on Accounts Receivable (%)",
    "33. Personal Benefits: Life Insurance (1 = Yes)",
    "34. Personal Benefits: Health Insurance (1 = Yes)",
    "35. Participate in Third-Party Rx’s (1 = Yes)",
    "36. Bid for HMO Contract: 0 = No bid ($)"
]

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_id = f"Team {i}"
        
        # สร้าง Array เก็บค่า 36 ช่อง (Index 0-35)
        # ใส่ค่า Default ไว้บางส่วนเพื่อป้องกันการคำนวณ Error ในรอบแรก
        inputs = [0.0] * 36 
        
        # --- Set Some Reasonable Defaults (Optional) ---
        inputs[0] = 50.0  # Rx Markup
        inputs[1] = 3.0   # Prof Fee
        inputs[6] = 50.0  # Hours Open
        inputs[13] = 45.0 # Other Markup
        inputs[17] = 20.0 # Pharm Wage
        inputs[19] = 6.0  # Clerk Wage
        inputs[20] = 8000.0 # Mgr Salary
        
        st.session_state.players[team_id] = {
            'shop_name': f"Pharmacy {i}",
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 
                'inventory_rx': 20000.0, 
                'inventory_otc': 15000.0,
                'investments': 0.0,
                'emergency_loan': 0.0
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Engine (Mapped to New 36 Inputs)
# ==========================================
def process_period():
    for t, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        
        inp = p['inputs'] # List of 36 items (Index 0 to 35)
        fin = p['financials']
        
        # --- 1. Map Inputs to Variables (For readability) ---
        rx_markup = inp[0]      # Item 1
        rx_fee = inp[1]         # Item 2
        promo_total = inp[7]    # Item 8
        other_markup = inp[13]  # Item 14
        
        # Service Score (Sum of Yes/No items)
        # Delivery(4), Records(5), Credit(6), LifeIns(33), HealthIns(34), 3rdParty(35)
        service_score = inp[3] + inp[4] + inp[5] + inp[32] + inp[33] + inp[34]
        
        # --- 2. Revenue Calculation (Simulation) ---
        # Logic: Markup ต่ำ + Promo สูง + Service ดี = ขายดี
        base_sales = 60000 
        price_factor = (50 / rx_markup) * 1.05 if rx_markup > 0 else 0
        promo_factor = 1 + (promo_total / 8000)
        service_factor = 1 + (service_score * 0.05)
        
        total_revenue = base_sales * price_factor * promo_factor * service_factor
        
        # แยกยอดขาย Rx / OTC (สมมติ 60/40)
        rx_sales = total_revenue * 0.60
        otc_sales = total_revenue * 0.40
        
        # --- 3. Expenses & COGS ---
        # COGS (Cost of Goods Sold)
        cogs_rx = rx_sales / (1 + (rx_markup/100))
        cogs_otc = otc_sales / (1 + (other_markup/100))
        total_cogs = cogs_rx + cogs_otc
        
        # Wages
        # Hours Open (Item 7) * Weeks (13) * Staff Count * Rate
        weeks = 13
        hours_open = inp[6]
        
        pharm_wages = inp[16] * inp[17] * hours_open * weeks
        clerk_wages = inp[18] * inp[19] * hours_open * weeks
        mgr_salary = inp[20] # Item 21
        
        total_wages = pharm_wages + clerk_wages + mgr_salary
        
        # Operating Expenses
        mortgage = inp[23]  # Item 24
        promo_exp = inp[7]  # Item 8
        
        # Fixed Estimate for Utilities/Other (Since removed from input list)
        misc_overhead = 3000.0 
        
        total_expenses = total_wages + mortgage + promo_exp + misc_overhead
        
        # --- 4. Net Profit ---
        gross_margin = total_revenue - total_cogs
        net_profit = gross_margin - total_expenses
        
        # --- 5. Cash Flow Calculation ---
        # Cash In
        cash_in = total_revenue + inp[11] # Sales + Investment Withdrawal (Item 12)
        
        # Cash Out
        # Expenses + Purchases + Investments + Debt Pay + HMO Bid
        cash_out_ops = total_expenses
        cash_out_purchases = inp[14] + inp[15] # Rx Buy (15) + Other Buy (16)
        cash_out_invest = inp[9]               # Investment (10)
        cash_out_debt = inp[28] + inp[30]      # AP (29) + Long Term (31)
        cash_out_hmo = inp[35]                 # HMO Bid (36)
        
        total_cash_out = cash_out_ops + cash_out_purchases + cash_out_invest + cash_out_debt + cash_out_hmo
        
        # Update Balance
        fin['cash'] += (cash_in - total_cash_out)
        fin['investments'] += (inp[9] - inp[11]) # Net Investment
        
        # Check Emergency Loan
        min_cash = inp[25] # Minimum Cash Balance (Item 26) - Desired buffer
        if fin['cash'] < 0:
            loan_needed = abs(fin['cash']) + 2000
            fin['emergency_loan'] += loan_needed
            fin['cash'] += loan_needed
            
        # History
        p['history'].append({
            "Period": st.session_state.global_period,
            "Sales": total_revenue,
            "Net Profit": net_profit,
            "Cash": fin['cash']
        })
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
    st.title("💊 Communi-Pharm V4.0")
    st.caption("Standard 36-Input Version")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Team", options=list(st.session_state.players.keys()), format_func=format_team_name)
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    st.header(f"🏥 {p['shop_name']}")
    
    if p['status'] == 'Submitted':
        st.success("✅ Decisions Submitted")
        if st.button("Edit Decisions"):
            p['status'] = 'Thinking'; st.rerun()
    else:
        with st.form("form_exact_36"):
            st.subheader("📝 Decision Form (36 Items)")
            st.info("Please fill in all 36 fields exactly as they appear in your manual.")
            
            inputs = p['inputs']
            
            # Divide into 3 logical columns for easier entry
            c1, c2, c3 = st.columns(3)
            
            # --- Column 1: Items 1-12 ---
            with c1:
                st.markdown("##### Section 1: Pricing & Investment")
                for i in range(0, 12):
                    # Checkbox logic for items 4,5,6 (Indices 3,4,5)
                    if i in [3, 4, 5]: 
                        val = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]))
                    else:
                        val = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                    inputs[i] = val

            # --- Column 2: Items 13-24 ---
            with c2:
                st.markdown("##### Section 2: Inventory & Staff")
                for i in range(12, 24):
                    val = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                    inputs[i] = val

            # --- Column 3: Items 25-36 ---
            with c3:
                st.markdown("##### Section 3: Finance & Benefits")
                for i in range(24, 36):
                    # Checkbox logic for items 33,34,35 (Indices 32,33,34)
                    if i in [32, 33, 34]:
                        val = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]))
                    else:
                        val = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                    inputs[i] = val

            if st.form_submit_button("✅ Submit All 36 Decisions"):
                p['inputs'] = inputs
                p['status'] = 'Submitted'
                st.rerun()

elif role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Panel")
    if st.button("Run Simulation Period"):
        process_period()
        st.success("Period Processed!")
        st.rerun()
    
    st.write("---")
    st.write("Current Player Data:")
    st.json(st.session_state.players)
