import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Configuration
# ==========================================
st.set_page_config(page_title="Communi-Pharm V10.3 (Calibrated)", layout="wide")
ADMIN_PASSWORD = "admin"

# Labels
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

REPORT_COLUMNS = [
    "Rank", "Store Name", "LOCATION", "Net Profit", "ROI", 
    "TOT SALES", "Rx SALES", "OTH SALES", "Rx Mkt Sh",
    "Avg Rx Pr", "Rx Ing $", "Rx GM%", 
    "Store Hrs", "A/P Paid", "M’age Pay", "E. Loan",
    "Net Worth", "Cash Flow", "Cash", "Investments",
    "Current", "Acid Test", "Turnover", "ROA", "G Margin", "Debt/NW"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# Configurable Weights
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
# 2. State Management & Initialization
# ==========================================
def initialize_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 2 # Start at Period 2 as requested
    st.session_state.weights_df = pd.DataFrame(DEFAULT_WEIGHTS).set_index("Factor")
    
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        
        # --- PRE-LOADED INPUTS (Based on User's Data) ---
        inputs = [0.0] * 36
        # Default Inputs
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=1; inputs[18]=25.0; inputs[19]=1; inputs[20]=10.0; 
        inputs[21]=1500.0; inputs[23]=40.0
        
        # Override for Team 1 (ThaikritOsot Simulation)
        if i == 1:
            inputs[0] = 49.0   # Rx Markup
            inputs[1] = 1.0    # Rx Fee
            inputs[2] = 0.0    # Copay
            inputs[3] = 1.0    # Delivery
            inputs[4] = 1.0    # Records
            inputs[5] = 1.0    # Credit
            inputs[6] = 60.0   # Hours
            inputs[7] = 1000.0 # Promo
            inputs[8] = 60.0   # % Promo Rx
            inputs[13] = 47.0  # OTC Markup
            inputs[14] = 40000.0 # Rx Purchase
            inputs[15] = 25000.0 # OTC Purchase
            inputs[17] = 1.0   # Pharmacists
            inputs[18] = 21.0  # Pharm Rate
            inputs[19] = 1.5   # Clerks
            inputs[20] = 4.75  # Clerk Rate
            inputs[21] = 8100.0 # Mgr Salary
            inputs[22] = 33.33 # Mgr Time Rx
            inputs[23] = 60.0  # Mgr Hrs
            inputs[24] = 8200.0 # Mortgage
            inputs[25] = 0.0
            inputs[26] = 1000.0 # Min Cash
            inputs[28] = 999999.0 # Pay AP (Will be capped logic)
            inputs[32] = 1.0   # Life Ins
            inputs[33] = 1.0   # Health Ins
            inputs[34] = 1.0   # 3rd Party
        
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}" if i != 1 else "ThaikritOsot",
            'location_code': 1 if i == 1 else (i % 3) + 1, # Store 1 = Medical Center
            'status': 'Thinking',
            'period': 2,
            'inputs': inputs,
            'financials': {
                'cash': 7000.0,
                'investments': 0.0,
                'acct_receivable': 68000.0,
                'inventory_rx': 45000.0,
                'inventory_otc': 40000.0,
                'fixed_assets': 35000.0,
                'acct_payable': 20000.0,
                'notes_payable': 10000.0,
                'long_term_debt': 80000.0,
                'retained_earnings': -12000.0
            },
            'prev_stats': { 
                'avg_price': 19.50, 'mkt_share': 100/num_teams, 'rx_per_hr': 5.0
            },
            'history': []
        }

if 'players' not in st.session_state:
    initialize_game(5)

