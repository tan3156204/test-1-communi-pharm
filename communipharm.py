import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V30 (Full Report)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.9em; }
    .metric-header { font-weight: bold; background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# --- MAPPINGS ---
INPUT_LABELS = [
    "1. Rx Markup/Fee", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0/1)", "5. Pt. Records (0/1)", "6. Credit (0/1)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists (FTE)", "18. Pharm Wage ($/hr)",
    "19. # Clerks (FTE)", "20. Clerk Wage ($/hr)", "21. Mgr Salary ($/mo)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

MARKET_LABELS = [
    "1. Avg Ingredient Cost ($)", "2. Avg Copay Allowed ($)", "3. Avg Third-Party Fee ($)",
    "4. Percent Market Rx’s 3rd-Party (%)", "5. Maximum Promotion Expenditure ($)", 
    "6. % Sales A/R Store Type 1 (%)", "7. % A/R Sales Store Type 2 (%)", "8. % A/R Sales Store Type 3 (%)",
    "9. Interest Rate for Period (%)", "10. Average Number Rx Per Store (#)", "11. Average Other Sales Per Store ($)",
    "12. Gross Margin Slippage Rate (%)", "13. Number Periods per Year (#)", "14. Third-Party Lag in Payment (%)",
    "15. A/R Lag in Payment (%)", "16. Mutual Fund Transaction Price ($)", "17. Closing Date Month",
    "18. Day", "19. Year", "20. Current Inflation Rate (%)",
    "21. Stockout Rx Inventory Index", "22. Stockout Other Inventory Index", "23. Pass Book Savings Rate (%)",
    "24. Mutual Fund Next Period ($)", "25. Interest Rate on CD’s (%)", "26. Average Dollar Sales/Clerk ($)",
    "27. Maximum Price for Rx’s ($)", "28. SS & WC as % of Salary & Wages (%)"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.025}

RX_DEFAULT = {
    "Factor": ["Price", "Promo", "Hours", "Delivery", "Records", "Credit", "Inventory", "MktShare", "Efficiency", "PastPrice"],
    "Medical Center":    [10, 5, 20, 5, 10, 5, 5, 5, 5, 30],
    "Neighborhood":      [20, 10, 10, 10, 5, 5, 5, 5, 5, 25],
    "Shopping Center":   [40, 15, 5, 0, 0, 5, 0, 5, 0, 30]
}
OTC_DEFAULT = {
    "Factor": ["PrevMarkup", "PresMarkup", "AdIndex", "Hours", "Inventory", "RxShare"],
    "Medical Center":    [10, 20, 20, 10, 10, 30],
    "Neighborhood":      [20, 30, 20, 10, 10, 10], 
    "Shopping Center":   [10, 40, 30, 10, 10, 0]   
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

if 'market_data_list' not in st.session_state:
    st.session_state.market_data_list = [
        11.23, 2.0, 2.90, 25.0, 1500.0, 80.0, 50.0, 20.0,
        2.5, 6000.0, 48000.0, 0.0, 4.0, 15.0, 30.0,
        10.0, 1.0, 1.0, 2024.0, 3.0, 100.0, 100.0, 
        2.0, 10.5, 5.0, 120.0, 100.0, 15.0
    ]

if 'rx_weights_df' not in st.session_state: st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state: st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

def get_starting_inputs():
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 1.0, 25.0, 1.0, 10.0, 1500.0, 30.0, 40.0, 60.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_teams(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0, 'retained_earnings': 138000.0
        }
        prev_stats = { 'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 'rx_per_hr': 5.0, 'otc_markup': 45.0 }
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 3. LOGIC ENGINE
# ==========================================
def calculate_results():
    rx_w_df = st.session_state.rx_weights_df; mkt = st.session_state.market_data_list
    
    # Market Data Unpacking
    BASE_COST_RX = mkt[0]; PCT_3RD_PARTY = mkt[3]/100.0
    INT_RATE_LOAN = mkt[8]/100.0; AVG_RX_VOL = mkt[9]; AVG_OTC_VOL = mkt[10]
    WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    
    store_list = [p for p in st.session_state.players.values()]
    
    # 1. Market Share Calculation
    data = []
    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        data.append({
            'id': tid, 'loc': p['location_code'], 'price': price,
            'promo': inp[7], 'hours': inp[6], 'mkt_share': prev['mkt_share']
        })
    df_comp = pd.DataFrame(data)
    rx_shares = {}; otc_shares = {}
    
    for loc_code in [1, 2, 3]:
        sub_df = df_comp[df_comp['loc'] == loc_code].copy()
        if sub_df.empty: continue
        loc_name = LOC_MAP[loc_code]
        rx_w = rx_w_df.set_index("Factor")[loc_name].values
        # Simple Ranking
        sub_df['score'] = (sub_df['price'].rank(ascending=False)*rx_w[0]) + (sub_df['promo'].rank(ascending=True)*rx_w[1])
        tot = sub_df['score'].sum()
        for idx, row in sub_df.iterrows(): rx_shares[row['id']] = row['score']/tot if tot else 0
        for idx, row in sub_df.iterrows(): otc_shares[row['id']] = 1.0/len(sub_df)

    # 2. Financials & Detailed Metrics
    total_rx_mkt = AVG_RX_VOL * len(store_list)
    total_otc_mkt = AVG_OTC_VOL * len(store_list)
    
    for p in store_list:
        if p['location_code'] == 0: continue
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        
        # Sales Logic
        my_rx_sh = rx_shares.get(tid, 0); my_otc_sh = otc_shares.get(tid, 0)
        rx_count = total_rx_mkt * my_rx_sh
        rx_3pty_count = rx_count * PCT_3RD_PARTY
        
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        rx_sales = rx_count * price
        otc_sales = total_otc_mkt * my_otc_sh
        tot_sales = rx_sales + otc_sales
        
        # COGS
        cost_rx = rx_sales / (price/BASE_COST_RX) if price else 0
        cost_otc = otc_sales / (1 + inp[13]/100)
        
        gm_rx = rx_sales - cost_rx
        gm_total = tot_sales - cost_rx - cost_otc
        
        # Expenses & Overtime Logic
        std_hours = 40 * WEEKS_PER_PERIOD
        hrs_open = inp[6] * WEEKS_PER_PERIOD
        ot_hours = max(0, hrs_open - std_hours)
        
        # Pharmacist
        rph_base_pay = inp[17] * std_hours * inp[18]
        rph_ot_pay = inp[17] * ot_hours * inp[18] * 1.5
        rph_total = rph_base_pay + rph_ot_pay
        
        # Clerk
        clk_base_pay = inp[19] * std_hours * inp[20]
        clk_ot_pay = inp[19] * ot_hours * inp[20] * 1.5
        clk_total = clk_base_pay + clk_ot_pay
        
        rent = tot_sales * LOC_RENT_RATE.get(p['location_code'], 0.03)
        mortgage = inp[24]
        promo = inp[7]
        mgr_sal = inp[21]
        intr = (fin['long_term_debt'] + fin['notes_payable']) * INT_RATE_LOAN
        
        total_exp = rph_total + clk_total + rent + mortgage + promo + mgr_sal + intr + 3000
        net_profit = gm_total - total_exp
        
        # Cash Flow & Balance Sheet Update
        cash_start = fin['cash']
        fin['cash'] += (net_profit + inp[30] - inp[9]) # Simplified Ops Cash Flow
        
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
            net_profit -= e_loan * 0.2
            
        fin['retained_earnings'] += net_profit
        
        # --- PREPARE REPORT DATA ---
        curr_assets = fin['cash'] + fin['acct_receivable'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['investments']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        total_assets = curr_assets + fin['fixed_assets']
        nw = fin['retained_earnings']
        
        metrics = {
            "TOT SALES": tot_sales,
            "Rx SALES": rx_sales,
            "OTH SALES": otc_sales,
            "Avg Rx Pr": price,
            "Rx Ing $": BASE_COST_RX,
            "Rx GM%": (gm_rx/rx_sales*100) if rx_sales else 0,
            "3-Pty GM%": (gm_rx/rx_sales*100) * 0.9, # Simulated lower margin
            "Tot #Rx's": rx_count,
            "3-Pty #Rx": rx_3pty_count,
            "Copay Dis": inp[2],
            "OTC M'kup": inp[13],
            "Rx Mkt Sh": my_rx_sh * 100,
            "Store Hrs": inp[6],
            "A/P Paid": inp[28],
            "M'age Pay": mortgage,
            "E. Loan": e_loan,
            "Mgr Hrs": inp[22],
            "RP OverT": ot_hours / WEEKS_PER_PERIOD, # Avg per week
            "RP Hr Pay": inp[18],
            "Clk OverT": ot_hours / WEEKS_PER_PERIOD,
            "Clk Wage": inp[20],
            "Adv Exp": promo,
            "Net Worth": nw,
            "Cash Flow": fin['cash'] - cash_start, # Net change
            "E Rx Pur": inp[14], # Using purchase input as proxy
            "E OTC Pur": inp[15],
            
            # RATIOS
            "Current": curr_assets / curr_liab if curr_liab else 0,
            "Acid Test": (fin['cash'] + fin['acct_receivable'] + fin['investments']) / curr_liab if curr_liab else 0,
            "Turnover": (cost_rx+cost_otc) / ((fin['inventory_rx']+fin['inventory_otc'])/2) if fin['inventory_rx'] else 0,
            "ROI": (net_profit / nw * 100) if nw else 0,
            "ROA": (net_profit / total_assets * 100) if total_assets else 0,
            "G Margin": (gm_total / tot_sales * 100) if tot_sales else 0,
            "Profit": (net_profit / tot_sales * 100) if tot_sales else 0,
            "Debt/NW": (fin['long_term_debt'] + curr_liab) / nw if nw else 0,
            
            "LOCATION": LOC_MAP[p['location_code']]
        }
        
        p['history'].append(metrics)
        p['status'] = 'Pending'
        p['period'] += 1 # Increment Student Period
        p['prev_stats']['mkt_share'] = my_rx_sh

    st.session_state.global_period += 1

# ==========================================
# 4. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V30")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    state = st.session_state.game_state
    
    # SETUP PHASE
    if state == "SETUP_STEP_1":
        st.markdown('<div class="step-header">Step 1: Teams</div>', unsafe_allow_html=True)
        n = st.number_input("Number of Teams", 1, 20, 5)
        if st.button("Next ➡️"): initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()
    elif state == "SETUP_STEP_2":
        st.markdown('<div class="step-header">Step 2: Weights</div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Rx Weights", "OTC Weights"])
        with t1: st.session_state.rx_weights_df = st.data_editor(st.session_state.rx_weights_df)
        with t2: st.session_state.otc_weights_df = st.data_editor(st.session_state.otc_weights_df)
        if st.button("Next ➡️"): st.session_state.game_state="SETUP_STEP_3"; st.rerun()
    elif state == "SETUP_STEP_3":
        st.markdown('<div class="step-header">Step 3: Initial Environment</div>', unsafe_allow_html=True)
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=400, use_container_width=True)
        if st.button("🏁 START GAME", type="primary"): 
            st.session_state.market_data_list = edited_df['Value'].tolist()
            st.session_state.game_state="ACTIVE"
            st.rerun()

    # ACTIVE PHASE
    elif state == "ACTIVE":
        st.success(f"### Results for Period {st.session_state.global_period - 1}")
        
        # --- FULL REPORT TABLE ---
        if any(p['history'] for p in st.session_state.players.values()):
            # Collect data
            report_data = {}
            metrics_order = list(st.session_state.players['team_1']['history'][-1].keys())
            
            for tid, p in st.session_state.players.items():
                if p['history']:
                    last_metrics = p['history'][-1]
                    report_data[p['shop_name']] = [last_metrics[m] for m in metrics_order]
            
            df_rep = pd.DataFrame(report_data, index=metrics_order)
            
            # Formatting
            def format_val(val, idx):
                if idx == "LOCATION": return val
                if any(x in idx for x in ["%", "Rate", "ROI", "ROA", "Margin", "Profit"]): return f"{val:.2f}%"
                if any(x in idx for x in ["$", "SALES", "Cost", "Pay", "Wage", "Exp", "Worth", "Flow", "Pur"]): return f"${val:,.0f}"
                return f"{val:,.2f}"

            for col in df_rep.columns:
                df_rep[col] = [format_val(v, i) for i, v in zip(df_rep.index, df_rep[col])]
            
            st.dataframe(df_rep, height=800, use_container_width=True)
        
        st.divider()
        c1, c2 = st.columns([3, 2])
        ready_count = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        c1.metric("Students Submitted", f"{ready_count}/{len(st.session_state.players)}")
        
        if c2.button("⚙️ Setup Next Period", type="primary"):
            st.session_state.game_state = "MARKET_EDIT_RUN"
            st.rerun()

    elif state == "MARKET_EDIT_RUN":
        st.markdown(f'<div class="step-header">🚨 Market Environment: Period {st.session_state.global_period}</div>', unsafe_allow_html=True)
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=500, use_container_width=True)
        if st.button("🧮 RUN PERIOD", type="primary"):
            st.session_state.market_data_list = edited_df['Value'].tolist()
            calculate_results()
            st.session_state.game_state="ACTIVE"
            st.rerun()

def render_student_ui():
    if st.session_state.game_state not in ["ACTIVE", "MARKET_EDIT_RUN"]: 
        st.warning("⏳ Waiting for Instructor to start game..."); return
    
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    # --- STUDENT FLOW ---
    
    # 1. SETUP (Period 1 Only)
    if p['period'] == 1 and p['status'] == 'Pending' and not p['history']:
        st.info("👋 Welcome! Please set up your store.")
        c1, c2 = st.columns(2)
        n = c1.text_input("Store Name", p['shop_name'])
        l = c2.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Start Operations") and l!=0: 
            p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return

    # 2. OPERATIONS (Period > 1 or Period 1 Thinking)
    st.markdown(f"### 🏥 {p['shop_name']}")
    st.caption(f"Location: {LOC_MAP[p['location_code']]} | Period: {p['period']}")
    
    tab1, tab2 = st.tabs(["📋 Decisions", "📊 Previous Results"])
    
    with tab1:
        if p['status'] == 'Submitted':
            st.success("✅ Decisions Submitted. Waiting for Instructor.")
            if st.button("Edit Decisions"): p['status']='Thinking'; st.rerun()
        else:
            st.write("Edit your inputs for this period:")
            df = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df, hide_index=True, height=500)
            if st.button("Submit Decisions", type="primary"):
                p['inputs'] = ed['Value'].tolist()
                p['status'] = 'Submitted'
                st.rerun()
                
    with tab2:
        if p['history']:
            last = p['history'][-1]
            st.write(f"**Results from Period {last.get('Period', '?')}**")
            
            # Simple Student View (Subset of full data)
            stud_metrics = ["TOT SALES", "Net Profit", "Cash Flow", "Net Worth", "Rx Mkt Sh"]
            cols = st.columns(len(stud_metrics))
            for i, m in enumerate(stud_metrics):
                cols[i].metric(m, f"{last.get(m, 0):,.0f}" if "Sh" not in m else f"{last.get(m, 0):.2f}%")
            
            st.json(last) # Show full details
        else:
            st.info("No results yet. Submit decisions for Period 1.")

# ROUTER
role = st.sidebar.selectbox("User Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Password", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
