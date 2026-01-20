import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V29 (Strict Flow)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white;}
    .badge-submitted { background-color: #4caf50; }
    .badge-pending { background-color: #ff9800; }
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
    st.session_state.game_state = "SETUP_STEP_1" # 1:Teams, 2:Weights, 3:InitEnv, ACTIVE
    st.session_state.global_period = 1
    st.session_state.players = {}

# Default Market Data
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
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    mkt = st.session_state.market_data_list
    
    BASE_COST_RX = mkt[0]; INT_RATE_LOAN = mkt[8]/100.0
    AVG_RX_VOL = mkt[9]; AVG_OTC_VOL = mkt[10]; SALES_PER_CLERK = mkt[25]; BENEFIT_PCT = mkt[27]/100.0
    WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    
    store_list = [p for p in st.session_state.players.values()]
    
    # 1. Ranking Logic
    data = []
    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']; fin = p['financials']
        calc_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        data.append({
            'id': tid, 'loc': p['location_code'], 'price': calc_price,
            'promo': inp[7], 'hours': inp[6], 'mkt_share': prev['mkt_share'],
            'otc_markup': inp[13]
        })
    df_comp = pd.DataFrame(data)
    
    rx_shares = {}; otc_shares = {}
    for loc_code in [1, 2, 3]:
        sub_df = df_comp[df_comp['loc'] == loc_code].copy()
        if sub_df.empty: continue
        loc_name = LOC_MAP[loc_code]
        rx_w = rx_w_df.set_index("Factor")[loc_name].values
        
        # Simplified Scoring
        sub_df['score'] = (sub_df['price'].rank(ascending=False)*rx_w[0]) + (sub_df['promo'].rank(ascending=True)*rx_w[1]) + (sub_df['hours'].rank(ascending=True)*rx_w[2])
        tot = sub_df['score'].sum()
        for idx, row in sub_df.iterrows(): rx_shares[row['id']] = row['score']/tot if tot else 0
        for idx, row in sub_df.iterrows(): otc_shares[row['id']] = 1.0/len(sub_df) # Equal share for OTC simplified

    # 2. Financials
    total_rx_mkt = AVG_RX_VOL * len(store_list)
    total_otc_mkt = AVG_OTC_VOL * len(store_list)
    
    for p in store_list:
        if p['location_code'] == 0: continue
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        
        my_rx = rx_shares.get(tid, 0); my_otc = otc_shares.get(tid, 0)
        rx_cnt = total_rx_mkt * my_rx
        
        price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        rx_rev = rx_cnt * price
        otc_rev = total_otc_mkt * my_otc
        tot_rev = rx_rev + otc_rev
        
        cogs_rx = rx_rev / (price/BASE_COST_RX) if price else 0
        cogs_otc = otc_rev / (1 + inp[13]/100)
        gm = tot_rev - cogs_rx - cogs_otc
        
        # Exp
        wages = (inp[17]*inp[18] + (tot_rev/SALES_PER_CLERK/WEEKS_PER_PERIOD)*inp[20]) * 40 * WEEKS_PER_PERIOD if SALES_PER_CLERK else 0
        rent = tot_rev * LOC_RENT_RATE.get(p['location_code'], 0.03)
        intr = (fin['long_term_debt']+fin['notes_payable']) * INT_RATE_LOAN
        exp = wages + rent + intr + inp[7] + inp[21] + inp[24] + 3000
        
        profit = gm - exp
        
        # Cash & BS
        fin['cash'] += (profit + inp[30] - inp[9]) # Simplified CF
        if fin['cash'] < 0:
            loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += loan; fin['cash'] += loan
            profit -= loan*0.2
            
        fin['retained_earnings'] += profit
        
        p['history'].append({
            "Period": st.session_state.global_period,
            "TOT SALES": tot_rev, "Rx SALES": rx_rev, "Net Profit": profit,
            "Cash": fin['cash'], "Net Worth": fin['retained_earnings'],
            "Income_Statement": {"Sales": tot_rev, "Net Profit": profit},
            "Balance_Sheet": {"Assets": fin['cash'], "Equity": fin['retained_earnings']}
        })
        p['status'] = 'Pending'
        p['prev_stats']['mkt_share'] = my_rx

    st.session_state.global_period += 1

# ==========================================
# 4. UI ROUTER
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V29")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    state = st.session_state.game_state

    # --- STEP 1: TEAMS ---
    if state == "SETUP_STEP_1":
        
        st.markdown('<div class="step-header">Step 1: Game Initialization (Teams)</div>', unsafe_allow_html=True)
        n = st.number_input("Number of Teams", 1, 20, 5)
        if st.button("Next: Set Weights ➡️"): 
            initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()

    # --- STEP 2: WEIGHTS ---
    elif state == "SETUP_STEP_2":
        
        st.markdown('<div class="step-header">Step 2: Define Scoring Weights</div>', unsafe_allow_html=True)
        st.warning("⚠️ Weights cannot be changed after this step.")
        t1, t2 = st.tabs(["Rx Weights", "OTC Weights"])
        with t1: st.session_state.rx_weights_df = st.data_editor(st.session_state.rx_weights_df)
        with t2: st.session_state.otc_weights_df = st.data_editor(st.session_state.otc_weights_df)
        
        c1, c2 = st.columns([1,5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_1"; st.rerun()
        if c2.button("Next: Initial Environment ➡️", type="primary"): 
            st.session_state.game_state="SETUP_STEP_3"; st.rerun()

    # --- STEP 3: INITIAL ENVIRONMENT ---
    elif state == "SETUP_STEP_3":
        
        st.markdown('<div class="step-header">Step 3: Initial Market Environment (Period 1)</div>', unsafe_allow_html=True)
        st.info("Set the starting market conditions. You can edit this again before running Period 2.")
        
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=600, use_container_width=True)
        
        c1, c2 = st.columns([1,5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_2"; st.rerun()
        if c2.button("🏁 LOCK & START GAME", type="primary"): 
            st.session_state.market_data_list = edited_df['Value'].tolist()
            st.session_state.game_state="ACTIVE"
            st.rerun()

    # --- ACTIVE GAME LOOP ---
    elif state == "ACTIVE":
        st.success(f"### ✅ Game Active: Period {st.session_state.global_period}")
        st.info("Wait for students to submit decisions, then click 'Setup & Run' to adjust the environment and process results.")
        
        # Summary
        if any(p['history'] for p in st.session_state.players.values()):
            data = {p['shop_name']: [p['history'][-1]['Net Profit'], p['history'][-1]['Net Worth']] for p in st.session_state.players.values() if p['history']}
            st.dataframe(pd.DataFrame(data, index=["Net Profit", "Net Worth"]))

        # Action Area
        st.divider()
        col_stat, col_btn = st.columns([3, 2])
        ready_count = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        col_stat.metric("Students Ready", f"{ready_count}/{len(st.session_state.players)}")
        
        if col_btn.button("⚙️ Setup & Run Period", type="primary"):
            st.session_state.game_state = "MARKET_EDIT_RUN"
            st.rerun()

    # --- MARKET EDIT (Before Running) ---
    elif state == "MARKET_EDIT_RUN":
        
        st.markdown(f'<div class="step-header">🚨 Market Shift: Period {st.session_state.global_period}</div>', unsafe_allow_html=True)
        st.warning("Adjust the environment variables below to create scenarios for this period. Then click 'Calculate'.")
        
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=500, use_container_width=True, key="mkt_editor")
        
        c1, c2 = st.columns([1,5])
        if c1.button("❌ Cancel"): st.session_state.game_state="ACTIVE"; st.rerun()
        if c2.button("🧮 CONFIRM & CALCULATE RESULTS", type="primary"):
            st.session_state.market_data_list = edited_df['Value'].tolist()
            calculate_results()
            st.session_state.game_state="ACTIVE"
            st.rerun()

def render_student_ui():
    if st.session_state.game_state not in ["ACTIVE", "MARKET_EDIT_RUN"]: 
        st.warning("⏳ Please wait for the Instructor to start the game."); return
    
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Your Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    if p['period'] == 1 and p['status'] == 'Pending':
        st.info("Welcome! Please name your store and select a location.")
        c1, c2 = st.columns(2)
        n = c1.text_input("Store Name", p['shop_name']); l = c2.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Start Period 1") and l!=0: p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return

    tab1, tab2 = st.tabs(["📋 Decisions", "📊 Reports"])
    with tab1:
        if p['status']=='Submitted': 
            st.success("Decisions Submitted! Waiting for processing..."); 
            st.button("Edit", on_click=lambda: p.update({'status':'Thinking'}))
        else:
            df = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df, hide_index=True, height=500)
            if st.button("Submit Decisions", type="primary"): p['inputs']=ed['Value'].tolist(); p['status']='Submitted'; st.rerun()
    with tab2:
        if p['history']:
            last = p['history'][-1]
            st.metric("Net Profit", f"${last['Net Profit']:,.2f}")
            st.json(last)
        else: st.info("Reports will appear here after Period 1 ends.")

role = st.sidebar.selectbox("User Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Password", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
