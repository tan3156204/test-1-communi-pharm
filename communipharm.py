import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config & Setup
# ==========================================
st.set_page_config(page_title="Communi-Pharm: Instructor Page 2", layout="wide")
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
        team_id = f"Team {i}"
        # Default Inputs
        inputs = [0.0] * 36
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=20.0; inputs[19]=6.0; inputs[20]=8000.0
        inputs[23]=40.0 # Manager Hours
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}",
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
    for t, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        inp = p['inputs']
        fin = p['financials']
        
        # --- Revenue ---
        rx_markup = inp[0] if inp[0] > 0 else 1
        promo_impact = 1 + (inp[7] / 10000)
        service_impact = 1 + (sum([inp[3], inp[4], inp[5], inp[32], inp[33], inp[34]]) * 0.03)
        
        total_sales = (45000 + 25000) * promo_impact * service_impact
        rx_sales = total_sales * 0.65
        otc_sales = total_sales * 0.35
        
        # --- Costs ---
        cost_rx = rx_sales / (1 + (rx_markup/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cost_rx + cost_otc
        
        # Update Inv
        fin['inventory_rx'] += inp[14] - cost_rx
        fin['inventory_otc'] += inp[15] - cost_otc
        
        # --- Expenses ---
        weeks = 13; hours = inp[6]
        payroll = (inp[16]*inp[17] + inp[18]*inp[19])*hours*weeks + inp[20]
        
        exp_rent = inp[23] if inp[23] > 0 else 2500.0
        total_exp = payroll + exp_rent + inp[7] + (fin['fixed_assets']*0.02) + 2000 # Misc
        
        gross_margin = total_sales - total_cogs
        net_profit = gross_margin - total_exp
        
        # Cash
        cash_in = total_sales * 0.95 + inp[29]
        cash_out = (total_exp - (fin['fixed_assets']*0.02)) + inp[14] + inp[15] + inp[30]
        fin['cash'] += (cash_in - cash_out)
        fin['retained_earnings'] += net_profit
        
        if fin['cash'] < 0:
            fin['notes_payable'] += abs(fin['cash']) + 1000
            fin['cash'] += abs(fin['cash']) + 1000
            
        # Stats for Page 2
        avg_rx_price = 10.0 * (1 + rx_markup/100) + inp[1]
        roi = (net_profit / fin['retained_earnings']) if fin['retained_earnings'] else 0
        
        p['history'].append({
            "Period": st.session_state.global_period,
            # Financials for Matrix
            "TOT SALES": total_sales,
            "Rx SALES": rx_sales,
            "OTH SALES": otc_sales,
            "Avg Rx Pr": avg_rx_price,
            "TOT COGS": total_cogs,
            "GROSS MARGIN": gross_margin,
            "TOT EXPENSES": total_exp,
            "NET PROFIT": net_profit,
            "CASH": fin['cash'],
            "NET WORTH": fin['retained_earnings'],
            # Stats for Bottom Table
            "Wage/Hr": inp[17], # Pharmacist Pay
            "Hrs Wked": inp[22], # Mgr Hours
            "Pt Rec": inp[4],
            "Del Ser": inp[3],
            "Store Credit": inp[5],
            "Copay Dsct": inp[2],
            "Hrs Open": inp[6],
            "ROI": roi,
            "Life Ins": inp[32],
            "Hlt Ins": inp[33]
        })
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI Display
# ==========================================
def format_money(val): return f"${val:,.0f}"
def format_dec(val): return f"${val:,.2f}"

with st.sidebar:
    st.title("💊 Communi-Pharm V6.0")
    role = st.selectbox("Role", ["Student", "Instructor"])
    if role == "Student":
        team = st.selectbox("Team", list(st.session_state.players.keys()))
        new_name = st.text_input("Change Name", st.session_state.players[team]['shop_name'])
        st.session_state.players[team]['shop_name'] = new_name
    else:
        pwd = st.text_input("Password", type="password")

# --- INSTRUCTOR: PAGE 2 OUTPUT ---
if role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.markdown(f"## INSTRUCTOR'S SUMMARY FOR CITY # 1")
    st.markdown(f"**Current Period # {st.session_state.global_period - 1}**")
    
    if st.button("Run Simulation"):
        process_period()
        st.rerun()
        
    st.markdown("---")
    
    # Check Data
    has_data = any(len(p['history']) > 0 for p in st.session_state.players.values())
    if has_data:
        # ==================================
        # 1. FINANCIAL MATRIX (Page 2 Top)
        # ==================================
        # Rows defined exactly as per PDF snippet
        row_labels = [
            "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", 
            "TOT COGS", "GROSS MARGIN", "TOT EXPENSES", "NET PROFIT", 
            "CASH", "NET WORTH"
        ]
        
        matrix_data = {}
        for t_id, p in st.session_state.players.items():
            if p['history']:
                last = p['history'][-1]
                col = p['shop_name']
                vals = []
                for lbl in row_labels:
                    v = last.get(lbl, 0)
                    if lbl == "Avg Rx Pr": vals.append(format_dec(v))
                    else: vals.append(format_money(v))
                matrix_data[col] = vals
                
        df_matrix = pd.DataFrame(matrix_data, index=row_labels)
        st.table(df_matrix)
        
        # ==================================
        # 2. CITY SUMMARY STATISTICS (Page 2 Bottom)
        # ==================================
        st.markdown("### CITY SUMMARY STATISTICS")
        
        stats_rows = []
        for t_id, p in st.session_state.players.items():
            if p['history']:
                last = p['history'][-1]
                stats_rows.append({
                    "Store Name": p['shop_name'],
                    "Wage/Hr": f"${last['Wage/Hr']:.2f}",
                    "Hrs Wked": f"{last['Hrs Wked']:.0f}",
                    "Pt Rec": "Yes" if last['Pt Rec'] else "No",
                    "Del Ser": "Yes" if last['Del Ser'] else "No",
                    "Credit": "Yes" if last['Store Credit'] else "No",
                    "Copay": f"${last['Copay Dsct']:.2f}",
                    "Hrs Open": f"{last['Hrs Open']:.0f}",
                    "ROI": f"{last['ROI']:.2f}",
                    "Life Ins": "Yes" if last['Life Ins'] else "No",
                    "Hlt Ins": "Yes" if last['Hlt Ins'] else "No"
                })
                
        df_stats = pd.DataFrame(stats_rows)
        # Reorder columns to match snippet loosely
        cols = ["Store Name", "Wage/Hr", "Hrs Wked", "Pt Rec", "Del Ser", "Credit", "Copay", "Hrs Open", "ROI", "Life Ins", "Hlt Ins"]
        st.table(df_stats[cols])

# --- STUDENT VIEW (Basic) ---
elif role == "Student":
    p = st.session_state.players[team]
    st.header(f"🏥 {p['shop_name']}")
    if p['status'] == 'Thinking':
        with st.form("input_form"):
            c1, c2, c3 = st.columns(3)
            # Shortened input form for brevity in this snippet
            for i in range(36):
                col = [c1,c2,c3][i//12]
                val = p['inputs'][i]
                if i in [3,4,5,32,33,34]:
                    p['inputs'][i] = col.selectbox(INPUT_LABELS[i], [0,1], index=int(val))
                else:
                    p['inputs'][i] = col.number_input(INPUT_LABELS[i], value=float(val))
            if st.form_submit_button("Submit"):
                p['status'] = 'Submitted'
                st.rerun()
    else:
        st.success("Decisions Submitted. Waiting for Instructor.")
