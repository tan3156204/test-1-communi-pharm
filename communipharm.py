import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm Simulation", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #e6f3ff; border: 1px solid #2980b9; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0/1)", "5. Pt. Records (0/1)", "6. Credit (0/1)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($)",
    "19. # Clerks", "20. Clerk Wage ($)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

REPORT_COLUMNS = [
    "Net Profit", "TOT SALES", "Cash", "ROI", 
    "Rx SALES", "OTH SALES", "Rx Mkt Sh", "Avg Rx Pr", 
    "Store Hrs", "Net Worth", "Current", "Acid Test", "Turnover",
    "G Margin", "Debt/NW", "Cash Flow"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

DEFAULT_WEIGHTS = {
    "Factor": [
        "Store's Past Rx Price", "Store's Present Rx Price", "Store's Promotion Index",
        "Store's Hours", "Offers Delivery Service", "Offers Patient Records",
        "Offers Credit", "Store's Inventory Level", "Store's Previous Market Share",
        "Store's RX Per Hour"
    ],
    "Medical Center":    [10, 30, 5,  20, 5, 10, 5, 5, 5, 5],
    "Neighborhood":      [20, 25, 10, 10, 10, 5, 5, 5, 5, 5],
    "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0, 5, 0]
}

# ==========================================
# 2. STATE MANAGEMENT & INITIALIZATION
# ==========================================

def start_new_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 2 
    st.session_state.game_active = True
    st.session_state.weights_df = pd.DataFrame(DEFAULT_WEIGHTS).set_index("Factor")
    
    # Loop create team ตามจำนวนที่กำหนด (1-7)
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        store_name = f"Store {i}" 
        
        # --- Pre-fill Inputs for Validation (Store 1 only) ---
        inputs = [0.0] * 36
        if i == 1: 
            # Store 1: ใส่ค่า Validate ตาม PDF ไว้ให้ test
            inputs[0]=49.0; inputs[1]=1.0; inputs[2]=0.0
            inputs[3]=1.0; inputs[4]=1.0; inputs[5]=1.0
            inputs[6]=60.0; inputs[7]=1000.0; inputs[8]=60.0
            inputs[9]=0.0; inputs[10]=0.0
            inputs[13]=47.0; inputs[14]=40000.0; inputs[15]=25000.0
            inputs[17]=1.0; inputs[18]=21.0
            inputs[19]=1.5; inputs[20]=4.75
            inputs[21]=8100.0; inputs[22]=33.33; inputs[23]=60.0
            inputs[24]=8200.0; inputs[26]=1000.0
            inputs[28]=999999.0; inputs[29]=10000.0 
            inputs[31]=2.0 
            inputs[32]=1.0; inputs[33]=1.0; inputs[34]=1.0
        else:
            # Default values for other stores
            inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
            inputs[17]=1; inputs[18]=25.0; inputs[19]=1; inputs[20]=10.0; 
            inputs[21]=1500.0; inputs[23]=40.0

        # --- Setup Period 1 History ---
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0,
            'retained_earnings': 138000.0
        }

        p1_history = {
            "Store Name": store_name, "LOCATION": "Not Selected",
            "Net Profit": 9848.0, "ROI": 7.0, 
            "TOT SALES": 142312.0, "Rx SALES": 115752.0, "OTH SALES": 26560.0,
            "Rx Mkt Sh": 12.5, "Avg Rx Pr": 19.61, "Rx Ing $": 11.23, "Rx GM%": 42.7,
            "Store Hrs": 46.0, "A/P Paid": 20000.0, "E. Loan": 0.0,
            "Net Worth": 138000.0, "Cash Flow": 5000.0, "Cash": 15000.0,
            "Investments": 2000.0,
            "Current": 2.40, "Acid Test": 1.16, "Turnover": 0.67,
            "ROA": 3.0, "G Margin": 45.0, "Debt/NW": 1.17
        }
        
        if i == 1:
            p1_history["LOCATION"] = "Medical Center"

        st.session_state.players[team_id] = {
            'shop_name': store_name,
            'location_code': 1 if i == 1 else 0, 
            'status': 'Thinking',
            'period': 2,
            'inputs': inputs,
            'financials': financials,
            'prev_stats': { 'avg_price': 19.61, 'mkt_share': 12.5, 'rx_per_hr': 5.0 },
            'history': [p1_history]
        }

# Default Start 5 Teams
if 'players' not in st.session_state:
    start_new_game(5)