# ==========================================
# 3. Logic Engine (Calibrated)
# ==========================================
def calculate_rank_scores(store_list, w_df):
    data = []
    # Calibrated Base Cost from Analysis ($19.47 price / 1.49 markup - 1 fee)
    base_cost = 12.40 
    
    for p in store_list:
        tid = p['id']
        inp = p['p']['inputs']
        prev = p['p']['prev_stats']
        fin = p['p']['financials']
        
        curr_price = base_cost * (1 + inp[0]/100) + inp[1]
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        
        data.append({
            'id': tid,
            'price_past': prev['avg_price'],
            'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3],
            'records': inp[4], 'credit': inp[5], 'inventory': inv_level,
            'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr']
        })
    
    df_comp = pd.DataFrame(data)
    loc_code = store_list[0]['p']['location_code']
    weights = w_df[LOC_MAP[loc_code]].values
    
    # Ranking Logic
    df_ranks = pd.DataFrame({'id': df_comp['id']})
    def get_rank(series, ascending): return series.rank(method='min', ascending=ascending)

    df_ranks['r1'] = get_rank(df_comp['price_past'], False)
    df_ranks['r2'] = get_rank(df_comp['price_pres'], False)
    for i, col in enumerate(['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']):
        df_ranks[f'r{i+3}'] = get_rank(df_comp[col], True)
    
    final_scores = {}
    for index, row in df_ranks.iterrows():
        total_score = sum(row[f'r{i+1}'] * weights[i] for i in range(10))
        final_scores[row['id']] = total_score
        
    return final_scores, base_cost

