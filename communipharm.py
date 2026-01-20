import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V33 (Corrected 29 Vars)", layout="wide")

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
# Student Inputs 1-36
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

# Instructor Data Labels (Exactly 29 Variables based on analysis)
INST_LABELS_29 = [
    "1. Avg Rx Ing Cost ($)", "2. Avg 3rd-Party Copay", "3. Avg 3rd-Party Fee",
    "4. % Market 3rd-Party", "5. Max Ad Allow ($)", "6. % AR (Medical)",
    "7. % AR (Neighbor)", "8. % AR (Shopping)", "9. Interest Rate (%)",
    "10. Avg Rx Volume", "11. Avg OTC Sales ($)", "12. GM Slippage Rate",
    "13. # Periods/Year", "14. % 3rd-Party Lag", "15. % AR Lag",
    "16. MF Value/Share", "17. Date (Unused)", "18. Date (Month)",
    "19. Date (Day)", "20. Date (Year)", "21. Inflation Rate (%)",
    "22. Rx Purch Index", "23. OTC Purch Index", "24. Savings Rate (%)",
    "25. End MF Quote", "26. CD Interest (%)", "27. Sales/Clerk/Hr ($)",
    "28. Benefits (%)", "29. Emergency Rate/Misc"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.025}

RX_WEIGHTS_CONFIG = {
    "Price_Past": [10, 20, 25], "Price_Pres": [30, 25, 30], "Promo": [5, 10, 15],
    "Hours": [20, 10, 5], "Delivery": [5, 10, 0], "Records": [10, 5, 0],
    "Credit": [5, 5, 5], "Inventory": [5, 5, 0], "MktShare": [5, 5, 5], "Efficiency": [5, 5, 0]
}
OTC_WEIGHTS_CONFIG = {
    "Markup_Past": [10, 20, 10], "Markup_Pres": [20, 30, 40], "Ad_Index": [20, 20, 30],
    "Hours": [10, 10, 10], "Inventory": [10, 10, 10], "RxShare": [30, 10, 0]
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

# Default Instructor Data (29 Variables)
# Derived from: 11.23 2 2.75 ... 28.5 23
if 'inst_data_list' not in st.session_state:
    st.session_state.inst_data_list = [
        11.23, 2.0, 2.75, 46.43, 1200.0, 30.2, 21.2, 9.34, 10.5, 
        5949.0, 74500.0, 0.1, 6.0, 14.4, 11.2, 0.0, 0.0, 26.4, 6.0, 30.0, 
        89.0, 1.1, 77.0, 55.0, 5.25, 27.65, 7.88, 28.5, 23.0
    ]

if 'rx_weights_df' not in st.session_state: st.session_state.rx_weights_df = pd.DataFrame(RX_WEIGHTS_CONFIG)
if 'otc_weights_df' not in st.session_state: st.session_state.otc_weights_df = pd.DataFrame(OTC_WEIGHTS_CONFIG)

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
        prev_stats = { 
            'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 
            'ad_index': 1.0, 'rx_per_hr': 5.0, 'otc_markup': 45.0,
            'cogs_rx': 35000.0, 'avg_inv_rx': 50000.0, 'cogs_otc': 15000.0, 'avg_inv_otc': 20000.0
        }
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 3. LOGIC ENGINE
# ==========================================
def calculate_results():
    store_list = [p for p in st.session_state.players.values()]
    num_stores = len(store_list)
    
    # --- MAP INSTRUCTOR DATA (29 VARS) ---
    inst = st.session_state.inst_data_list
    # Index 0 corresponds to Label 1.
    BASE_RX_COST = inst[0]      # 1. Avg Rx Ing Cost
    CONST_FEE = 2.90            # Constant fee from V21 logic (not in 29 vars explicitly, usually fixed)
    AD_LIMIT = inst[4]          # 5. Max Ad Allow
    INTEREST_RATE = inst[8]/100 # 9. Interest Rate
    RX_MKT_VOL = inst[9]        # 10. Avg Rx Vol
    OTC_MKT_VAL = inst[10]      # 11. Avg OTC Sales
    SALES_PER_CLK = inst[26]    # 27. Sales/Clerk/Hr
    BENEFIT_PCT = inst[27]      # 28. Benefits % (e.g. 28.5 or 8.5)
    EMERGENCY_RATE = 400.0      # Hardcoded or use Var 29 if it represents rate
    if inst[28] > 100: EMERGENCY_RATE = inst[28] # If var 29 is large, assume it's rate
    
    # --- PHASE 1: RANKING PREP ---
    ranking_data = []
    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']; fin = p['financials']
        
        # Price Calc
        if inp[0] > 10: calc_price = BASE_RX_COST * (1 + inp[0]/100)
        else: calc_price = BASE_RX_COST + inp[0]
        pres_price = max(calc_price, 5.0) + CONST_FEE
        
        # Ad Index
        def calc_ad(curr, past):
            factor = min((curr/AD_LIMIT) + (past*0.533), 2.0)
            return max(0, (0.84*factor) - (0.16*(factor**2)))
        
        new_rx_ad = calc_ad(inp[7] * (inp[8]/100), prev.get('ad_index', 1.0))
        new_otc_ad = calc_ad(inp[7] * (1 - inp[8]/100), prev.get('ad_index', 1.0))
        
        # Inv Level
        def calc_inv(cogs, avg_inv): return cogs/avg_inv if avg_inv>0 else 10
        rx_inv = calc_inv(prev.get('cogs_rx',1), prev.get('avg_inv_rx',1))
        otc_inv = calc_inv(prev.get('cogs_otc',1), prev.get('avg_inv_otc',1))
        
        ranking_data.append({
            'id': tid, 'loc_idx': max(0, p['location_code']-1),
            'Price_Past': prev['avg_price'], 'Price_Pres': pres_price,
            'Promo': new_rx_ad, 'Hours': inp[6],
            'Delivery': inp[3], 'Records': inp[4], 'Credit': inp[5],
            'Inventory': rx_inv, 'MktShare': prev['mkt_share'], 'Efficiency': prev.get('rx_per_hr',5),
            'Markup_Past': prev.get('otc_markup',45), 'Markup_Pres': inp[13],
            'Ad_Index_OTC': new_otc_ad, 'Inv_OTC': otc_inv
        })
        
    df = pd.DataFrame(ranking_data)
    
    # --- PHASE 2: SCORING ---
    def calc_pts(series, asc): return (num_stores + 1) - series.rank(method='min', ascending=asc)

    # Rx Scoring
    rx_sc = pd.Series(0.0, index=df.index)
    rx_map = [('Price_Past',1), ('Price_Pres',1), ('Promo',0), ('Hours',0), ('Delivery',0), ('Records',0), ('Credit',0), ('Inventory',1), ('MktShare',0), ('Efficiency',0)]
    rx_keys = list(st.session_state.rx_weights_df.columns)
    
    for idx, (col, asc) in enumerate(rx_map):
        pts = calc_pts(df[col], bool(asc))
        key = rx_keys[idx]
        wts = df['loc_idx'].apply(lambda x: st.session_state.rx_weights_df[key].iloc[x])
        rx_sc += pts * wts
        
    df['Rx_Share'] = rx_sc / rx_sc.sum()
    
    # OTC Scoring
    df['Rx_Share_Val'] = df['Rx_Share'] * 100
    otc_sc = pd.Series(0.0, index=df.index)
    otc_map = [('Markup_Past',1), ('Markup_Pres',1), ('Ad_Index_OTC',0), ('Hours',0), ('Inv_OTC',1), ('Rx_Share_Val',0)]
    otc_keys = list(st.session_state.otc_weights_df.columns)
    
    for idx, (col, asc) in enumerate(otc_map):
        pts = calc_pts(df[col], bool(asc))
        key = otc_keys[idx]
        wts = df['loc_idx'].apply(lambda x: st.session_state.otc_weights_df[key].iloc[x])
        otc_sc += pts * wts
        
    df['OTC_Share'] = otc_sc / otc_sc.sum()
    
    rx_share_map = df.set_index('id')['Rx_Share'].to_dict()
    otc_share_map = df.set_index('id')['OTC_Share'].to_dict()
    
    # --- PHASE 3: FINANCIALS ---
    hmo_bids = {p['id']: p['inputs'][35] for p in store_list if p['inputs'][35] > 0}
    hmo_win = min(hmo_bids, key=hmo_bids.get) if hmo_bids else None
    
    for p in store_list:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        share = rx_share_map[tid]
        if tid == hmo_win: share *= 1.15
        
        # Sales
        rx_cnt = RX_MKT_VOL * num_stores * share
        if inp[0]>10: p_pr = BASE_RX_COST*(1+inp[0]/100)
        else: p_pr = BASE_RX_COST + inp[0]
        p_pr = max(p_pr, 5.0) + CONST_FEE
        
        rx_sale = rx_cnt * p_pr
        otc_sale = OTC_MKT_VAL * num_stores * otc_share_map[tid]
        tot_sale = rx_sale + otc_sale
        
        # COGS
        cost_rx = rx_sale / (p_pr/BASE_RX_COST)
        cost_otc = otc_sale * 0.65
        gm = tot_sale - (cost_rx + cost_otc)
        
        # Staffing (90% Rule)
        p_fte = inp[16] # Input 17
        c_fte = inp[18] # Input 19
        
        # Wages
        avail_p = (p_fte*40*13) + (inp[22]/100*inp[22]*13)
        req_p = rx_cnt/10.0
        p_ot = max(0, req_p - avail_p)
        w_p = (avail_p*inp[17]) + (p_ot*EMERGENCY_RATE*1.5)
        
        avail_c = c_fte*40*13
        req_c = tot_sale/SALES_PER_CLK # Var 27
        c_ot = max(0, req_c - avail_c)
        w_c = (avail_c*inp[19]) + (c_ot*inp[19]*1.5)
        
        # Benefits (Using Var 28)
        ben = (w_p + w_c) * (BENEFIT_PCT/100.0) 
        
        # Expenses
        rent = tot_sale * LOC_RENT_RATE.get(p['location_code'], 0.03)
        exp = w_p + w_c + ben + rent + inp[7] + inp[20] + inp[23] + 3000
        
        depr = fin['fixed_assets']*0.02
        bad = inp[29]
        inte = (fin['long_term_debt']+fin['notes_payable']) * INTEREST_RATE # Var 9
        
        opex = exp + depr + inte + bad
        profit = gm - opex + (fin['investments']*0.015)
        
        # Cash & Balances
        fin['investments'] += (inp[9]-inp[11])
        fin['inventory_rx'] = max(0, fin['inventory_rx'] + inp[14] - cost_rx)
        fin['inventory_otc'] = max(0, fin['inventory_otc'] + inp[15] - cost_otc)
        
        c_ops = tot_sale - (exp + inte)
        fin['cash'] += (c_ops - inp[28] - inp[9] - inp[30])
        fin['acct_payable'] += (inp[14]+inp[15]-inp[28])
        fin['long_term_debt'] -= inp[30]
        
        e_loan = 0; pen = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
            pen = e_loan * 0.20; profit -= pen; fin['retained_earnings'] -= pen; opex += pen
            
        fin['retained_earnings'] += profit
        
        # Update Stats
        p['prev_stats'].update({
            'avg_price': p_pr, 'mkt_share': share*100, 
            'ad_index': df[df['id']==tid]['Promo'].values[0],
            'cogs_rx': cost_rx, 'avg_inv_rx': (fin['inventory_rx']+inp[14])/2,
            'cogs_otc': cost_otc, 'avg_inv_otc': (fin['inventory_otc']+inp[15])/2
        })
        
        # History
        def safe(n,d): return n/d if d!=0 else 0
        nw = fin['retained_earnings']
        ca = fin['cash']+fin['investments']+fin['inventory_rx']+fin['inventory_otc']
        cl = fin['acct_payable']+fin['notes_payable']
        
        p['history'].append({
            "Period": st.session_state.global_period,
            "TOT SALES": tot_sale, "Rx SALES": rx_sale, "OTH SALES": otc_sale,
            "Avg Rx Pr": p_pr, "Rx Ing $": BASE_RX_COST, "Rx GM%": safe(rx_sale-cost_rx, rx_sale)*100,
            "Tot #Rx's": rx_cnt, "Rx Mkt Sh": share*100, "Store Hrs": inp[6],
            "RP OverT": p_ot, "RP Hr Pay": EMERGENCY_RATE if p_ot>0 else inp[17],
            "Net Worth": nw, "Cash Flow": c_ops,
            "Current": safe(ca,cl), "ROI": safe(profit,nw)*100, "LOCATION": LOC_MAP[p['location_code']],
            "Income_Statement": {
                "Sales": {"Total": tot_sale, "Rx": rx_sale, "Other": otc_sale},
                "COGS": {"Total": cost_rx+cost_otc}, "Gross Margin": gm,
                "Expenses": {"Total": exp, "Penalty": pen}, "Net Profit": profit
            },
            "Balance_Sheet": {
                "Assets": {"Total": ca+fin['fixed_assets'], "Cash": fin['cash']},
                "Liabilities": {"Total": cl+fin['long_term_debt']}, "Equity": nw
            }
        })
        p['status'] = 'Pending'
    st.session_state.global_period += 1

# ==========================================
# 4. UI
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V33")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown('<div class="step-header">Step 1: Teams</div>', unsafe_allow_html=True)
        n = st.number_input("Teams", 1, 20, 5)
        if st.button("Next ➡️"): initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()
        
    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown('<div class="step-header">Step 2: Market Data (29 Variables)</div>', unsafe_allow_html=True)
        st.info("Paste your 31-token string here (Period# + 29 Vars + 1 Misc). The system will use the 29 variables.")
        
        # Raw String Paste
        raw_val = " ".join(map(str, [1] + st.session_state.inst_data_list + [0])) # Dummy display
        raw_str = st.text_area("Paste String", value=raw_val, height=70)
        
        if st.button("Parse String"):
            try:
                # Expecting ~31 tokens. 
                # Token 0 = Period (Ignore for list), Token 1..29 = Vars, Token 30 = Misc
                tokens = [float(x) for x in raw_str.split()]
                if len(tokens) >= 30:
                    st.session_state.inst_data_list = tokens[1:30] # Extract 29 vars
                    st.toast("Parsed 29 Variables Successfully!", icon="✅"); st.rerun()
                else: st.error(f"Need at least 30 tokens, got {len(tokens)}")
            except: st.error("Parse Error")
            
        # Table Editor
        df_inst = pd.DataFrame({"Label": INST_LABELS_29, "Value": st.session_state.inst_data_list})
        edited = st.data_editor(df_inst, height=600, hide_index=True)
        
        c1, c2 = st.columns([1,5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_1"; st.rerun()
        if c2.button("Next ➡️", type="primary"):
            st.session_state.inst_data_list = edited['Value'].tolist()
            st.session_state.game_state="SETUP_STEP_3"; st.rerun()
            
    elif st.session_state.game_state == "SETUP_STEP_3":
        st.markdown('<div class="step-header">Step 3: Weights</div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Rx Weights", "OTC Weights"])
        with t1: e1 = st.data_editor(st.session_state.rx_weights_df)
        with t2: e2 = st.data_editor(st.session_state.otc_weights_df)
        if st.button("Start Game"): 
            st.session_state.rx_weights_df=e1; st.session_state.otc_weights_df=e2; st.session_state.game_state="ACTIVE"; st.rerun()
            
    elif st.session_state.game_state == "ACTIVE":
        st.write(f"### City Summary - Period {st.session_state.global_period-1}")
        if any(p['history'] for p in st.session_state.players.values()):
            metrics = ["TOT SALES", "Rx SALES", "Rx GM%", "Rx Mkt Sh", "Net Worth", "ROI", "RP OverT", "RP Hr Pay", "LOCATION"]
            data = {p['shop_name']: [p['history'][-1].get(m,0) for m in metrics] for p in st.session_state.players.values() if p['history']}
            st.table(pd.DataFrame(data, index=metrics))
        
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        st.metric("Ready", f"{ready}/{len(st.session_state.players)}")
        if st.button("🚀 Run Period"): calculate_results(); st.rerun()

def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("Waiting..."); return
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
            ed = st.data_editor(df, hide_index=True, height=600)
            if st.button("Submit"): p['inputs']=ed['Value'].tolist(); p['status']='Submitted'; st.rerun()
    with tab2:
        if p['history']:
            last = p['history'][-1]
            st.write(f"**Period {last['Period']}**"); st.json(last['Income_Statement'])
        else: st.info("No Data")

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
