import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Configuration
# ==========================================
st.set_page_config(page_title="Communi-Pharm V10.0", layout="wide")
ADMIN_PASSWORD = "admin"

# 36 Player Inputs
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

# Output Columns
REPORT_COLUMNS = [
    "Rank", "Store Name", "LOCATION", "Net Profit", "ROI", 
    "TOT SALES", "Rx SALES", "OTH SALES", "Rx Mkt Sh",
    "Avg Rx Pr", "Rx Ing $", "Rx GM%", "3-Pty GM%",
    "Tot #Rx’s", "3-Pty #Rx", "Copay Dis", "OTC M’kup",
    "Store Hrs", "A/P Paid", "M’age Pay", "E. Loan",
    "Mgr Hrs", "RP OverT", "RP Hr Pay", "Clk OverT", "Clk Wage",
    "Adv Exp", "Net Worth", "Cash Flow", "E Rx Pur", "E OTC Pur",
    "Current", "Acid Test", "Turnover", "ROA", "G Margin", "Debt/NW"
]

# Location Data
LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

DEFAULT_WEIGHTS = {
    "Factor": [
        "Store's Past Rx Price", "Store's Present Rx Price", "Store's Promotion Index",
        "Store's Hours", "Offers Delivery Service", "Offers Patient Records",
        "Offers Credit", "Store's Inventory Level", "Store's Previous Market Share",
        "Store's RX Per Hour"
    ],
    "Medical Center":    [10, 30, 5,  10, 5, 10, 5, 10, 10, 5],
    "Neighborhood":      [20, 25, 10, 5,  10, 5, 5, 5,  10, 5],
    "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0,  5,  0]
}

# ==========================================
# 2. State Management
# ==========================================
def initialize_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1
    st.session_state.weights_df = pd.DataFrame(DEFAULT_WEIGHTS).set_index("Factor")
    
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        
        # Initial Inputs
        inputs = [0.0] * 36
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=1; inputs[18]=25.0; inputs[19]=1; inputs[20]=10.0; 
        inputs[21]=1500.0; inputs[23]=40.0
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}", 
            'location_code': 0, # 0 = Not Selected Yet
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 50000.0, 'acct_receivable': 2000.0,
                'inventory_rx': 30000.0, 'inventory_otc': 15000.0,
                'fixed_assets': 60000.0, 'acct_payable': 5000.0,
                'notes_payable': 0.0, 'long_term_debt': 40000.0,
                'retained_earnings': 112000.0 
            },
            'prev_stats': { 
                'avg_price': 20.0, 'mkt_share': 100/num_teams, 'rx_per_hr': 5.0
            },
            'history': []
        }

if 'players' not in st.session_state:
    initialize_game(5) 

# ==========================================
# 3. Logic Engine
# ==========================================
def calculate_demand_score(p, w_df):
    if p['location_code'] == 0: return 1, 0 # Skip if no location
    
    inp = p['inputs']
    prev = p['prev_stats']
    loc_col = LOC_MAP[p['location_code']]
    weights = w_df[loc_col] 
    
    current_price = 10.0 * (1 + inp[0]/100) + inp[1]
    score_past_pr = weights["Store's Past Rx Price"] * (20 / prev['avg_price']) 
    score_pres_pr = weights["Store's Present Rx Price"] * (20 / current_price)
    
    score_promo = weights["Store's Promotion Index"] * (inp[7] / 1000)
    score_hours = weights["Store's Hours"] * (inp[6] / 40)
    score_deliv = weights["Offers Delivery Service"] * inp[3]
    score_rec = weights["Offers Patient Records"] * inp[4]
    score_cred = weights["Offers Credit"] * inp[5]
    
    inv_level = (p['financials']['inventory_rx'] + p['financials']['inventory_otc']) / 10000
    score_inv = weights["Store's Inventory Level"] * inv_level
    score_share = weights["Store's Previous Market Share"] * prev['mkt_share']
    score_eff = weights["Store's RX Per Hour"] * prev['rx_per_hr']
    
    total_score = sum([score_past_pr, score_pres_pr, score_promo, score_hours, 
                       score_deliv, score_rec, score_cred, score_inv, score_share, score_eff])
    return max(total_score, 1), current_price

