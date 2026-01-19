import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm Simulation V10.16", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #e6f3ff; border: 1px solid #2980b9; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0=No, 1=Yes)", "5. Pt. Records (0=No, 1=Yes)", "6. Credit (0=No, 1=Yes)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($)",
    "19. # Clerks", "20. Clerk Wage ($)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0=No, 1=Yes)",
    "34. Ben: Health (0=No, 1=Yes)", "35. 3rd Party (0=No, 1=Yes)", "36. HMO Bid ($)"
]

REPORT_COLUMNS = [
    "Net Profit", "TOT SALES", "Cash", "ROI", 
    "Rx SALES", "OTH SALES", "Rx Mkt Sh", "OTC Mkt Sh",
    "Avg Rx Pr", "Store Hrs", "Net Worth", "Current", 
    "Acid Test", "Turnover", "G Margin", "Debt/NW", "Cash Flow"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

RX_FACTORS = [
    "Store's Past Rx Price", "Store's Present Rx Price", "Store's Promotion Index",
    "Store's Hours", "Offers Delivery Service", "Offers Patient Records",
    "Offers Credit", "Store's Inventory Level", "Store's Previous Market Share",
    "Store's RX Per Hour"
]

OTC_FACTORS = [
    "Store's Previous OTC Markup",   
    "Store's Present OTC Markup",    
    "Store's Advertising Index",     
    "Store's Hours",                 
    "Store's Inventory Level",       
    "Store's Present Rx Market Share" 
]

# --- DEFAULT WEIGHTS ---
RX_DEFAULT_WEIGHTS = {
    "Factor": RX_FACTORS,
    "Medical Center":    [10, 30, 5,  20, 5, 10, 5, 5, 5, 5],
    "Neighborhood":      [20, 25, 10, 10, 10, 5, 5, 5, 5, 5],
    "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0, 5, 0]
}

OTC_DEFAULT_WEIGHTS = {
    "Factor": OTC_FACTORS,
    "Medical Center":    [10, 20, 20, 10, 10, 30],
    "Neighborhood":      [20, 30, 20, 10, 10, 10], 
    "Shopping Center":   [10, 40, 30, 10, 10, 0]   
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'master_rx_weights' not in st.session_state:
    st.session_state.master_rx_weights = pd.DataFrame(RX_DEFAULT_WEIGHTS)
if 'master_otc_weights' not in st.session_state:
    st.session_state.master_otc_weights = pd.DataFrame(OTC_DEFAULT_WEIGHTS)

def get_starting_inputs():
    return [
        50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 
        0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 
        1.0, 25.0, 1.0, 10.0, 1500.0, 30.0, 40.0, 60.0, 
        0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 
        0.0, 0.0, 0.0, 0.0
    ]

def start_new_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    st.session_state.game_active = True
    st.session_state.rx_weights_df = st.session_state.master_rx_weights.copy()
    st.session_state.otc_weights_df = st.session_state.master_otc_weights.copy()
    
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0,
            'retained_earnings': 138000.0
        }
        st.session_state.players[team_id] = {
            'shop_name': f"Store {i}",
            'location_code': 0, 
            'status': 'Thinking',
            'period': 1,
            'inputs': get_starting_inputs(),
            'financials': financials,
            'prev_stats': { 'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 'rx_per_hr': 5.0, 'otc_markup': 45.0 },
            'history': [] 
        }

if 'players' not in st.session_state:
    start_new_game(5)

# ==========================================
# 3. LOGIC ENGINE
# ==========================================
def calculate_results(store_list, rx_w_df, otc_w_df):
    data = []
    base_cost = 11.23; price_constant = 2.90
    loc_code = store_list[0]['p']['location_code']
    loc_name = LOC_MAP[loc_code]
    
    for p in store_list:
        tid = p['id']; inp = p['p']['inputs']; prev = p['p']['prev_stats']; fin = p['p']['financials']
        curr_price = (base_cost * (1 + inp[0]/100)) + inp[1] + price_constant
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        data.append({
            'id': tid, 'price_past': prev['avg_price'], 'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3], 'records': inp[4], 'credit': inp[5], 
            'inventory': inv_level, 'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr'],
            'otc_markup_past': prev.get('otc_markup', 45.0), 'otc_markup_pres': inp[13], 'advertising': inp[7]
        })
    
    df_comp = pd.DataFrame(data)
    
    # --- SCORING ---
    rx_weights = rx_w_df.set_index("Factor")[loc_name].values
    otc_weights = otc_w_df.set_index("Factor")[loc_name].values
    
    df_rx_ranks = pd.DataFrame({'id': df_comp['id']})
    def get_rank(series, ascending): return series.rank(method='min', ascending=ascending)
    df_rx_ranks['r0'] = get_rank(df_comp['price_past'], False) 
    df_rx_ranks['r1'] = get_rank(df_comp['price_pres'], False) 
    cols_map = ['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']
    for i, col in enumerate(cols_map): df_rx_ranks[f'r{i+2}'] = get_rank(df_comp[col], True) 
        
    rx_scores = {row['id']: sum(row[f'r{i}'] * rx_weights[i] for i in range(10)) for index, row in df_rx_ranks.iterrows()}
    total_rx_score = sum(rx_scores.values())
    rx_shares = {k: (v/total_rx_score if total_rx_score else 0) for k,v in rx_scores.items()}

    df_comp['rx_share_result'] = df_comp['id'].map(rx_shares)
    
    df_otc_ranks = pd.DataFrame({'id': df_comp['id']})
    df_otc_ranks['o0'] = get_rank(df_comp['otc_markup_past'], False)
    df_otc_ranks['o1'] = get_rank(df_comp['otc_markup_pres'], False)
    df_otc_ranks['o2'] = get_rank(df_comp['advertising'], True)
    df_otc_ranks['o3'] = get_rank(df_comp['hours'], True)
    df_otc_ranks['o4'] = get_rank(df_comp['inventory'], True)
    df_otc_ranks['o5'] = get_rank(df_comp['rx_share_result'], True)

    otc_scores = {row['id']: sum(row[f'o{i}'] * otc_weights[i] for i in range(6)) for index, row in df_otc_ranks.iterrows()}
    total_otc_score = sum(otc_scores.values())
    otc_shares = {k: (v/total_otc_score if total_otc_score else 0) for k,v in otc_scores.items()}

    # --- FINANCIALS ---
    base_rx_market = len(store_list) * 6000 
    base_otc_market_usd = base_rx_market * 8.0 
    
    for s_data in store_list:
        tid = s_data['id']; p = s_data['p']; inp = p['inputs']; fin = p['financials']
        my_rx_share = rx_shares[tid]; my_otc_share = otc_shares[tid]
        
        rx_count = base_rx_market * my_rx_share
        avg_rx_price = (base_cost * (1 + inp[0]/100)) + inp[1] + price_constant
        rx_sales = rx_count * avg_rx_price
        loc_mult = 1.5 if loc_code == 3 else 1.0
        otc_sales = base_otc_market_usd * loc_mult * my_otc_share
        tot_sales = rx_sales + otc_sales
        
        cost_rx = rx_sales / (1 + (inp[0]/100))
        cost_otc = otc_sales / (1 + (inp[13]/100))
        
        req_ret_rx = min(inp[26], fin['inventory_rx'] * 0.25)
        req_ret_otc = min(inp[27], fin['inventory_otc'] * 0.25)
        fin['inventory_rx'] = max(0, (fin['inventory_rx'] + inp[14] - req_ret_rx) - cost_rx)
        fin['inventory_otc'] = max(0, (fin['inventory_otc'] + inp[15] - req_ret_otc) - cost_otc)
        tot_cogs = cost_rx + cost_otc
        gross_margin = tot_sales - tot_cogs
        
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
            "Rx Mkt Sh": my_rx_share * 100, "OTC Mkt Sh": my_otc_share * 100,
            "Avg Rx Pr": avg_rx_price, "Store Hrs": hrs_open, "E. Loan": e_loan, 
            "Net Worth": nw, "Cash Flow": cash_in - cash_out, "Cash": fin['cash'],
            "Current": curr_assets/curr_liab if curr_liab else 0,
            "Acid Test": (fin['cash'] + fin['acct_receivable']) / (curr_liab + 1),
            "Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2 + 1),
            "G Margin": (gross_margin/tot_sales*100) if tot_sales else 0,
            "Debt/NW": ((fin['long_term_debt'] + curr_liab) / nw) if nw else 0,
            "Period": p['period']
        })
        p['prev_stats'] = { 'avg_price': avg_rx_price, 'mkt_share': my_rx_share*100, 'rx_per_hr': rx_count/(hrs_open*13), 'otc_markup': inp[13] }
        p['status'] = 'Thinking'; p['period'] += 1

