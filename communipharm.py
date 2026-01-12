import streamlit as st
import pandas as pd
import numpy as np
import random

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V8.0", layout="wide")
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

LOCATION_MAP = {1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# ==========================================
# 2. State Management & Initialization
# ==========================================
def initialize_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1
    
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        inputs = [0.0] * 36
        # Defaults
        inputs[0]=50.0; inputs[1]=3.0; inputs[2]=3.0; inputs[3]=1; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=2.0; inputs[18]=20.0; inputs[19]=2.0; inputs[20]=6.0; inputs[21]=8000.0
        inputs[23]=40.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}", 
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 'acct_receivable': 2000.0,
                'inventory_rx': 25000.0, 'inventory_otc': 15000.0,
                'fixed_assets': 50000.0, 'acct_payable': 5000.0,
                'notes_payable': 0.0, 'long_term_debt': 30000.0,
                'retained_earnings': 92000.0 
            },
            'history': []
        }

if 'players' not in st.session_state:
    initialize_game(5) 

# ==========================================
# 3. Game Logic (Advanced Calculation)
# ==========================================
def process_period():
    # 1. Calculate City Totals first (for Market Share)
    city_rx_sales = 0
    
    # Temporary storage for calculation results
    calc_results = {}

    for t, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        
        inp = p['inputs']
        fin = p['financials']
        
        # --- SALES ---
        rx_markup = inp[0] if inp[0] > 0 else 1
        promo_impact = 1 + (inp[7] / 10000)
        service_impact = 1 + (sum([inp[3], inp[4], inp[5], inp[32], inp[33], inp[34]]) * 0.03)
        
        base_sales = (50000 + 30000) * promo_impact * service_impact
        rx_sales = base_sales * 0.65
        otc_sales = base_sales * 0.35
        tot_sales = rx_sales + otc_sales
        city_rx_sales += rx_sales
        
        # --- COGS ---
        cost_rx = rx_sales / (1 + (rx_markup/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        tot_cogs = cost_rx + cost_otc
        
        # Inventory Check (Emergency Purchase Logic)
        e_rx_pur = 0
        e_otc_pur = 0
        
        fin['inventory_rx'] += inp[14] - cost_rx
        if fin['inventory_rx'] < 0:
            e_rx_pur = abs(fin['inventory_rx']) * 1.1 # Penalty cost
            fin['inventory_rx'] = 0 # Reset to 0
            
        fin['inventory_otc'] += inp[15] - cost_otc
        if fin['inventory_otc'] < 0:
            e_otc_pur = abs(fin['inventory_otc']) * 1.1
            fin['inventory_otc'] = 0

        # --- EXPENSES ---
        weeks = 13
        store_hrs = inp[6]
        
        # Payroll & Overtime Logic
        # Pharmacist
        pharm_hrs_req = store_hrs * inp[16] * weeks
        rp_base_wage = inp[17] * store_hrs * weeks * inp[16] # Simplified
        rp_overtime = 0 # Placeholder for simulation logic
        if store_hrs > 40: rp_overtime = (store_hrs - 40) * inp[16] * weeks * inp[17] * 1.5
        
        # Clerk
        clk_base_wage = inp[19] * store_hrs * weeks * inp[19] # Simplified
        clk_overtime = 0
        if store_hrs > 40: clk_overtime = (store_hrs - 40) * inp[19] * weeks * inp[19] * 1.5
        
        mgr_pay = inp[20]
        payroll_tot = rp_base_wage + rp_overtime + clk_base_wage + clk_overtime + mgr_pay
        
        exp_rent = inp[23] if inp[23] > 0 else 2500.0
        exp_ads = inp[7]
        exp_depr = fin['fixed_assets'] * 0.02
        exp_int = (fin['long_term_debt'] * 0.02)
        other_ops = 3000.0 
        
        tot_exp = payroll_tot + exp_rent + exp_ads + exp_depr + exp_int + other_ops
        
        # --- PROFIT & CASH ---
        gross_margin = tot_sales - tot_cogs
        net_profit = gross_margin - tot_exp
        
        cash_in = tot_sales * 0.95 + inp[29]
        cash_out = (tot_exp - exp_depr) + inp[14] + inp[15] + inp[30] + e_rx_pur + e_otc_pur
        
        fin['cash'] += (cash_in - cash_out)
        fin['retained_earnings'] += net_profit
        fin['long_term_debt'] -= inp[30]
        
        # Emergency Loan
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 1000
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan
            
        # --- DETAILED METRICS ---
        avg_rx_price = 10.0 * (1 + rx_markup/100) + inp[1]
        tot_rx_count = rx_sales / avg_rx_price if avg_rx_price else 0
        rx_ing_cost = cost_rx / tot_rx_count if tot_rx_count else 0
        rx_gm_pct = ((rx_sales - cost_rx) / rx_sales * 100) if rx_sales else 0
        
        # Third Party Logic (Simulated)
        is_3pty = inp[34] # Input 35
        num_3pty_rx = tot_rx_count * 0.3 if is_3pty == 1 else 0
        gm_3pty_pct = rx_gm_pct * 0.8 if is_3pty == 1 else 0 # Lower margin
        
        # Store Data for Ratios
        calc_results[t] = {
            "p": p, "fin": fin, "inp": inp,
            "rx_sales": rx_sales, "otc_sales": otc_sales, "tot_sales": tot_sales,
            "cost_rx": cost_rx, "cost_otc": cost_otc, "tot_cogs": tot_cogs,
            "avg_rx_price": avg_rx_price, "rx_ing_cost": rx_ing_cost, "rx_gm_pct": rx_gm_pct,
            "tot_rx_count": tot_rx_count, "num_3pty_rx": num_3pty_rx, "gm_3pty_pct": gm_3pty_pct,
            "rp_base": rp_base_wage, "rp_ot": rp_overtime, "clk_base": clk_base_wage, "clk_ot": clk_overtime,
            "adv_exp": exp_ads, "mgr_pay": mgr_pay, "ap_paid": inp[28],
            "e_loan": e_loan, "e_rx_pur": e_rx_pur, "e_otc_pur": e_otc_pur,
            "net_profit": net_profit, "gross_margin": gross_margin, "cash_flow": cash_in - cash_out
        }

    # 2. Final Pass: Calculate Market Share & Ratios, then Save
    for t, data in calc_results.items():
        p = data['p']
        fin = data['fin']
        inp = data['inp']
        
        # Market Share
        rx_mkt_sh = (data['rx_sales'] / city_rx_sales * 100) if city_rx_sales else 0
        
        # RATIOS
        curr_assets = fin['cash'] + fin['acct_receivable'] + fin['inventory_rx'] + fin['inventory_otc']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        ratio_current = curr_assets / curr_liab if curr_liab else 0
        ratio_acid = (fin['cash'] + fin['acct_receivable']) / curr_liab if curr_liab else 0
        
        avg_inv = (fin['inventory_rx'] + fin['inventory_otc']) # Simplified (End Inv)
        ratio_turnover = data['tot_cogs'] / avg_inv if avg_inv else 0
        
        net_worth = fin['retained_earnings']
        tot_assets = curr_assets + fin['fixed_assets']
        
        ratio_roi = (data['net_profit'] / net_worth) if net_worth else 0
        ratio_roa = (data['net_profit'] / tot_assets) if tot_assets else 0
        ratio_gm = (data['gross_margin'] / data['tot_sales']) if data['tot_sales'] else 0
        ratio_profit = (data['net_profit'] / data['tot_sales']) if data['tot_sales'] else 0
        
        tot_debt = curr_liab + fin['long_term_debt']
        ratio_debt_nw = (tot_debt / net_worth) if net_worth else 0
        
        location_name = LOCATION_MAP.get(int(inp[2]), "Unknown") # Input 3 is Location

        # SAVE TO HISTORY
        p['history'].append({
            "Period": st.session_state.global_period,
            # Requested Metrics
            "TOT SALES": data['tot_sales'],
            "Rx SALES": data['rx_sales'],
            "OTH SALES": data['otc_sales'],
            "Avg Rx Pr": data['avg_rx_price'],
            "Rx Ing $": data['rx_ing_cost'],
            "Rx GM%": data['rx_gm_pct'],
            "3-Pty GM%": data['gm_3pty_pct'],
            "Tot #Rx’s": data['tot_rx_count'],
            "3-Pty #Rx": data['num_3pty_rx'],
            "Copay Dis": inp[2], # Input 3
            "OTC M’kup": inp[13], # Input 14
            "Rx Mkt Sh": rx_mkt_sh,
            "Store Hrs": inp[6], # Input 7
            "A/P Paid": inp[28], # Input 29
            "M’age Pay": data['mgr_pay'],
            "E. Loan": data['e_loan'],
            "Mgr Hrs": inp[22], # Input 23
            "RP OverT": data['rp_ot'],
            "RP Hr Pay": inp[17], # Input 18
            "Clk OverT": data['clk_ot'],
            "Clk Wage": inp[19], # Input 20
            "Adv Exp": data['adv_exp'],
            "Net Worth": net_worth,
            "Cash Flow": data['cash_flow'],
            "E Rx Pur": data['e_rx_pur'],
            "E OTC Pur": data['e_otc_pur'],
            # Ratios
            "Current": ratio_current,
            "Acid Test": ratio_acid,
            "Turnover": ratio_turnover,
            "ROI": ratio_roi,
            "ROA": ratio_roa,
            "G Margin": ratio_gm,
            "Profit": ratio_profit,
            "Debt/NW": ratio_debt_nw,
            "LOCATION": location_name
        })
        p['status'] = 'Thinking'
        p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI Dashboard
# ==========================================
def format_val(key, val):
    if key in ["Tot #Rx’s", "3-Pty #Rx", "Store Hrs", "Mgr Hrs"]: return f"{val:,.0f}"
    if "%" in key or key in ["Rx Mkt Sh"]: return f"{val:.2f}%"
    if key in ["Current", "Acid Test", "Turnover", "ROI", "ROA", "G Margin", "Profit", "Debt/NW"]: return f"{val:.2f}"
    if isinstance(val, (int, float)): return f"${val:,.0f}"
    return str(val)

with st.sidebar:
    st.title("💊 Communi-Pharm V8.0")
    role = st.selectbox("Select Role", ["Student", "Instructor"])
    
    if role == "Student":
        team_ids = list(st.session_state.players.keys())
        def get_shop_name(tid): return st.session_state.players[tid]['shop_name']
        
        if not team_ids: st.error("Ask Instructor to Start Game")
        else:
            selected_id = st.selectbox("เลือกร้านของคุณ", options=team_ids, format_func=get_shop_name)
            p = st.session_state.players[selected_id]
            st.markdown("---")
            new_name = st.text_input("✏️ Shop Name", value=p['shop_name'])
            if new_name != p['shop_name']: p['shop_name'] = new_name; st.rerun()

    else: # Instructor
        pwd = st.text_input("Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.markdown("---")
            reset_teams = st.number_input("Teams", 1, 20, len(st.session_state.players))
            if st.button("⚠️ Reset Game", type="primary"):
                initialize_game(reset_teams); st.rerun()

# ==========================================
# 5. Main Content
# ==========================================
if role == "Instructor":
    if pwd == ADMIN_PASSWORD:
        st.header("👨‍🏫 INSTRUCTOR SUMMARY REPORT")
        st.markdown(f"**Period:** {st.session_state.global_period - 1}")
        
        if st.button("🚀 Run Simulation"):
            process_period(); st.rerun()

        has_data = any(len(p['history']) > 0 for p in st.session_state.players.values())
        if has_data:
            # === MASTER SUMMARY TABLE ===
            # List of all requested metrics in order
            row_labels = [
                "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", "Rx GM%", "3-Pty GM%",
                "Tot #Rx’s", "3-Pty #Rx", "Copay Dis", "OTC M’kup", "Rx Mkt Sh", "Store Hrs",
                "A/P Paid", "M’age Pay", "E. Loan", "Mgr Hrs", "RP OverT", "RP Hr Pay", 
                "Clk OverT", "Clk Wage", "Adv Exp", "Net Worth", "Cash Flow", "E Rx Pur", "E OTC Pur",
                "--- RATIOS ---", # Spacer
                "Current", "Acid Test", "Turnover", "ROI", "ROA", "G Margin", "Profit", "Debt/NW",
                "LOCATION"
            ]
            
            matrix_data = {}
            for tid, data in st.session_state.players.items():
                if data['history']:
                    last = data['history'][-1]
                    vals = []
                    for lbl in row_labels:
                        if lbl == "--- RATIOS ---": 
                            vals.append("")
                        else:
                            v = last.get(lbl, 0)
                            vals.append(format_val(lbl, v))
                    matrix_data[data['shop_name']] = vals 
            
            df_out = pd.DataFrame(matrix_data, index=row_labels)
            st.table(df_out)
            
        else:
            st.info("No data yet.")
    else:
        if pwd: st.error("Wrong Password")

elif role == "Student":
    if 'selected_id' in locals():
        st.title(f"🏥 {p['shop_name']}")
        st.markdown(f"**Period:** {st.session_state.global_period} | **Status:** {p['status']}")
        
        if p['status'] == 'Thinking':
            with st.form("decision_form"):
                c1, c2, c3 = st.columns(3)
                inputs = p['inputs']
                for i in range(36):
                    col = [c1, c2, c3][i // 12]
                    with col:
                        if i in [3, 4, 5, 32, 33, 34]: 
                            inputs[i] = st.selectbox(INPUT_LABELS[i], [0, 1], index=int(inputs[i]), key=f"in_{i}")
                        else:
                            inputs[i] = st.number_input(INPUT_LABELS[i], value=float(inputs[i]), key=f"in_{i}")
                st.markdown("---")
                if st.form_submit_button("✅ Submit"):
                    p['inputs'] = inputs; p['status'] = 'Submitted'; st.rerun()
        elif p['status'] == 'Submitted':
            st.success("Submitted. Waiting for Instructor.")
            if p['history']:
                 last = p['history'][-1]
                 st.metric("Net Profit", f"${last['NET PROFIT']:,.0f}")
                 if st.button("Edit Next"): p['status']='Thinking'; st.rerun()
            else:
                 if st.button("Edit"): p['status']='Thinking'; st.rerun()