def process_period():
    w_df = st.session_state.weights_df
    loc_scores = {1: [], 2: [], 3: []}
    
    # 1. Calculate Scores
    for tid, p in st.session_state.players.items():
        if p['status'] != 'Submitted': continue
        if p['location_code'] == 0: continue # Skip stores with no location

        score, curr_pr = calculate_demand_score(p, w_df)
        loc_scores[p['location_code']].append({'id': tid, 'score': score, 'price': curr_pr})
        
    # 2. Distribute Sales
    for loc_code, stores in loc_scores.items():
        if not stores: continue
        
        total_loc_score = sum(s['score'] for s in stores)
        base_demand_rx = 6000 # Demand available per location type
        
        for s_data in stores:
            tid = s_data['id']
            p = st.session_state.players[tid]
            inp = p['inputs']
            fin = p['financials']
            
            mkt_share = (s_data['score'] / total_loc_score) if total_loc_score else 0
            rx_count = base_demand_rx * mkt_share
            avg_rx_price = s_data['price']
            
            rx_sales = rx_count * avg_rx_price
            otc_sales = rx_sales * 0.45 * (1 + inp[13]/100)
            tot_sales = rx_sales + otc_sales
            
            cost_rx = rx_sales / (1 + (inp[0]/100))
            cost_otc = otc_sales / (1 + (inp[13]/100))
            
            # Emergency Pur
            e_rx_pur = 0; e_otc_pur = 0
            if fin['inventory_rx'] < cost_rx:
                e_rx_pur = (cost_rx - fin['inventory_rx']) * 1.15
                fin['inventory_rx'] = cost_rx 
            if fin['inventory_otc'] < cost_otc:
                e_otc_pur = (cost_otc - fin['inventory_otc']) * 1.15
                fin['inventory_otc'] = cost_otc
                
            fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - cost_rx
            fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - cost_otc
            
            tot_cogs = cost_rx + cost_otc + e_rx_pur + e_otc_pur
            gross_margin = tot_sales - tot_cogs
            
            # Expenses
            hrs_open = inp[6]
            rp_wage = inp[18] * inp[17] * hrs_open * 13 
            rp_ot = (hrs_open - 40) * inp[17] * inp[18] * 1.5 * 13 if hrs_open > 40 else 0
            clk_wage = inp[20] * inp[19] * hrs_open * 13
            clk_ot = (hrs_open - 40) * inp[19] * inp[20] * 1.5 * 13 if hrs_open > 40 else 0
            mgr_sal = inp[21]
            rent = inp[23] if inp[23] > 0 else 3000
            ads = inp[7]
            depr = fin['fixed_assets'] * 0.02
            interest = fin['long_term_debt'] * 0.025
            other_exp = 2000
            
            tot_exp = rp_wage + rp_ot + clk_wage + clk_ot + mgr_sal + rent + ads + depr + interest + other_exp
            net_profit = gross_margin - tot_exp
            
            # Cash & Fin
            cash_in = tot_sales * 0.9 + inp[29] 
            cash_out = (tot_exp - depr) + inp[14] + inp[15] + inp[30] + inp[31] + e_rx_pur + e_otc_pur
            fin['cash'] += (cash_in - cash_out)
            fin['retained_earnings'] += net_profit
            fin['long_term_debt'] -= inp[31]
            
            e_loan = 0
            if fin['cash'] < 0:
                e_loan = abs(fin['cash']) + 2000
                fin['notes_payable'] += e_loan
                fin['cash'] += e_loan
            
            # Ratios
            nw = fin['retained_earnings']
            curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
            curr_liab = fin['acct_payable'] + fin['notes_payable']
            
            # Save History
            p['prev_stats'] = {'avg_price': avg_rx_price, 'mkt_share': mkt_share * 100, 'rx_per_hr': rx_count / (hrs_open * 13) if hrs_open else 0}
            
            p['history'].append({
                "Store Name": p['shop_name'],
                "LOCATION": LOC_MAP[p['location_code']],
                "Net Profit": net_profit,
                "ROI": net_profit/nw if nw else 0,
                "TOT SALES": tot_sales,
                "Rx SALES": rx_sales,
                "OTH SALES": otc_sales,
                "Rx Mkt Sh": mkt_share * 100,
                "Avg Rx Pr": avg_rx_price,
                "Rx Ing $": cost_rx / rx_count if rx_count else 0,
                "Rx GM%": (rx_sales - cost_rx)/rx_sales*100 if rx_sales else 0,
                "3-Pty GM%": 0, "Tot #Rx’s": rx_count, "3-Pty #Rx": 0,
                "Copay Dis": inp[2], "OTC M’kup": inp[13],
                "Store Hrs": hrs_open, "A/P Paid": inp[28], "M’age Pay": mgr_sal, "E. Loan": e_loan,
                "Mgr Hrs": inp[22], "RP OverT": rp_ot, "RP Hr Pay": inp[18],
                "Clk OverT": clk_ot, "Clk Wage": inp[20], "Adv Exp": ads,
                "Net Worth": nw, "Cash Flow": cash_in - cash_out,
                "E Rx Pur": e_rx_pur, "E OTC Pur": e_otc_pur,
                "Current": curr_assets/curr_liab if curr_liab else 0,
                "Acid Test": (fin['cash'] + fin['acct_receivable']) / (curr_liab + 1),
                "Turnover": tot_cogs / (fin['inventory_rx']+fin['inventory_otc']),
                "ROA": net_profit / (fin['fixed_assets'] + curr_assets),
                "G Margin": gross_margin / tot_sales if tot_sales else 0,
                "Debt/NW": (fin['long_term_debt'] + curr_liab) / nw if nw else 0
            })
            p['status'] = 'Thinking'
            p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. User Interface
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V10.0")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Instructor":
        pwd = st.text_input("Admin Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.markdown("---")
            teams = st.number_input("Number of Teams", 1, 20, 5)
            if st.button("⚠️ Reset / New Game", type="primary"):
                initialize_game(teams); st.rerun()
    
    elif role == "Student":
        if st.session_state.players:
            t_ids = list(st.session_state.players.keys())
            sel_id = st.selectbox("Your Store", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
            
            # Name Change
            p = st.session_state.players[sel_id]
            new_name = st.text_input("Shop Name", p['shop_name'])
            if new_name != p['shop_name']: p['shop_name'] = new_name; st.rerun()

# --- CONTENT ---
if role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.title("👨‍🏫 Instructor Control")
    t1, t2, t3 = st.tabs(["Weights", "Run", "Report"])
    
    with t1:
        st.write("Config Weights per Location")
        st.session_state.weights_df = st.data_editor(st.session_state.weights_df, height=400)
    
    with t2:
        sub = sum(1 for x in st.session_state.players.values() if x['status']=='Submitted')
        st.metric("Ready to Process", f"{sub} / {len(st.session_state.players)} Teams")
        if st.button("🚀 Run Simulation", type="primary"):
            process_period(); st.success("Done!"); st.rerun()
            
    with t3:
        rows = []
        for p in st.session_state.players.values():
            if p['history']: rows.append(p['history'][-1])
        
        if rows:
            df = pd.DataFrame(rows).sort_values("Net Profit", ascending=False).reset_index(drop=True)
            df.insert(0, "Rank", df.index + 1)
            # Filter cols
            fin_cols = [c for c in REPORT_COLUMNS if c in df.columns]
            st.dataframe(df[fin_cols].style.format(precision=2))
        else:
            st.info("No data available")

elif role == "Student" and 'sel_id' in locals():
    p = st.session_state.players[sel_id]
    st.title(f"🏥 {p['shop_name']}")
    
    # === STEP 1: SELECT LOCATION (ONE TIME) ===
    if p['location_code'] == 0:
        st.warning("⚠️ Please select your store location to begin.")
        st.markdown("""
        * **Medical Center:** High volume, high competition, sensitive to professional service.
        * **Neighborhood:** Loyal customers, convenience focus, balanced competition.
        * **Shopping Center:** High traffic, price sensitive, lower loyalty.
        """)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🏥 Medical Center"): p['location_code']=1; st.rerun()
        with c2:
            if st.button("🏡 Neighborhood"): p['location_code']=2; st.rerun()
        with c3:
            if st.button("🛍️ Shopping Center"): p['location_code']=3; st.rerun()
            
    # === STEP 2: GAMEPLAY ===
    else:
        st.info(f"📍 Location: **{LOC_MAP[p['location_code']]}** | Period: {st.session_state.global_period}")
        
        if p['status'] == 'Thinking':
            with st.form("input"):
                cols = st.columns(3)
                for i in range(36):
                    with cols[i%3]:
                        if i in [3,4,5,32,33,34]: p['inputs'][i] = st.selectbox(INPUT_LABELS[i], [0,1], index=int(p['inputs'][i]))
                        else: p['inputs'][i] = st.number_input(INPUT_LABELS[i], value=float(p['inputs'][i]))
                if st.form_submit_button("Submit"): p['status']='Submitted'; st.rerun()
        
        elif p['status'] == 'Submitted':
            st.success("Decisions Submitted. Waiting for Instructor.")
            if p['history']:
                l = p['history'][-1]
                c1,c2,c3 = st.columns(3)
                c1.metric("Sales", f"${l['TOT SALES']:,.0f}")
                c2.metric("Profit", f"${l['Net Profit']:,.0f}")
                c3.metric("Mkt Share", f"{l['Rx Mkt Sh']:.2f}%")
                if st.button("Edit Next Period"): p['status']='Thinking'; st.rerun()
