import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V28 (Dynamic Market)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .fin-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dotted #eee; }
    .fin-value { font-family: 'Courier New', monospace; font-weight: bold; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white;}
    .badge-submitted { background-color: #4caf50; }
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

# 28 Market Variables provided by user
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

# Default Market Data (Standard Values)
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
    mkt = st.session_state.market_data_list # LIST OF 28 VARIABLES
    
    # --- Unpack Dynamic Market Data ---
    BASE_COST_RX = mkt[0]
    CONST_FEE = mkt[2] # 3rd Party Fee used as const fee? Or just const fee
    INT_RATE_LOAN = mkt[8]/100.0
    AVG_RX_VOL = mkt[9]
    AVG_OTC_VOL = mkt[10]
    WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    SALES_PER_CLERK = mkt[25]
    BENEFIT_PCT = mkt[27]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    if not store_list: return

    # 1. HMO Bidding
    hmo_bids = {p['id']: p['inputs'][35] for p in store_list if p['inputs'][35] > 0}
    hmo_winner_id = min(hmo_bids, key=hmo_bids.get) if hmo_bids else None

    # 2. Ranking & Scoring
    data = []
    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']; fin = p['financials']
        
        # Price Calculation
        if inp[0] > 10: calc_price = BASE_COST_RX * (1 + inp[0]/100)
        else: calc_price = BASE_COST_RX + inp[0]
        pres_price = calc_price + inp[1] # Using Fee input
        
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        data.append({
            'id': tid, 'loc': p['location_code'],
            'price_past': prev['avg_price'], 'price_pres': pres_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3], 'records': inp[4], 'credit': inp[5], 
            'inventory': inv_level, 'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr'],
            'otc_markup_past': prev.get('otc_markup', 45.0), 'otc_markup_pres': inp[13], 'advertising': inp[7]
        })
    df_comp = pd.DataFrame(data)

    # Calculate Shares (Simplified for brevity, same logic as before but using dynamic weights)
    # Note: Need to handle location 0 (not selected yet)
    rx_shares = {}; otc_shares = {}
    
    for loc_code in [1, 2, 3]:
        loc_name = LOC_MAP[loc_code]
        sub_df = df_comp[df_comp['loc'] == loc_code].copy()
        if sub_df.empty: continue
        
        rx_weights = rx_w_df.set_index("Factor")[loc_name].values
        otc_weights = otc_w_df.set_index("Factor")[loc_name].values
        
        # Rank within location
        sub_df['r0'] = sub_df['price_past'].rank(ascending=False)
        sub_df['r1'] = sub_df['price_pres'].rank(ascending=False)
        cols = ['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']
        for i, col in enumerate(cols): sub_df[f'r{i+2}'] = sub_df[col].rank(ascending=True)
        
        scores = sub_df.apply(lambda row: sum(row[f'r{i}'] * rx_weights[i] for i in range(10)), axis=1)
        
        # HMO Bonus
        if hmo_winner_id: scores[sub_df['id'] == hmo_winner_id] *= 1.15
        
        tot_s = scores.sum()
        for idx, val in scores.items(): rx_shares[sub_df.loc[idx, 'id']] = val/tot_s if tot_s else 0
        
        # OTC (Simplified Ranking)
        otc_sc = sub_df['otc_markup_pres'].rank(ascending=False) * otc_weights[1] + sub_df['advertising'].rank(ascending=True) * otc_weights[2]
        tot_o = otc_sc.sum()
        for idx, val in otc_sc.items(): otc_shares[sub_df.loc[idx, 'id']] = val/tot_o if tot_o else 0

    # 3. Financials
    total_market_rx = AVG_RX_VOL * len(store_list)
    total_market_otc = AVG_OTC_VOL * len(store_list)
    
    for p in store_list:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        if p['location_code'] == 0: continue # Skip if no location

        my_rx_share = rx_shares.get(tid, 0)
        my_otc_share = otc_shares.get(tid, 0)
        
        rx_count = total_market_rx * my_rx_share
        if inp[0] > 10: p_pr = BASE_COST_RX * (1 + inp[0]/100)
        else: p_pr = BASE_COST_RX + inp[0]
        p_pr += inp[1]
        
        rx_sales = rx_count * p_pr
        otc_sales = total_market_otc * my_otc_share
        tot_sales = rx_sales + otc_sales
        
        cost_rx = rx_sales / (p_pr/BASE_COST_RX) if p_pr else 0
        cost_otc = otc_sales / (1 + inp[13]/100)
        gm = tot_sales - (cost_rx + cost_otc)
        
        # Expenses
        hrs = inp[6]
        # Pharmacist Cost (FTE + Overtime) - Simplified logic using Inputs 17, 18
        # Assuming Input 17 is FTE count, Input 18 is Wage
        rph_wage = inp[17] * 40 * WEEKS_PER_PERIOD * inp[18] 
        
        # Clerk Cost - Driven by Sales/Clerk (Market Var 26)
        req_clerks = tot_sales / SALES_PER_CLERK if SALES_PER_CLERK else 1
        clk_wage = req_clerks * 40 * WEEKS_PER_PERIOD * inp[20]
        
        ben = (rph_wage + clk_wage) * BENEFIT_PCT
        rent = tot_sales * LOC_RENT_RATE.get(p['location_code'], 0.03)
        
        # Interest
        inte = (fin['long_term_debt'] + fin['notes_payable']) * INT_RATE_LOAN
        
        exp = rph_wage + clk_wage + ben + rent + inp[7] + inp[21] + inp[24] + inte + inp[29]
        
        profit = gm - exp + (fin['investments'] * (mkt[24]/100)) # Investment return
        
        # Cash Flow & Balance Sheet Updates
        fin['investments'] += (inp[9]-inp[11])
        fin['inventory_rx'] = max(0, fin['inventory_rx'] + inp[14] - cost_rx)
        fin['inventory_otc'] = max(0, fin['inventory_otc'] + inp[15] - cost_otc)
        
        cash_ops = tot_sales - (exp - inte) # Approximate
        fin['cash'] += (cash_ops - inp[9] - inp[30])
        fin['long_term_debt'] -= inp[30]
        
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan
            profit -= (e_loan * 0.20) # Penalty
            
        fin['retained_earnings'] += profit
        
        p['prev_stats'].update({'avg_price': p_pr, 'mkt_share': my_rx_share, 'rx_per_hr': rx_count/500}) # approx
        
        # History
        p['history'].append({
            "Period": st.session_state.global_period,
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Avg Rx Pr": p_pr, "Rx Ing $": BASE_COST_RX, 
            "Rx GM%": ((rx_sales-cost_rx)/rx_sales*100) if rx_sales else 0,
            "Tot #Rx's": rx_count, "Rx Mkt Sh": my_rx_share*100,
            "Net Worth": fin['retained_earnings'], "Cash Flow": cash_ops,
            "LOCATION": LOC_MAP[p['location_code']],
            "Income_Statement": {
                "Sales": {"Total": tot_sales}, "Gross Margin": gm,
                "Expenses": {"Total": exp}, "Net Profit": profit
            },
            "Balance_Sheet": {
                "Assets": {"Cash": fin['cash'], "Total": fin['cash']+fin['inventory_rx']+fin['inventory_otc']},
                "Liabilities": {"Total": fin['acct_payable']+fin['long_term_debt']}, "Equity": fin['retained_earnings']
            }
        })
        p['status'] = 'Pending'
        
    st.session_state.global_period += 1