# ==========================================
# 3. LOGIC ENGINE
# ==========================================
def calculate_results(store_list, w_df):
    data = []
    base_cost = 11.23; price_constant = 2.90
    for p in store_list:
        tid = p['id']; inp = p['p']['inputs']; prev = p['p']['prev_stats']; fin = p['p']['financials']
        curr_price = (base_cost * (1 + inp[0]/100)) + inp[1] + price_constant
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        data.append({
            'id': tid, 'price_past': prev['avg_price'], 'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3], 'records': inp[4], 
            'credit': inp[5], 'inventory': inv_level, 'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr']
        })
    df_comp = pd.DataFrame(data)
    loc_code = store_list[0]['p']['location_code']
    weights = w_df[LOC_MAP[loc_code]].values
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
        
    total_loc_score = sum(final_scores.values())
    base_market_size = len(stores) * 6000 
    
    for s_data in stores:
        tid = s_data['id']; p = s_data['p']; inp = p['inputs']; fin = p['financials']
        my_score = final_scores[tid]
        mkt_share = (my_score / total_loc_score) if total_loc_score else 0
        rx_count = base_market_size * mkt_share
        avg_rx_price = (base_cost * (1 + inp[0]/100)) + inp[1] + price_constant
        rx_sales = rx_count * avg_rx_price
        otc_ratio = 0.25 if loc_code == 1 else 0.45
        otc_sales = rx_sales * otc_ratio * (1 + (inp[7]/5000)) * (1 + inp[13]/100)
        tot_sales = rx_sales + otc_sales
        cost_rx = rx_sales / (1 + (inp[0]/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        req_ret_rx = min(inp[26], fin['inventory_rx'] * 0.25)
        req_ret_otc = min(inp[27], fin['inventory_otc'] * 0.25)
        fin['inventory_rx'] = max(0, (fin['inventory_rx'] + inp[14] - req_ret_rx) - cost_rx)
        fin['inventory_otc'] = max(0, (fin['inventory_otc'] + inp[15] - req_ret_otc) - cost_otc)
        tot_cogs = cost_rx + cost_otc; gross_margin = tot_sales - tot_cogs
        hrs_open = inp[6]
        wages = (inp[17]*inp[18] + inp[19]*inp[20]) * hrs_open * 13
        if hrs_open > 40: wages *= 1.1
        ben_rate = 0.05 if inp[32]==1 else 0
        ben_rate += 0.15 if inp[33]==1 else 0
        ben_cost = wages * ben_rate
        fixed_ops = inp[21] + inp[24] + 3000
        depr = fin['fixed_assets']*0.02
        interest_exp = (fin['long_term_debt'] + fin['notes_payable']) * 0.025
        ar_interest_income = (fin['acct_receivable'] * 0.5) * (inp[31] / 100)
        tot_exp = wages + ben_cost + fixed_ops + inp[7] + depr + interest_exp
        net_profit = gross_margin - tot_exp + ar_interest_income
        pay_ap = min(inp[28], fin['acct_payable'])
        debt_written = inp[29]
        cash_in = (tot_sales * 0.9) + debt_written
        cash_out = (tot_exp - depr) + inp[14] + inp[15] + inp[30] + pay_ap
        fin['cash'] += (cash_in - cash_out)
        fin['retained_earnings'] += net_profit
        fin['long_term_debt'] += (debt_written - inp[30]) 
        fin['acct_payable'] = max(0, fin['acct_payable'] - pay_ap + (inp[14]+inp[15])*0.5)
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 2000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
        nw = fin['retained_earnings']
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        p['history'].append({
            "Store Name": p['shop_name'], "LOCATION": LOC_MAP[p['location_code']],
            "Net Profit": net_profit, "ROI": (net_profit/nw*100) if nw else 0,
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Rx Mkt Sh": mkt_share * 100, "Avg Rx Pr": avg_rx_price,
            "Store Hrs": hrs_open, "E. Loan": e_loan, 
            "Net Worth": nw, "Cash Flow": cash_in - cash_out, "Cash": fin['cash'],
            "Current": curr_assets/curr_liab if curr_liab else 0,
            "Acid Test": (fin['cash'] + fin['acct_receivable']) / (curr_liab + 1),
            "Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2 + 1),
            "ROA": (net_profit / (fin['fixed_assets'] + curr_assets)*100),
            "G Margin": (gross_margin/tot_sales*100) if tot_sales else 0,
            "Debt/NW": ((fin['long_term_debt'] + curr_liab) / nw) if nw else 0
        })
        p['prev_stats'] = {'avg_price': avg_rx_price, 'mkt_share': mkt_share*100, 'rx_per_hr': rx_count/(hrs_open*13)}
        p['status'] = 'Thinking'; p['period'] += 1

def run_simulation_step():
    w_df = st.session_state.weights_df
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['location_code'] != 0:
            stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
    for loc_code, stores in stores_by_loc.items():
        if stores: calculate_results(stores, w_df)
    st.session_state.global_period += 1

# ==========================================
# 4. USER INTERFACE
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm")
    role = st.selectbox("Select Role", ["Student", "Instructor"])
    st.markdown("---")
    
    if role == "Instructor":
        pwd = st.text_input("Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("Authorized")
            
            # --- New Feature: Team Count Setting ---
            st.markdown("### ⚙️ Game Settings")
            num_teams = st.number_input("Number of Teams", min_value=1, max_value=7, value=5, step=1)
            
            if st.button("🔄 New Game / Reset", type="primary"):
                start_new_game(num_teams)
                st.rerun()
                
            st.markdown("---")
            ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
            st.write(f"**Period:** {st.session_state.global_period}")
            st.metric("Ready Teams", f"{ready}/{len(st.session_state.players)}")
            
            if st.button("🚀 Run Period"):
                run_simulation_step()
                st.success("Processed!")
                st.rerun()
    else:
        if st.button("🔄 Reset My Test"):
            start_new_game(5)
            st.rerun()

if role == "Student":
    if st.session_state.players:
        t_ids = list(st.session_state.players.keys())
        sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
        p = st.session_state.players[sel_id]

        # --- STORE SETUP (RENAME) SECTION ---
        if p['period'] == 2 and p['status'] == 'Thinking':
            st.info("👋 Welcome! Please set up your store details before starting.")
            with st.container():
                c1, c2 = st.columns(2)
                # Store Name Input
                new_name = c1.text_input("📛 Store Name", p['shop_name'])
                if new_name != p['shop_name']:
                    p['shop_name'] = new_name
                    st.rerun()
                
                # Location Input
                loc_idx = c2.selectbox("📍 Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x], index=p['location_code'])
                if loc_idx != p['location_code']:
                    p['location_code'] = loc_idx
                    st.rerun()
            st.markdown("---")

        st.title(f"🏥 {p['shop_name']}")
        st.caption(f"Location: {LOC_MAP[p['location_code']]} | Period: {st.session_state.global_period} | Status: {p['status']}")
        
        tab1, tab2 = st.tabs(["📝 Decisions (Inputs)", "📊 Financial Report (History)"])
        
        with tab1:
            st.subheader(f"Decisions for Period {p['period']}")
            if p['status'] == 'Thinking':
                with st.form("input_form"):
                    cols = st.columns(3)
                    for i in range(36):
                        with cols[i%3]:
                            label = INPUT_LABELS[i].split('(')[0]
                            val = float(p['inputs'][i])
                            if i in [3,4,5,32,33,34]:
                                p['inputs'][i] = st.selectbox(f"{i+1}. {label}", [0,1], index=int(val))
                            else:
                                p['inputs'][i] = st.number_input(f"{i+1}. {label}", value=val)
                    st.markdown("---")
                    if st.form_submit_button("✅ Submit Decisions", type="primary"):
                        p['status'] = 'Submitted'
                        st.rerun()
            else:
                st.success("Submitted! Waiting for Instructor.")
                if st.button("Edit Decisions"):
                    p['status'] = 'Thinking'
                    st.rerun()

        with tab2:
            st.subheader("Performance History")
            if p['history']:
                last = p['history'][-1]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m2.metric("Sales", f"${last['TOT SALES']:,.0f}")
                m3.metric("Cash", f"${last['Cash']:,.0f}")
                m4.metric("ROI", f"{last['ROI']:.2f}%")
                st.markdown("---")
                df_hist = pd.DataFrame(p['history'])
                display_cols = [c for c in REPORT_COLUMNS if c in df_hist.columns]
                st.dataframe(df_hist[display_cols].T.style.format("{:,.2f}"), use_container_width=True, height=600)
            else:
                st.info("No history available.")

elif role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.header("👨‍🏫 Instructor Dashboard")
    tab_conf, tab_res = st.tabs(["⚙️ Configuration", "🏆 Results"])
    with tab_conf:
        st.write("### Simulation Weights")
        st.session_state.weights_df = st.data_editor(st.session_state.weights_df, use_container_width=True)
    with tab_res:
        st.write("### Current Standings")
        rows = [p['history'][-1] for p in st.session_state.players.values() if p['history']]
        if rows:
            df = pd.DataFrame(rows).sort_values("Net Profit", ascending=False)
            st.dataframe(df[REPORT_COLUMNS].style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("No results yet.")