def run_simulation_step():
    rx_w = st.session_state.rx_weights_df
    otc_w = st.session_state.otc_weights_df
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['location_code'] != 0: stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
    for loc_code, stores in stores_by_loc.items():
        if stores: calculate_results(stores, rx_w, otc_w)
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
            st.markdown("### ⚙️ Game Control")
            num_teams = st.number_input("Number of Teams", 1, 20, 5)
            if st.button("🔄 Start New Game", type="primary"):
                start_new_game(num_teams); st.rerun()
            st.markdown("---")
            ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
            st.write(f"**Current Period:** {st.session_state.global_period}")
            st.metric("Ready Teams", f"{ready}/{len(st.session_state.players)}")
            if st.button("🚀 Run Period"):
                run_simulation_step(); st.success("Processed!"); st.rerun()
    else:
        if st.button("🔄 Reset My Session (Test)"): start_new_game(5); st.rerun()

if role == "Student":
    if st.session_state.players:
        t_ids = list(st.session_state.players.keys())
        sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
        p = st.session_state.players[sel_id]

        if p['period'] == 1 and p['status'] == 'Thinking':
            st.info("Please setup your store details.")
            c1, c2 = st.columns(2)
            new_name = c1.text_input("Store Name", p['shop_name'])
            if new_name != p['shop_name']: p['shop_name'] = new_name; st.rerun()
            loc_idx = c2.selectbox("Select Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x], index=p['location_code'])
            if loc_idx != p['location_code']: p['location_code'] = loc_idx; st.rerun()
            if p['location_code'] == 0: st.warning("Please select a location."); st.stop()
            st.markdown("---")

        st.title(f"🏥 {p['shop_name']}")
        st.caption(f"Location: {LOC_MAP[p['location_code']]} | Period: {st.session_state.global_period} | Status: {p['status']}")
        
        tab1, tab2 = st.tabs(["📝 Decisions (Excel View)", "📊 Financial Report"])
        
        with tab1:
            st.subheader(f"Decisions for Period {p['period']}")
            if p['status'] == 'Thinking':
                st.info("💡 Tip: You can type a value and press **Enter** to move to the next row automatically!")
                
                # --- EXCEL STYLE EDITOR START ---
                # 1. Create Dataframe for display
                df_inputs = pd.DataFrame({
                    "Input #": [f"{i+1}" for i in range(36)],
                    "Description": INPUT_LABELS,
                    "Value": p['inputs']
                })

                # 2. Show Editor
                edited_df = st.data_editor(
                    df_inputs,
                    column_config={
                        "Input #": st.column_config.TextColumn(disabled=True, width="small"),
                        "Description": st.column_config.TextColumn(disabled=True, width="large"),
                        "Value": st.column_config.NumberColumn(
                            "Your Input", 
                            min_value=0.0, 
                            max_value=1000000.0,
                            required=True,
                            width="medium"
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=1300, # Tall enough to see all without internal scroll
                    key=f"editor_{sel_id}_{p['period']}" # Unique key per period
                )
                
                # 3. Submit Logic
                st.markdown("---")
                if st.button("✅ Submit Decisions", type="primary"):
                    # Save values back to player state
                    p['inputs'] = edited_df["Value"].tolist()
                    p['status'] = 'Submitted'
                    st.rerun()
                # --- EXCEL STYLE EDITOR END ---

            else:
                st.success("Submitted! Waiting for Instructor."); 
                if st.button("Edit Decisions"): p['status'] = 'Thinking'; st.rerun()

        with tab2:
            st.subheader("Performance History")
            if p['history']:
                last = p['history'][-1]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m2.metric("Sales", f"${last['TOT SALES']:,.0f}")
                m3.metric("Rx Share", f"{last['Rx Mkt Sh']:.1f}%")
                m4.metric("OTC Share", f"{last['OTC Mkt Sh']:.1f}%")
                
                df_hist = pd.DataFrame(p['history'])
                display_cols = ["Period"] + [c for c in REPORT_COLUMNS if c in df_hist.columns]
                st.dataframe(df_hist[display_cols].style.format("{:,.2f}"), use_container_width=True, height=500)
            else:
                st.info("No history yet.")

elif role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.header("👨‍🏫 Instructor Dashboard")
    tab_conf, tab_res = st.tabs(["⚙️ Weights", "🏆 Results"])
    with tab_conf:
        with st.form("weights_form"):
            c1, c2 = st.columns(2)
            with c1: st.write("### 💊 Rx Weights"); edited_rx = st.data_editor(st.session_state.rx_weights_df, use_container_width=True, num_rows="fixed")
            with c2: st.write("### 🛍️ OTC Weights"); edited_otc = st.data_editor(st.session_state.otc_weights_df, use_container_width=True, num_rows="fixed")
            if st.form_submit_button("💾 Save Weights"):
                st.session_state.rx_weights_df = edited_rx; st.session_state.otc_weights_df = edited_otc
                st.session_state.master_rx_weights = edited_rx.copy(); st.session_state.master_otc_weights = edited_otc.copy()
                st.success("Saved!")
                st.rerun()

    with tab_res:
        st.write("### Current Standings")
        rows = [p['history'][-1] for p in st.session_state.players.values() if p['history']]
        if rows:
            df = pd.DataFrame(rows).sort_values("Net Profit", ascending=False)
            st.dataframe(df[["Store Name", "Period"] + REPORT_COLUMNS].style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("No results yet.")