# ==========================================
# 4. UI
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V28")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    # --- STEP 1: TEAMS ---
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown('<div class="step-header">Step 1: Game Initialization</div>', unsafe_allow_html=True)
        n = st.number_input("Teams", 1, 20, 5)
        if st.button("Next ➡️"): initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()
        
    # --- STEP 2: WEIGHTS ---
    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown('<div class="step-header">Step 2: Scoring Weights</div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Rx", "OTC"])
        with t1: st.session_state.rx_weights_df = st.data_editor(st.session_state.rx_weights_df)
        with t2: st.session_state.otc_weights_df = st.data_editor(st.session_state.otc_weights_df)
        c1, c2 = st.columns([1,5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_1"; st.rerun()
        if c2.button("Start Game 🚀", type="primary"): st.session_state.game_state="ACTIVE"; st.rerun()
            
    # --- ACTIVE GAME ---
    elif st.session_state.game_state == "ACTIVE":
        st.write(f"### 🏙️ City Status - Period {st.session_state.global_period-1}")
        
        # Display Summary Table
        if any(p['history'] for p in st.session_state.players.values()):
            metrics = ["TOT SALES", "Rx SALES", "Rx GM%", "Rx Mkt Sh", "Net Worth", "ROI", "LOCATION"]
            data = {p['shop_name']: [p['history'][-1].get(m,0) for m in metrics] for p in st.session_state.players.values() if p['history']}
            st.dataframe(pd.DataFrame(data, index=metrics).style.format("{:.2f}"))
        
        # Controls
        st.divider()
        col_stat, col_act = st.columns([3, 1])
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        col_stat.metric("Teams Ready", f"{ready}/{len(st.session_state.players)}")
        
        if col_act.button("⚙️ Setup Next Period"):
            st.session_state.game_state = "MARKET_EDIT"
            st.rerun()

    # --- MARKET EDIT (New Screen) ---
    elif st.session_state.game_state == "MARKET_EDIT":
        st.markdown(f'<div class="step-header">🌍 Edit Market Environment (Period {st.session_state.global_period})</div>', unsafe_allow_html=True)
        st.info("Modify these variables to create scenarios (e.g., Inflation, Low Demand).")
        
        # Create DataFrame for editing
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=600, use_container_width=True)
        
        c1, c2 = st.columns([1, 5])
        if c1.button("⬅️ Back"): 
            st.session_state.game_state = "ACTIVE"
            st.rerun()
            
        if c2.button("✅ Confirm & Run Period", type="primary"):
            st.session_state.market_data_list = edited_df['Value'].tolist()
            calculate_results()
            st.session_state.game_state = "ACTIVE"
            st.rerun()

def render_student_ui():
    if st.session_state.game_state not in ["ACTIVE", "MARKET_EDIT"]: st.warning("Wait for class start..."); return
    
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    if p['period'] == 1 and p['status'] == 'Pending':
        c1, c2 = st.columns(2)
        n = c1.text_input("Name", p['shop_name']); l = c2.selectbox("Loc", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Confirm") and l!=0: p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return

    tab1, tab2 = st.tabs(["Decisions", "Report"])
    with tab1:
        if p['status']=='Submitted': st.success("Submitted"); st.button("Unsubmit", on_click=lambda:p.update({'status':'Thinking'}))
        else:
            df = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df, hide_index=True, height=500)
            if st.button("Submit"): p['inputs']=ed['Value'].tolist(); p['status']='Submitted'; st.rerun()
    with tab2:
        if p['history']:
            last = p['history'][-1]
            st.write(f"**Period {last['Period']} Report**")
            st.json(last['Income_Statement'])
            st.json(last['Balance_Sheet'])
        else: st.info("No Data")

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
