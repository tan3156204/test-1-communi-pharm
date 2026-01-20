import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V31 (True Ranking Engine)", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .fin-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dotted #eee; }
    .fin-label { font-weight: 500; color: #444; }
    .fin-value { font-family: 'Courier New', monospace; font-weight: bold; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white;}
    .badge-pending { background-color: #9e9e9e; }
    .badge-submitted { background-color: #4caf50; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# Inputs Mapped exactly to 1-36
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

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.025}

# Weights Configuration (Table 2 form Guide)
# Structure: [Wt_Med, Wt_Neigh, Wt_Shop]
RX_WEIGHTS_CONFIG = {
    "Price_Past": [10, 22, 25],     # Lower is better
    "Price_Pres": [5, 5, 10],     # Lower is better
    "Advertising Index":      [11, 13, 15],      # Higher is better
    "Hours":      [7, 11, 12],      # Higher is better
    "Delivery":   [10, 6, 1],       # Higher is better
    "Patient Records":    [15, 8, 1],       # Higher is better
    "Credit":     [3, 2, 1],        # Higher is better
    "Inventory":  [10, 11, 10],        # Lower Ratio is better
    "MktShare":   [23, 16, 5],        # Higher is better
    "Rxs Per HOur": [6, 16, 10]         # Higher is better
}

OTC_WEIGHTS_CONFIG = {
    "Markup_Past": [2, 15, 20],    # Lower is better
    "Markup_Pres": [4, 15, 20],    # Lower is better
    "Ad_Index":    [4, 10, 10],    # Higher is better
    "Hours":       [2, 15, 15],    # Higher is better
    "Inventory":   [3, 10, 20],    # Lower Ratio is better
    "RxShare":     [5, 15, 15]      # Higher is better
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

# Instructor Data (Market Parameters)
if 'inst_data' not in st.session_state:
    st.session_state.inst_data = {
        'rx_cost': 11.23, 'const_fee': 2.90, 'int_rate': 0.025, 
        'rx_market': 6000, 'otc_mult': 8.0, 
        'ben_life': 0.05, 'ben_health': 0.15, 'wage_std_pharm': 25.0, 'wage_std_clerk': 6.0,
        'emer_rate': 400.0, 'ad_limit': 1000.0 # Max Allowable Ad
    }

def get_starting_inputs():
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 1.0, 25.0, 1.0, 10.0, 1500.0, 30.0, 40.0, 60.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_teams(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        # Initial Financials
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0, 'retained_earnings': 138000.0
        }
        # Initial Stats for Ranking
        prev_stats = { 
            'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 
            'ad_index': 1.0, 'rx_per_hr': 5.0, 'otc_markup': 45.0,
            'cogs_rx': 35000.0, 'avg_inv_rx': 50000.0, # For Inv Level Calc
            'cogs_otc': 15000.0, 'avg_inv_otc': 20000.0
        }
        
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 3. HELPER FUNCTIONS (LOGIC)
# ==========================================
def calculate_ad_index(current_ad, max_ad, past_index):
    # Logic: Hyperbolic function
    # Ad Factor = (Current / Max) + (Past * 0.533)
    # Limit Factor <= 2.0
    # Index = (0.84 * Factor) - (0.16 * Factor^2)
    
    ad_factor = (current_ad / max_ad) + (past_index * 0.533)
    ad_factor = min(ad_factor, 2.0)
    
    new_index = (0.84 * ad_factor) - (0.16 * (ad_factor ** 2))
    return max(0, new_index) # Cannot be negative

def calculate_inv_level(past_cogs, past_avg_inv):
    # Logic: Past COGS / Past Avg Inventory
    # Lower is better (High Turnover)
    if past_avg_inv == 0: return 10.0 # Bad score
    return past_cogs / past_avg_inv

# ==========================================
# 4. MAIN SIMULATION ENGINE
# ==========================================
def calculate_results():
    store_list = [p for p in st.session_state.players.values()]
    I = st.session_state.inst_data
    num_stores = len(store_list)
    
    # --- PHASE 1: DATA PREPARATION & CALCULATIONS ---
    # We need to collect raw values for all stores to rank them
    
    ranking_data = []
    
    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']; fin = p['financials']
        
        # 1. Price Calculation
        # Assume Input[0] > 10 is Markup%, else Fee$
        if inp[0] > 10: calc_price = I['rx_cost'] * (1 + inp[0]/100)
        else: calc_price = I['rx_cost'] + inp[0]
        pres_price = max(calc_price, 5.0) + I['const_fee'] # Safety Floor
        
        # 2. Ad Index
        # Input[7] is Promo $, Input[9] is % Promo allocated to Rx
        rx_ad_spend = inp[7] * (inp[8]/100)
        otc_ad_spend = inp[7] * (1 - inp[8]/100)
        
        new_rx_ad_idx = calculate_ad_index(rx_ad_spend, I['ad_limit'], prev.get('ad_index', 1.0))
        # Assuming similar logic for OTC Ad Index or simplified
        new_otc_ad_idx = calculate_ad_index(otc_ad_spend, I['ad_limit'], prev.get('ad_index', 1.0)) # Reuse prev for simplicity
        
        # 3. Inventory Level (Depth)
        rx_inv_level = calculate_inv_level(prev.get('cogs_rx', 1), prev.get('avg_inv_rx', 1))
        otc_inv_level = calculate_inv_level(prev.get('cogs_otc', 1), prev.get('avg_inv_otc', 1))
        
        # 4. Service Score (Sum of binaries)
        service_score = inp[3] + inp[4] + inp[5] # Delivery + Records + Credit
        
        ranking_data.append({
            'id': tid,
            'loc_idx': p['location_code'] - 1, # 0,1,2 for array indexing
            # Rx Factors
            'Price_Past': prev['avg_price'],
            'Price_Pres': pres_price,
            'Promo': new_rx_ad_idx,
            'Hours': inp[6],
            'Delivery': inp[3],
            'Records': inp[4],
            'Credit': inp[5],
            'Inventory': rx_inv_level,
            'MktShare': prev['mkt_share'],
            'Efficiency': prev.get('rx_per_hr', 5.0),
            # OTC Factors
            'Markup_Past': prev.get('otc_markup', 45.0),
            'Markup_Pres': inp[13],
            'Ad_Index_OTC': new_otc_ad_idx,
            'Inv_OTC': otc_inv_level,
            'RxShare_Pres': 0 # To be filled after Rx calc
        })
    
    df = pd.DataFrame(ranking_data)
    
    # --- PHASE 2: RANKING & WEIGHTING (THE ENGINE) ---
    
    # Helper to calculate points based on rank
    # Rank 1 (Best) gets Num_Stores points. Rank N (Worst) gets 1 point.
    def calc_points(series, ascending_is_better):
        # rank(method='min') gives 1 for best.
        # If ascending=True (Smallest is best, e.g. Price), Rank 1 is smallest.
        # If ascending=False (Largest is best, e.g. Ad), Rank 1 is largest.
        ranks = series.rank(method='min', ascending=ascending_is_better)
        # Convert Rank 1 to Max Points
        # Points = Total + 1 - Rank
        return (num_stores + 1) - ranks

    # 1. Rx Scoring
    # Define which variables are Ascending (Lower is Better) vs Descending (Higher is Better)
    # Ascending (True): Price, Inventory Level
    # Descending (False): Promo, Hours, Services, Share, Efficiency
    
    rx_scores = pd.Series(0.0, index=df.index)
    
    # Loop through factors and apply weights
    factors_map = [
        ('Price_Past', True), ('Price_Pres', True), ('Promo', False), 
        ('Hours', False), ('Delivery', False), ('Records', False), 
        ('Credit', False), ('Inventory', True), ('MktShare', False), 
        ('Efficiency', False)
    ]
    
    keys = list(RX_WEIGHTS_CONFIG.keys()) # Ensure order matches map
    
    for idx, (col, asc) in enumerate(factors_map):
        points = calc_points(df[col], asc)
        
        # Apply Weight based on Location
        # We need to apply row-by-row because locations differ
        key = keys[idx]
        weights = df['loc_idx'].apply(lambda x: RX_WEIGHTS_CONFIG[key][x if x>=0 else 0])
        
        rx_scores += points * weights
        
    # 2. Rx Market Share Calculation
    total_rx_score = rx_scores.sum()
    df['Rx_Share_Pct'] = rx_scores / total_rx_score
    
    # 3. OTC Scoring
    # Fill dependency
    df['RxShare_Pres'] = df['Rx_Share_Pct'] * 100
    
    otc_scores = pd.Series(0.0, index=df.index)
    otc_map = [
        ('Markup_Past', True), ('Markup_Pres', True), ('Ad_Index_OTC', False),
        ('Hours', False), ('Inv_OTC', True), ('RxShare_Pres', False)
    ]
    otc_keys = list(OTC_WEIGHTS_CONFIG.keys())
    
    for idx, (col, asc) in enumerate(otc_map):
        points = calc_points(df[col], asc)
        key = otc_keys[idx]
        weights = df['loc_idx'].apply(lambda x: OTC_WEIGHTS_CONFIG[key][x if x>=0 else 0])
        otc_scores += points * weights
        
    total_otc_score = otc_scores.sum()
    df['OTC_Share_Pct'] = otc_scores / total_otc_score
    
    # Map back to dict for easy access
    rx_share_map = df.set_index('id')['Rx_Share_Pct'].to_dict()
    otc_share_map = df.set_index('id')['OTC_Share_Pct'].to_dict()
    
    # --- PHASE 3: FINANCIALS ---
    
    # HMO Logic
    hmo_bids = {p['id']: p['inputs'][35] for p in store_list if p['inputs'][35] > 0}
    hmo_winner_id = min(hmo_bids, key=hmo_bids.get) if hmo_bids else None
    
    for p in store_list:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        
        # Shares
        rx_share = rx_share_map[tid]
        otc_share = otc_share_map[tid]
        
        if tid == hmo_winner_id: rx_share *= 1.15 # Bonus
        
        # Sales
        rx_count = I['rx_market'] * num_stores * rx_share
        
        # Price (Re-calc for revenue)
        if inp[0] > 10: p_price = I['rx_cost'] * (1 + inp[0]/100)
        else: p_price = I['rx_cost'] + inp[0]
        p_price = max(p_price, 5.0) + I['const_fee']
        
        rx_sales = rx_count * p_price
        otc_sales = (I['rx_market'] * num_stores * 8.0) * otc_share * (I['otc_mult']/8.0)
        tot_sales = rx_sales + otc_sales
        
        # COGS
        cost_rx = rx_sales / (p_price/I['rx_cost'])
        cost_otc = otc_sales * 0.65
        gross_margin = tot_sales - (cost_rx + cost_otc)
        
        # Staffing (The 90% Rule + OT)
        hrs_open = inp[6]
        
        # Pharm
        pharm_fte = inp[16]
        if inp[17] < (I['wage_std_pharm'] * 0.9): pharm_fte = max(0, pharm_fte - 1)
        avail_pharm = (pharm_fte * 40 * 13) + (inp[22]/100 * inp[22] * 13)
        req_pharm = rx_count / 10.0
        p_ot = max(0, req_pharm - avail_pharm)
        
        # Clerk
        clerk_fte = inp[18]
        if inp[19] < (I['wage_std_clerk'] * 0.9): clerk_fte = max(0, clerk_fte - 1)
        avail_clerk = clerk_fte * 40 * 13
        req_clerk = tot_sales / 25.30
        c_ot = max(0, req_clerk - avail_clerk)
        
        # Wages
        w_pharm = (avail_pharm * inp[17]) + (p_ot * I['emer_rate'] * 1.5)
        w_clerk = (avail_clerk * inp[19]) + (c_ot * inp[19] * 1.5)
        
        # Benefits
        ben = 0
        if inp[32]==1: ben += (w_pharm+w_clerk) * I['ben_life']
        if inp[33]==1: ben += (w_pharm+w_clerk) * I['ben_health']
        
        # Opex
        rent = tot_sales * LOC_RENT_RATE.get(p['location_code'], 0.03)
        expenses = w_pharm + w_clerk + ben + rent + inp[7] + inp[20] + inp[23] + 3000
        
        depr = fin['fixed_assets']*0.02
        bad = inp[29]
        interest = (fin['long_term_debt'] + fin['notes_payable']) * I['int_rate']
        
        total_opex = expenses + depr + interest + bad
        net_profit = gross_margin - total_opex + (fin['investments']*0.015)
        
        # Cash Flow
        fin['investments'] += (inp[9]-inp[11])
        fin['inventory_rx'] = max(0, fin['inventory_rx'] + inp[14] - cost_rx)
        fin['inventory_otc'] = max(0, fin['inventory_otc'] + inp[15] - cost_otc)
        
        cash_ops = tot_sales - (expenses + interest)
        fin['cash'] += (cash_ops - inp[28] - inp[9] - inp[30])
        
        fin['acct_payable'] += (inp[14]+inp[15]-inp[28])
        fin['long_term_debt'] -= inp[30]
        
        e_loan = 0
        penalty = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
            penalty = e_loan * 0.20
            net_profit -= penalty; fin['retained_earnings'] -= penalty
            total_opex += penalty
            
        fin['retained_earnings'] += net_profit
        
        # Update Prev Stats for next round
        p['prev_stats'] = {
            'avg_price': p_price, 'mkt_share': rx_share*100,
            'ad_index': df[df['id']==tid]['Promo'].values[0],
            'rx_per_hr': rx_count/((hrs_open*13)+1), 'otc_markup': inp[13],
            'cogs_rx': cost_rx, 'avg_inv_rx': (fin['inventory_rx']+inp[14])/2,
            'cogs_otc': cost_otc, 'avg_inv_otc': (fin['inventory_otc']+inp[15])/2
        }
        
        # History
        curr_asst = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        def safe(n,d): return n/d if d!=0 else 0
        
        p['history'].append({
            "Period": st.session_state.global_period,
            # Instructor Metrics
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Avg Rx Pr": p_price, "Rx Ing $": I['rx_cost'], 
            "Rx GM%": safe(rx_sales-cost_rx, rx_sales)*100, 
            "Tot #Rx's": rx_count, "Rx Mkt Sh": rx_share*100,
            "Store Hrs": hrs_open, "RP OverT": p_ot, "Clk OverT": c_ot,
            "RP Hr Pay": I['emer_rate'] if p_ot>0 else inp[17],
            "Net Worth": fin['retained_earnings'], "Cash Flow": cash_ops,
            # Ratios
            "Current": safe(curr_asst, curr_liab), "ROI": safe(net_profit, fin['retained_earnings'])*100,
            "G Margin": safe(gross_margin, tot_sales)*100, "Profit": safe(net_profit, tot_sales)*100,
            "LOCATION": LOC_MAP[p['location_code']],
            
            # Reports
            "HMO Winner": (tid == hmo_winner_id),
            "Income_Statement": {
                "Sales": {"Total": tot_sales, "Rx": rx_sales, "Other": otc_sales},
                "COGS": {"Total": cost_rx+cost_otc},
                "Gross Margin": gross_margin,
                "Expenses": {"Total": expenses, "Penalty": penalty},
                "Net Profit": net_profit
            },
            "Balance_Sheet": {
                "Assets": {"Total": curr_asst + fin['fixed_assets'], "Cash": fin['cash']},
                "Liabilities": {"Total": curr_liab + fin['long_term_debt']},
                "Equity": fin['retained_earnings']
            }
        })
        p['status'] = 'Pending'
    
    st.session_state.global_period += 1

# ==========================================
# 5. UI ROUTER
# ==========================================
with st.sidebar:
    st.title("💊 COMMUNI-PHARM")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown('<div class="step-header">Step 1: Create Teams</div>', unsafe_allow_html=True)
        n = st.number_input("Number of Teams", 1, 20, 5)
        if st.button("Next ➡️"): initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()
        
    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown('<div class="step-header">Step 2: Market Environment</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.inst_data['rx_cost'] = st.number_input("Rx Base Cost ($)", value=11.23)
            st.session_state.inst_data['rx_market'] = st.number_input("Rx Market (Units)", value=6000)
            st.session_state.inst_data['ad_limit'] = st.number_input("Ad Limit ($)", value=1000.0)
        with c2:
            st.session_state.inst_data['wage_std_pharm'] = st.number_input("Std Pharm Wage", value=25.0)
            st.session_state.inst_data['emer_rate'] = st.number_input("Emergency Rate", value=400.0)
            
        if st.button("Next ➡️"): st.session_state.game_state="SETUP_STEP_3"; st.rerun()
        
    elif st.session_state.game_state == "SETUP_STEP_3":
        st.markdown('<div class="step-header">Step 3: Weights</div>', unsafe_allow_html=True)
        # Placeholder for weight editing
        st.info("Weights Loaded (Default Table 2)")
        if st.button("Start Game"): st.session_state.game_state="ACTIVE"; st.rerun()
        
    elif st.session_state.game_state == "ACTIVE":
        st.write(f"### City Summary - Period {st.session_state.global_period-1}")
        # Summary Table Logic (Same as V30)
        if any(p['history'] for p in st.session_state.players.values()):
            metrics = ["TOT SALES", "Rx SALES", "Rx GM%", "Rx Mkt Sh", "Net Worth", "ROI", "RP OverT", "LOCATION"]
            data = {p['shop_name']: [p['history'][-1].get(m, 0) for m in metrics] for p in st.session_state.players.values() if p['history']}
            st.table(pd.DataFrame(data, index=metrics))
            
        if st.button("🚀 Run Period"): calculate_results(); st.rerun()

def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("Waiting..."); return
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    if p['period'] == 1 and p['status'] == 'Pending':
        c1, c2 = st.columns(2)
        n = c1.text_input("Name", p['shop_name'])
        l = c2.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
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
            st.write(f"**Period {last['Period']} Report**")
            st.json(last['Income_Statement'])
        else: st.info("No Data")

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor": 
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
