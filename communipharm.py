import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm: Computer Printout", layout="wide")
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
        # Default values
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=20.0; inputs[19]=6.0; inputs[20]=8000.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Pharmacy {i}",
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 
                'acct_receivable': 2000.0,
                'inventory_rx': 20000.0, 
                'inventory_otc': 15000.0,
                'fixed_assets': 50000.0,
                'acct_payable': 5000.0,
                'notes_payable': 0.0,
                'long_term_debt': 30000.0,
                'retained_earnings': 92000.0 
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
        
        # --- Revenue ---
        rx_markup = inp[0] if inp[0] > 0 else 1
        promo_impact = 1 + (inp[7] / 10000)
        service_impact = 1 + (sum([inp[3], inp[4], inp[5], inp[32], inp[33], inp[34]]) * 0.03)
        
        total_sales = (45000 + 25000) * promo_impact * service_impact
        rx_sales = total_sales * 0.65
        otc_sales = total_sales * 0.35
        
        # --- COGS ---
        cost_rx = rx_sales / (1 + (rx_markup/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        total_cogs = cost_rx + cost_otc
        
        # Update Inventory
        fin['inventory_rx'] += inp[14] - cost_rx
        fin['inventory_otc'] += inp[15] - cost_otc
        
        # --- Expenses (Detailed for Report) ---
        weeks = 13; hours = inp[6]
        # Payroll
        pay_pharm = inp[16] * inp[17] * hours * weeks
        pay_clerk = inp[18] * inp[19] * hours * weeks
        pay_mgr = inp[20]
        total_payroll = pay_pharm + pay_clerk + pay_mgr
        
        # Ops Expenses (Simulated/Estimated)
        exp_rent = inp[23] if inp[23] > 0 else 2500.0 # Mortgage/Rent
        exp_util = 1200.0
        exp_repair = 300.0
        exp_ins = 400.0
        exp_tax = 350.0
        exp_legal = 500.0
        exp_ads = inp[7]
        exp_depr = fin['fixed_assets'] * 0.02
        exp_int = (fin['long_term_debt'] * 0.02) + (fin['notes_payable'] * 0.04)
        exp_misc = 500.0
        
        total_exp = total_payroll + exp_rent + exp_util + exp_repair + exp_ins + exp_tax + exp_legal + exp_ads + exp_depr + exp_int + exp_misc
        
        # Profit
        gross_margin = total_sales - total_cogs
        net_profit = gross_margin - total_exp
        
        # --- Cash Flow ---
        cash_in = total_sales * 0.95 + inp[29] # Sales + New Loan
        cash_out = (total_exp - exp_depr) + (inp[14]+inp[15]) + (inp[28]+inp[30]) # Exp + Buy + DebtPay
        net_cash = cash_in - cash_out
        
        fin['cash'] += net_cash
        fin['retained_earnings'] += net_profit
        
        # Emergency Loan Check
        if fin['cash'] < 0:
            loan = abs(fin['cash']) + 1000
            fin['notes_payable'] += loan
            fin['cash'] += loan

        # --- Save Report Data (Detailed) ---
        report = {
            "Period": st.session_state.global_period,
            # Sales
            "Sales_Rx": rx_sales, "Sales_Oth": otc_sales, "Sales_Tot": total_sales,
            # COGS
            "COGS_Rx": cost_rx, "COGS_Oth": cost_otc, "COGS_Tot": total_cogs,
            "Gross_Margin": gross_margin,
            # Expenses
            "Exp_Payroll": total_payroll,
            "Exp_Rent": exp_rent,
            "Exp_Util": exp_util,
            "Exp_Repair": exp_repair,
            "Exp_Supplies": 200.0, # Dummy
            "Exp_Ins": exp_ins,
            "Exp_Tax": exp_tax,
            "Exp_Legal": exp_legal,
            "Exp_Ads": exp_ads,
            "Exp_Depr": exp_depr,
            "Exp_Int": exp_int,
            "Exp_Misc": exp_misc,
            "Exp_Total": total_exp,
            "Net_Profit": net_profit,
            # Cash Flow
            "Cash_Beg": fin['cash'] - net_cash, # Estimate
            "Cash_In": cash_in,
            "Cash_Out": cash_out,
            "Cash_End": fin['cash'],
            # Balance Sheet
            "BS_Cash": fin['cash'], "BS_AR": fin['acct_receivable'], 
            "BS_Inv": fin['inventory_rx']+fin['inventory_otc'], "BS_Fixed": fin['fixed_assets'],
            "BS_AP": fin['acct_payable'], "BS_Note": fin['notes_payable'], 
            "BS_Long": fin['long_term_debt'], "BS_Equity": fin['retained_earnings']
        }
        
        p['history'].append(report)
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. User Interface (Printout Style)
# ==========================================
def format_money(val):
    return f"{val:,.0f}"

with st.sidebar:
    st.title("💊 Communi-Pharm V5.0")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Team", options=list(st.session_state.players.keys()), 
                            format_func=lambda x: f"{st.session_state.players[x]['shop_name']} ({x})")
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    
    # Header
    st.markdown(f"## 🏥 {p['shop_name']}")
    st.markdown(f"**PERIOD:** {st.session_state.global_period} | **STATUS:** {p['status']}")
    
    # === PRINTOUT SECTION ===
    if p['history']:
        last = p['history'][-1]
        
        # Calculate TO DATE (Cumulative)
        # นำประวัติทั้งหมดมารวมกันเพื่อหาค่าสะสม (To Date)
        hist_df = pd.DataFrame(p['history'])
        to_date = hist_df.sum(numeric_only=True)
        
        # ----------------------------------------------------
        # 1. OPERATING STATEMENT (งบกำไรขาดทุน)
        # ----------------------------------------------------
        st.markdown("### OPERATING STATEMENT")
        
        # Prepare Data Rows
        rows = [
            ["SALES", "", ""],
            ["  Prescription", format_money(last['Sales_Rx']), format_money(to_date['Sales_Rx'])],
            ["  Other", format_money(last['Sales_Oth']), format_money(to_date['Sales_Oth'])],
            ["  TOTAL SALES", format_money(last['Sales_Tot']), format_money(to_date['Sales_Tot'])],
            ["COST OF GOODS SOLD", "", ""],
            ["  Prescription", format_money(last['COGS_Rx']), format_money(to_date['COGS_Rx'])],
            ["  Other", format_money(last['COGS_Oth']), format_money(to_date['COGS_Oth'])],
            ["  TOTAL COGS", format_money(last['COGS_Tot']), format_money(to_date['COGS_Tot'])],
            ["GROSS MARGIN", format_money(last['Gross_Margin']), format_money(to_date['Gross_Margin'])],
            ["EXPENSES", "", ""],
            ["  Payroll", format_money(last['Exp_Payroll']), format_money(to_date['Exp_Payroll'])],
            ["  Rent", format_money(last['Exp_Rent']), format_money(to_date['Exp_Rent'])],
            ["  Utilities", format_money(last['Exp_Util']), format_money(to_date['Exp_Util'])],
            ["  Repairs", format_money(last['Exp_Repair']), format_money(to_date['Exp_Repair'])],
            ["  Supplies", format_money(last['Exp_Supplies']), format_money(to_date['Exp_Supplies'])],
            ["  Insurance", format_money(last['Exp_Ins']), format_money(to_date['Exp_Ins'])],
            ["  Taxes", format_money(last['Exp_Tax']), format_money(to_date['Exp_Tax'])],
            ["  Acct & Legal", format_money(last['Exp_Legal']), format_money(to_date['Exp_Legal'])],
            ["  Advertising", format_money(last['Exp_Ads']), format_money(to_date['Exp_Ads'])],
            ["  Depreciation", format_money(last['Exp_Depr']), format_money(to_date['Exp_Depr'])],
            ["  Interest", format_money(last['Exp_Int']), format_money(to_date['Exp_Int'])],
            ["  Miscellaneous", format_money(last['Exp_Misc']), format_money(to_date['Exp_Misc'])],
            ["  TOTAL EXPENSES", format_money(last['Exp_Total']), format_money(to_date['Exp_Total'])],
            ["NET PROFIT", format_money(last['Net_Profit']), format_money(to_date['Net_Profit'])]
        ]
        
        df_op = pd.DataFrame(rows, columns=["ITEM", "THIS PERIOD", "TO DATE"])
        st.table(df_op) # ใช้ st.table เพื่อให้หน้าตาเหมือนกระดาษรายงานที่สุด

        col_L, col_R = st.columns(2)
        
        # ----------------------------------------------------
        # 2. CASH FLOW STATEMENT
        # ----------------------------------------------------
        with col_L:
            st.markdown("### CASH FLOW STATEMENT")
            cf_rows = [
                ["Beg. Cash Balance", format_money(last['Cash_Beg'])],
                ["Sources of Cash (In)", format_money(last['Cash_In'])],
                ["Uses of Cash (Out)", format_money(last['Cash_Out'])],
                ["Ending Cash Balance", format_money(last['Cash_End'])]
            ]
            st.table(pd.DataFrame(cf_rows, columns=["ITEM", "AMOUNT"]))

        # ----------------------------------------------------
        # 3. BALANCE SHEET
        # ----------------------------------------------------
        with col_R:
            st.markdown("### BALANCE SHEET")
            bs_rows = [
                ["ASSETS", ""],
                ["  Cash", format_money(last['BS_Cash'])],
                ["  Acct Receivable", format_money(last['BS_AR'])],
                ["  Inventory", format_money(last['BS_Inv'])],
                ["  Fixed Assets", format_money(last['BS_Fixed'])],
                ["TOTAL ASSETS", format_money(last['BS_Cash']+last['BS_AR']+last['BS_Inv']+last['BS_Fixed'])],
                ["LIABILITIES", ""],
                ["  Acct Payable", format_money(last['BS_AP'])],
                ["  Notes Payable", format_money(last['BS_Note'])],
                ["  Long Term Debt", format_money(last['BS_Long'])],
                ["EQUITY (Net Worth)", format_money(last['BS_Equity'])]
            ]
            st.table(pd.DataFrame(bs_rows, columns=["ITEM", "AMOUNT"]))

    # === INPUT SECTION ===
    if p['status'] == 'Thinking':
        st.markdown("---")
        with st.expander("📝 Decision Form (36 Items)", expanded=True):
            with st.form("form_printout_36"):
                inputs = p['inputs']
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    for i in range(0, 12):
                         # Yes/No Selectbox for Items 4,5,6
                        if i in [3, 4, 5]: 
                            inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]))
                        else:
                            inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                with c2:
                    for i in range(12, 24):
                        inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))
                with c3:
                    for i in range(24, 36):
                         # Yes/No Selectbox for Items 33,34,35
                        if i in [32, 33, 34]:
                            inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]))
                        else:
                            inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]))

                if st.form_submit_button("✅ Submit Decisions"):
                    p['inputs'] = inputs
                    p['status'] = 'Submitted'
                    st.rerun()
    elif p['status'] == 'Submitted':
        if st.button("Edit Inputs"):
            p['status'] = 'Thinking'; st.rerun()

elif role == "Instructor" and is_admin:
    st.title("Instructor Panel")
    if st.button("Run Simulation"):
        process_period()
        st.success("Run Complete!")
        st.rerun()