def process_period():
    w_df = st.session_state.weights_df
    
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['status'] == 'Submitted' and p['location_code'] != 0:
            stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
            
    for loc_code, stores in stores_by_loc.items():
        if not stores: continue
        
        rank_scores, base_cost = calculate_rank_scores(stores, w_df)
        total_loc_score = sum(rank_scores.values())
        
        # Calibrated Market Size (~5,500 Rx per store average)
        base_market_size = len(stores) * 6000 
        
        for s_data in stores:
            tid = s_data['id']
            p = s_data['p']
            inp = p['inputs']
            fin = p['financials']
            
            # --- SALES ---
            my_score = rank_scores[tid]
            mkt_share = (my_score / total_loc_score) if total_loc_score else 0
            rx_count = base_market_size * mkt_share
            
            avg_rx_price = base_cost * (1 + inp[0]/100) + inp[1]
            rx_sales = rx_count * avg_rx_price
            
            # OTC Ratio Tuned by Location
            # Medical(1)=Low OTC, Neighbor(2)=Med, Shopping(3)=High
            otc_factors = {1: 0.25, 2: 0.50, 3: 0.75} 
            base_otc_ratio = otc_factors.get(loc_code, 0.45)
            
            otc_sales = rx_sales * base_otc_ratio * (1 + (inp[7]/5000)) * (1 + inp[13]/100)
            tot_sales = rx_sales + otc_sales
            
            # --- RETURNS & COGS ---
            req_ret_rx = min(inp[26], fin['inventory_rx'] * 0.25)
            req_ret_otc = min(inp[27], fin['inventory_otc'] * 0.25)
            cash_returns = (req_ret_rx + req_ret_otc) * 0.8
            
            cost_rx = rx_sales / (1 + (inp[0]/100))
            cost_otc = otc_sales / (1 + (inp[13]/100))
            
            # Emergency Purchase Logic
            e_rx = max(0, (cost_rx - fin['inventory_rx']) * 1.15)
            if e_rx > 0: fin['inventory_rx'] = cost_rx
            e_otc = max(0, (cost_otc - fin['inventory_otc']) * 1.15)
            if e_otc > 0: fin['inventory_otc'] = cost_otc
            
            fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] - req_ret_rx) - cost_rx
            fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] - req_ret_otc) - cost_otc
            
            tot_cogs = cost_rx + cost_otc + e_rx + e_otc
            gross_margin = tot_sales - tot_cogs
            
            # --- EXPENSES ---
            hrs_open = inp[6]
            # Wages (Pharmacist + Clerk)
            ph_wage = inp[17] * inp[18] * hrs_open * 13
            cl_wage = inp[19] * inp[20] * hrs_open * 13
            wages = ph_wage + cl_wage
            if hrs_open > 40: wages *= 1.1 # OT Factor
            
            # Benefits
            ben_rate = 0
            if inp[32]==1: ben_rate += 0.05
            if inp[33]==1: ben_rate += 0.15
            ben_cost = wages * ben_rate
            
            fixed_ops = inp[21] + inp[24] + 3000 # Salary + Mortgage + Misc
            marketing = inp[7]
            depr = fin['fixed_assets'] * 0.02
            interest = (fin['long_term_debt'] + fin['notes_payable']) * 0.025
            
            tot_exp = wages + ben_cost + fixed_ops + marketing + depr + interest
            net_profit = gross_margin - tot_exp
            
            # --- CASH FLOW ---
            # Cap A/P Payment at actual debt
            pay_ap = min(inp[28], fin['acct_payable'])
            
            cash_in = (tot_sales * 0.9) + cash_returns
            cash_out = (tot_exp - depr) + inp[14] + inp[15] + inp[31] + e_rx + e_otc + pay_ap
            
            fin['cash'] += (cash_in - cash_out)
            fin['acct_payable'] -= pay_ap
            # New AP from purchases (simplified assume 50% credit)
            fin['acct_payable'] += (inp[14] + inp[15]) * 0.5 
            fin['retained_earnings'] += net_profit
            fin['long_term_debt'] -= inp[31]
            
            e_loan = 0
            if fin['cash'] < 0:
                e_loan = abs(fin['cash']) + 5000
                fin['notes_payable'] += e_loan
                fin['cash'] += e_loan
                
            # --- METRICS & HISTORY ---
            nw = fin['retained_earnings']
            curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
            curr_liab = fin['acct_payable'] + fin['notes_payable']
            
            p['history'].append({
                "Store Name": p['shop_name'], "LOCATION": LOC_MAP[p['location_code']],
                "Net Profit": net_profit, "ROI": (net_profit/nw*100) if nw else 0,
                "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
                "Rx Mkt Sh": mkt_share * 100, "Avg Rx Pr": avg_rx_price,
                "Rx Ing $": cost_rx / rx_count if rx_count else 0,
                "Rx GM%": (rx_sales - cost_rx)/rx_sales*100 if rx_sales else 0,
                "A/P Paid": pay_ap, "Store Hrs": hrs_open, "E. Loan": e_loan,
                "Net Worth": nw, "Cash Flow": cash_in - cash_out, "Cash": fin['cash'],
                "Current": curr_assets/curr_liab if curr_liab else 0,
                "Acid Test": (fin['cash'] + fin['acct_receivable']) / (curr_liab + 1),
                "Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2 + 1),
                "ROA": (net_profit / (fin['fixed_assets'] + curr_assets)*100),
                "G Margin": (gross_margin / tot_sales*100) if tot_sales else 0,
                "Debt/NW": ((fin['long_term_debt'] + curr_liab) / nw) if nw else 0
            })
            
            p['status'] = 'Thinking'
            p['period'] = p.get('period', 1) + 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V10.3")
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
            p = st.session_state.players[sel_id]
            st.info(f"Store: {p['shop_name']} | Location: {LOC_MAP[p['location_code']]}")
            
            if p['status'] == 'Thinking':
                with st.form("inputs"):
                    cols = st.columns(3)
                    for i in range(36):
                        with cols[i%3]:
                            if i in [3,4,5,32,33,34]: p['inputs'][i] = st.selectbox(INPUT_LABELS[i], [0,1], index=int(p['inputs'][i]))
                            else: p['inputs'][i] = st.number_input(INPUT_LABELS[i], value=float(p['inputs'][i]))
                    if st.form_submit_button("✅ Submit"): p['status']='Submitted'; st.rerun()
            else:
                st.success("Submitted.")
                if st.button("Edit"): p['status']='Thinking'; st.rerun()
                
            if p['history']:
                last = p['history'][-1]
                m1,m2,m3 = st.columns(3)
                m1.metric("Sales", f"${last['TOT SALES']:,.0f}")
                m2.metric("Profit", f"${last['Net Profit']:,.0f}")
                m3.metric("Cash", f"${last['Cash']:,.0f}")
                st.dataframe(pd.DataFrame(list(last.items()), columns=["Metric","Value"]), use_container_width=True)

if role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.title("👨‍🏫 Instructor Control")
    if st.button("🚀 Run Simulation"):
        process_period(); st.rerun()
    
    rows = [p['history'][-1] for p in st.session_state.players.values() if p['history']]
    if rows:
        df = pd.DataFrame(rows).sort_values("Net Profit", ascending=False)
        st.dataframe(df[REPORT_COLUMNS].style.format(precision=2))
