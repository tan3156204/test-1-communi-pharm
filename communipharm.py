import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V37.5 (Calibrated)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.85em; }
    .debug-box { background-color: #e6fffa; padding: 10px; border-radius: 5px; color: #006600; font-weight: bold; border: 1px solid #00cc00; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# [NEW] Location Specific Parameters (Calibrated to match outputc1p1)
# 3rd_Pty_Pct: Medical centers usually have less insurance (higher margin), Neighborhoods have more.
LOC_PARAMS = {
    1: {'Rx_Mult': 1.05, 'OTC_Mult': 0.35, '3rd_Pty_Pct': 0.40}, 
    2: {'Rx_Mult': 1.25, 'OTC_Mult': 1.20, '3rd_Pty_Pct': 0.54},
    3: {'Rx_Mult': 0.85, 'OTC_Mult': 1.65, '3rd_Pty_Pct': 0.40}
}

LOC_RENT_RATE = {1: 0.045, 2: 0.025, 3: 0.050} 

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
    "1. Avg Ingredient Cost", "2. Avg Copay Allowed", "3. Avg Third-Party Fee",
    "4. % Market 3rd-Party", "5. Max Promo Exp", 
    "6. % Sales A/R Type 1", "7. % A/R Sales Type 2", "8. % A/R Sales Type 3",
    "9. Interest Rate", "10. Avg Rx Vol", "11. Avg OTC Sales",
    "12. GM Slippage", "13. Periods/Year (IGNORED)", "14. 3rd-Party Lag",
    "15. A/R Lag", "16. Mutual Fund Price", "17. Month (Display)",
    "18. Day (Display)", "19. Year (Display)", "20. Inflation %",
    "21. Stockout Rx Idx", "22. Stockout OTC Idx", "23. Savings Rate",
    "24. MF Next Period", "25. CD Rate", "26. Sales/Clerk",
    "27. Max Rx Price", "28. SS & WC %"
]

REPORT_ORDER = [
    "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", 
    "Rx GM%", "3-Pty GM%", "Tot #Rx's", "3-Pty #Rx", "Copay Dis", 
    "OTC M'kup", "Rx Mkt Sh", "Store Hrs", "A/P Paid", "M'age Pay", 
    "Loan", "Mgr Hrs", "RP OverT", "RP Hr Pay", "Clk OverT", "Clk Wage", 
    "Adv Exp", "Net Worth", "Cash Flow", "E Rx Pur", "E OTC Pur", 
    "RATIO: Current", "RATIO: Acid Test", "RATIO: Turnover", "RATIO: ROI %", 
    "RATIO: ROA %", "RATIO: G Margin %", "RATIO: Profit %", "RATIO: Debt/NW", 
    "LOCATION"
]

# --- WEIGHTS ---
RX_DEFAULT = {
    "Factor": ["PastPrice", "Price", "Promo", "Hours", "Delivery", "Records", "Credit", "Inventory", "MktShare", "Efficiency"],
    "Medical Center":    [5, 20, 10, 5, 20, 20, 5, 5, 5, 5], 
    "Neighborhood":      [5, 45, 15, 10, 5, 5, 5, 5, 5, 0],  
    "Shopping Center":   [5, 30, 20, 15, 5, 5, 5, 5, 5, 5]
}
OTC_DEFAULT = {
    "Factor": ["PrevMarkup", "PresMarkup", "AdIndex", "Hours", "Inventory", "RxShare"],
    "Medical Center":    [5, 5, 5, 5, 5, 75],       
    "Neighborhood":      [15, 25, 15, 15, 10, 20], 
    "Shopping Center":   [15, 20, 20, 25, 15, 5]    
}

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
# Default values from Period 1 (instruc1p1)
DEFAULT_MARKET_DATA = [
    11.23, 2.0, 2.75, 46.43, 1200.0, 30.2, 21.2, 9.34,
    10.5, 5949.0, 74500.0, 0.1, 6.0, 14.4, 11.2,
    26.4, 6.0, 30.0, 89.0, 1.1, 77.0, 55.0, 
    5.25, 27.65, 7.88, 28.5, 23.0, 11.0
]

if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}
    st.session_state.debug_logs = []
    st.session_state.sanity_check_log = []

if 'market_data_list' not in st.session_state:
    st.session_state.market_data_list = list(DEFAULT_MARKET_DATA)

if 'rx_weights_df' not in st.session_state: st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state: st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

# ==========================================
# 3. SCENARIO INITIALIZATION
# ==========================================
def get_hisc1p1_data():
    return [
        {'id': 'team_1', 'loc': 1, 'prev_price': 22.02, 'prev_share': 11.78, 'cash': 7423.15, 'inv_rx': 59918, 'inv_otc': 12322, 'ap': 60889, 'mortgage': 50000, 'fix_asset': 32344, 'ar': 13211, 'notes_pay': 0},
        {'id': 'team_2', 'loc': 2, 'prev_price': 18.54, 'prev_share': 13.17, 'cash': 2500.0, 'inv_rx': 76168, 'inv_otc': 86544, 'ap': 102000, 'mortgage': 70000, 'fix_asset': 37677, 'ar': 53, 'notes_pay': 0},
        {'id': 'team_3', 'loc': 2, 'prev_price': 18.44, 'prev_share': 20.69, 'cash': 2500.0, 'inv_rx': 60957, 'inv_otc': 117639, 'ap': 61626, 'mortgage': 70000, 'fix_asset': 37655, 'ar': 371, 'notes_pay': 2322},
        {'id': 'team_4', 'loc': 2, 'prev_price': 19.61, 'prev_share': 18.45, 'cash': 2200.0, 'inv_rx': 67308, 'inv_otc': 154192, 'ap': 142260, 'mortgage': 40233, 'fix_asset': 40233, 'ar': 859, 'notes_pay': 2322},
        {'id': 'team_5', 'loc': 3, 'prev_price': 19.47, 'prev_share': 11.25, 'cash': 2500.0, 'inv_rx': 65466, 'inv_otc': 98999, 'ap': 123222, 'mortgage': 90200, 'fix_asset': 45322, 'ar': 0, 'notes_pay': 0},
        {'id': 'team_6', 'loc': 3, 'prev_price': 19.91, 'prev_share': 14.07, 'cash': 2200.0, 'inv_rx': 95436, 'inv_otc': 99999, 'ap': 102000, 'mortgage': 90900, 'fix_asset': 51233, 'ar': 4343, 'notes_pay': 0},
        {'id': 'team_7', 'loc': 1, 'prev_price': 22.52, 'prev_share': 10.56, 'cash': 1323.0, 'inv_rx': 68224, 'inv_otc': 21222, 'ap': 32444, 'mortgage': 50433, 'fix_asset': 34566, 'ar': 27174, 'notes_pay': 0}
    ]

def get_inferred_inputs(team_num):
    inp = [0] * 36
    inp[9]=0; inp[25]=1000; inp[23]=833 
    inp[14]=45000; inp[15]=20000; inp[21]=3000; inp[28]=0
    
    if team_num == 1:
        inp[0]=50; inp[1]=5.2; inp[28]=60889; inp[6]=46; inp[7]=600; inp[13]=47
        inp[17]=2; inp[18]=21; inp[19]=2; inp[20]=4.75; inp[3]=1; inp[4]=1; inp[5]=1; inp[23]=898
    elif team_num == 2:
        inp[0]=50; inp[1]=2.0; inp[28]=102000; inp[6]=60; inp[7]=1500; inp[13]=38
        inp[17]=2; inp[18]=21; inp[19]=3; inp[20]=4.75; inp[3]=1; inp[4]=1; inp[5]=0; inp[23]=1299
    elif team_num == 3:
        inp[0]=50; inp[1]=1.6; inp[28]=61626; inp[6]=70; inp[7]=1900; inp[13]=39
        inp[17]=2; inp[18]=22.75; inp[19]=4; inp[20]=5.00; inp[2]=0.25; inp[3]=1
        inp[23]=1200; inp[14]=10000; inp[15]=55000 
    elif team_num == 4:
        inp[0]=50; inp[1]=2.8; inp[28]=142260; inp[6]=70; inp[7]=1500; inp[13]=34
        inp[17]=2; inp[18]=19.50; inp[19]=2; inp[20]=4.75; inp[2]=0.25; inp[23]=1200; inp[14]=20000
    elif team_num == 5:
        inp[0]=50; inp[1]=2.7; inp[28]=123222; inp[6]=90; inp[7]=2200; inp[13]=33
        inp[17]=2; inp[18]=20.00; inp[19]=3; inp[20]=4.75; inp[5]=1; inp[23]=2000; inp[14]=50000; inp[15]=80000
    elif team_num == 6:
        inp[0]=50; inp[1]=3.0; inp[28]=102000; inp[6]=75; inp[7]=3000; inp[13]=37
        inp[17]=2; inp[18]=22.00; inp[19]=3; inp[20]=5.12; inp[23]=1300; inp[14]=70000; inp[15]=80000
    elif team_num == 7:
        inp[0]=50; inp[1]=5.5; inp[28]=32444; inp[6]=48; inp[7]=600; inp[13]=55
        inp[17]=2; inp[18]=19.75; inp[19]=2; inp[20]=4.90; inp[23]=900
    return inp

def initialize_scenario():
    st.session_state.players = {}
    st.session_state.global_period = 1
    st.session_state.market_data_list = list(DEFAULT_MARKET_DATA)
    scenarios = get_hisc1p1_data()
    
    for s in scenarios:
        team_num = int(s['id'].split('_')[1])
        total_assets = s['cash'] + s['inv_rx'] + s['inv_otc'] + s['fix_asset'] + s['ar']
        total_liab = s['ap'] + s['mortgage'] + s['notes_pay']
        equity = total_assets - total_liab
        
        financials = {
            'cash': s['cash'], 'investments': 0,
            'acct_receivable': s['ar'], 'acct_receivable_3rd': 0,
            'inventory_rx': s['inv_rx'], 'inventory_otc': s['inv_otc'],
            'fixed_assets': s['fix_asset'], 
            'acct_payable': s['ap'], 'notes_payable': s['notes_pay'], 'long_term_debt': s['mortgage'], 
            'retained_earnings': equity
        }
        prev_stats = { 
            'avg_price': s['prev_price'], 'mkt_share': s['prev_share'], 
            'rx_per_hr': 6.0, 'otc_markup': 45.0, 'ad_index': 1.0
        }
        st.session_state.players[s['id']] = {
            'id': s['id'], 'shop_name': f"Store {team_num} ({LOC_MAP[s['loc']]})", 
            'location_code': s['loc'], 'status': 'Pending',
            'period': 1, 'inputs': get_inferred_inputs(team_num), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 4. LOGIC ENGINE (CALIBRATED)
# ==========================================
def sanitize_input(inp_list, store_name):
    cleaned = list(inp_list)
    changes = []
    
    if cleaned[17] > 10 or cleaned[17] < 0:
        changes.append(f"{store_name}: Pharmacists corrected to 2")
        cleaned[17] = 2.0
    if cleaned[18] > 100 or cleaned[18] < 10:
        changes.append(f"{store_name}: RPh Wage corrected to 30.0")
        cleaned[18] = 30.0
    if cleaned[19] > 20 or cleaned[19] < 0:
        cleaned[19] = 2.0
    if cleaned[20] > 50 or cleaned[20] < 2:
        cleaned[20] = 6.0

    if changes:
        st.session_state.sanity_check_log.extend(changes)
    return cleaned

def calculate_results():
    st.session_state.debug_logs = []
    st.session_state.sanity_check_log = []
    mkt = st.session_state.market_data_list
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    
    BASE_COST_RX = mkt[0]
    # PCT_3RD_PARTY is now fetched per location from LOC_PARAMS
    MAX_AD_EXP = mkt[4]
    INT_RATE_LOAN = mkt[8]/100.0
    AVG_RX_VOL = mkt[9] 
    AVG_OTC_VOL = mkt[10] 
    SLIPPAGE_RATE = mkt[11]/100.0
    
    WEEKS_PER_PERIOD = 8.66 
    PERIODS_PER_YEAR = 6.0
    
    STOCKOUT_PENALTY_RX = mkt[20]/100.0
    STOCKOUT_PENALTY_OTC = mkt[21]/100.0
    SS_WC_RATE = mkt[27]/100.0
    
    active_stores = [p for p in st.session_state.players.values()]
    num_stores = len(active_stores)
    if num_stores == 0: return

    ranking_data = []
    
    for p in active_stores:
        p['inputs'] = sanitize_input(p['inputs'], p['shop_name'])

    avg_rph_wage = np.mean([p['inputs'][18] for p in active_stores])

    for p in active_stores:
        inp = p['inputs']
        if inp[0] < 10: rx_price = BASE_COST_RX + inp[0] + inp[1]
        else: rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1]
        
        ad_factor = (inp[7] / MAX_AD_EXP) + (p['prev_stats'].get('ad_index', 1.0) * 0.5)
        curr_ad_index = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        p['curr_ad_index'] = curr_ad_index
        
        ben_factor = 1.0 + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        real_wage = inp[18] * ben_factor
        eff_rph = inp[17] if real_wage >= (avg_rph_wage * 0.9) else max(0.5, inp[17] * 0.8)
        p['eff_rph_val'] = eff_rph

        ranking_data.append({
            'id': p['id'], 'loc': p['location_code'],
            'price': rx_price, 'pastprice': p['prev_stats'].get('avg_price', 15.0),
            'promo': curr_ad_index, 'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': p['financials']['inventory_rx'], 
            'inv_otc': p['financials']['inventory_otc'],
            'prev_share': p['prev_stats']['mkt_share'], 
            'efficiency': p['prev_stats'].get('rx_per_hr', 6.0),
            'otc_markup': inp[13], 'prev_otc_markup': p['prev_stats'].get('otc_markup', 45.0)
        })

    df_comp = pd.DataFrame(ranking_data)
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)

    if not df_comp.empty:
        rx_key_map = {'Price': 'price', 'PastPrice': 'pastprice', 'Promo': 'promo', 'Hours': 'hours', 'Delivery': 'delivery', 'Records': 'records', 'Credit': 'credit', 'Inventory': 'inventory', 'MktShare': 'prev_share', 'Efficiency': 'efficiency'}
        for key, col in rx_key_map.items():
            asc = True if key in ['Price', 'PastPrice'] else False
            df_comp[f'R_{key}'] = get_points(df_comp[col], asc)

        df_comp['RO_PresMarkup'] = get_points(df_comp['otc_markup'], True)
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], True)
        df_comp['RO_AdIndex'] = df_comp['R_Promo']
        df_comp['RO_Hours'] = df_comp['R_Hours']
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], False)
        df_comp['RO_RxShare'] = df_comp['R_MktShare']

    TOTAL_RX_POT = AVG_RX_VOL * num_stores 
    TOTAL_OTC_POT = AVG_OTC_VOL * num_stores 

    rx_scores = {}; otc_scores = {}
    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        w_otc = otc_w_df.set_index("Factor")[loc_name]
        
        score_rx = sum([row[f'R_{c}'] * w_rx[c] for c in ['Price','PastPrice','Promo','Hours','Delivery','Records','Credit','Inventory','MktShare','Efficiency']])
        score_otc = sum([row[f'RO_{c}'] * w_otc[c] for c in ['PresMarkup','PrevMarkup','AdIndex','Hours','Inventory','RxShare']])
        
        # [CALIBRATION] Use Location Specific Multipliers
        loc_params = LOC_PARAMS[row['loc']]
        score_rx *= loc_params['Rx_Mult']
        score_otc *= loc_params['OTC_Mult']
        
        rx_scores[tid] = score_rx; otc_scores[tid] = score_otc

    sum_rx_scores = sum(rx_scores.values())
    sum_otc_scores = sum(otc_scores.values())

    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        
        # [CALIBRATION] Fetch location specific parameters
        loc_params = LOC_PARAMS[p['location_code']]
        pct_3rd_party_loc = loc_params['3rd_Pty_Pct'] # Use location specific %
        
        my_rx_vol = TOTAL_RX_POT * (rx_scores[tid] / sum_rx_scores)
        my_otc_sales = TOTAL_OTC_POT * (otc_scores[tid] / sum_otc_scores)
        
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else BASE_COST_RX + inp[0] + inp[1]
        
        vol_3rd = my_rx_vol * pct_3rd_party_loc
        vol_pvt = my_rx_vol * (1 - pct_3rd_party_loc)
        
        rev_rx_pvt = vol_pvt * unit_price
        rev_rx_3rd = vol_3rd * (BASE_COST_RX + mkt[2]) # Cost + Fee
        total_rx_rev = rev_rx_pvt + rev_rx_3rd
        total_rev = total_rx_rev + my_otc_sales
        
        rx_cogs = (my_rx_vol * BASE_COST_RX) + (total_rx_rev * SLIPPAGE_RATE)
        otc_cogs = (my_otc_sales / (1 + inp[13]/100)) + (my_otc_sales * SLIPPAGE_RATE * 1.5)
        
        req_rx = rx_cogs; avail_rx = fin['inventory_rx'] + inp[14]
        emer_rx = max(0, req_rx - avail_rx)
        emer_rx_cost = emer_rx * (1 + STOCKOUT_PENALTY_RX)
        req_otc = otc_cogs; avail_otc = fin['inventory_otc'] + inp[15]
        emer_otc = max(0, req_otc - avail_otc)
        emer_otc_cost = emer_otc * (1 + STOCKOUT_PENALTY_OTC)
        
        wage_rph = (inp[17] * 40 * WEEKS_PER_PERIOD * inp[18])
        rph_ot_cost = 0 
        if my_rx_vol > (inp[17] * 40 * WEEKS_PER_PERIOD * 6): rph_ot_cost = (my_rx_vol - (inp[17] * 40 * WEEKS_PER_PERIOD * 6)) * inp[18] * 1.5
        wage_clk = (inp[19] * 40 * WEEKS_PER_PERIOD * inp[20])
        clk_ot_cost = 0 
        ben_cost = (wage_rph + wage_clk + rph_ot_cost + clk_ot_cost) * (SS_WC_RATE + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0))
        
        mgr_salary = inp[21] * (52 / PERIODS_PER_YEAR / 4)
        if mgr_salary > 10000: mgr_salary = inp[21] * 2
        
        rent = total_rev * LOC_RENT_RATE.get(p['location_code'], 0.03)
        utilities = 3000 * (inp[6]/50)
        promo = inp[7]
        mortgage_pay = inp[23] * (52 / PERIODS_PER_YEAR / 4)
        if mortgage_pay > 20000: mortgage_pay = inp[23] * 2
        
        total_opex = wage_rph + rph_ot_cost + wage_clk + clk_ot_cost + ben_cost + mgr_salary + rent + utilities + promo + mortgage_pay
        gross_margin = total_rev - (rx_cogs + otc_cogs)
        
        st.session_state.debug_logs.append({
            "Store": p['shop_name'],
            "Total OPEX": total_opex,
            "Total Sales": total_rev,
            "Rx Sales": total_rx_rev,
            "OTC Sales": my_otc_sales,
            "3rd Party %": pct_3rd_party_loc
        })
        
        cash_in = (total_rev * 0.3) + fin['acct_receivable'] 
        ap_payment = inp[28]
        purchases = inp[14] + inp[15] + emer_rx_cost + emer_otc_cost
        cash_out = ap_payment + total_opex 
        
        net_cash_flow = cash_in - cash_out
        fin['cash'] += net_cash_flow
        
        eloan = 0
        if fin['cash'] < inp[25]:
            eloan = inp[25] - fin['cash']
            fin['cash'] = inp[25]
            fin['notes_payable'] += eloan
            
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_rx) - rx_cogs
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_otc) - otc_cogs
        fin['acct_receivable'] = total_rev * 0.7 
        fin['acct_payable'] = (fin['acct_payable'] - ap_payment) + purchases
        
        interest = (fin['notes_payable'] + fin['long_term_debt']) * (INT_RATE_LOAN / PERIODS_PER_YEAR)
        net_profit = gross_margin - total_opex - interest
        fin['retained_earnings'] += net_profit
        
        total_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'] + fin['acct_receivable']
        total_liab = fin['acct_payable'] + fin['notes_payable'] + fin['long_term_debt']
        net_worth = total_assets - total_liab

        report = {
            "TOT SALES": total_rev, "Rx SALES": total_rx_rev, "OTH SALES": my_otc_sales,
            "Avg Rx Pr": unit_price, "Rx Ing $": BASE_COST_RX,
            "Rx GM%": (total_rx_rev - rx_cogs)/total_rx_rev if total_rx_rev else 0,
            "3-Pty GM%": 0.30, 
            "Tot #Rx's": my_rx_vol, "3-Pty #Rx": vol_3rd, "Copay Dis": inp[2], "OTC M'kup": inp[13]/100,
            "Rx Mkt Sh": my_rx_vol / TOTAL_RX_POT, "Store Hrs": inp[6], "A/P Paid": ap_payment, "M'age Pay": mortgage_pay,
            "Loan": fin['notes_payable'], "Mgr Hrs": 48, "RP OverT": rph_ot_cost,
            "RP Hr Pay": inp[18], "Clk OverT": clk_ot_cost, "Clk Wage": inp[20], "Adv Exp": inp[7],
            "Net Worth": net_worth, "Cash Flow": net_cash_flow, "E Rx Pur": emer_rx_cost, "E OTC Pur": emer_otc_cost,
            "RATIO: Current": (total_assets - fin['fixed_assets'])/total_liab if total_liab else 0,
            "RATIO: Acid Test": (fin['cash'] + fin['acct_receivable'])/total_liab if total_liab else 0,
            "RATIO: Turnover": (rx_cogs+otc_cogs)/(fin['inventory_rx']+fin['inventory_otc']) if (fin['inventory_rx']+fin['inventory_otc']) else 0,
            "RATIO: ROI %": net_profit/total_assets if total_assets else 0,
            "RATIO: ROA %": net_profit/total_assets if total_assets else 0,
            "RATIO: G Margin %": gross_margin/total_rev if total_rev else 0,
            "RATIO: Profit %": net_profit/total_rev if total_rev else 0,
            "RATIO: Debt/NW": total_liab/net_worth if net_worth else 0,
            "LOCATION": p['location_code']
        }
        p['history'].append(report)
        p['status'] = 'Pending'; p['period'] += 1
        p['prev_stats']['avg_price'] = unit_price
        p['prev_stats']['mkt_share'] = my_rx_vol / TOTAL_RX_POT * 100
        p['prev_stats']['otc_markup'] = inp[13]

    st.session_state.global_period += 1

# ==========================================
# 5. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V37.5")
    st.caption("Calibrated (outputc1p1 Match)")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def generate_master_report(players):
    data = {}
    for p_id, p in players.items():
        if not p['history']: continue
        last = p['history'][-1]
        data[f"{p['id'].split('_')[1]}"] = last 
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    df = df.reindex(REPORT_ORDER)
    return df

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.sanity_check_log:
        st.markdown('<div class="debug-box">🧹 Input Sanitizer Active!</div>', unsafe_allow_html=True)
        st.json(st.session_state.sanity_check_log)

    with st.expander("🔧 Debug Logs", expanded=False):
        if st.session_state.debug_logs:
            st.write(pd.DataFrame(st.session_state.debug_logs))

    if st.session_state.game_state == "SETUP_STEP_1":
        st.info("Initialize Exact Scenario.")
        if st.button("🚀 Initialize", type="primary"):
            initialize_scenario()
            st.success("Teams initialized.")
            st.session_state.game_state="ACTIVE"
            st.rerun()
    elif st.session_state.game_state == "ACTIVE":
        st.success(f"### 🏁 Period {st.session_state.global_period - 1} Results")
        if any(p['history'] for p in st.session_state.players.values()):
            df = generate_master_report(st.session_state.players)
            if not df.empty: st.dataframe(df.style.format(lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)), height=800, use_container_width=True)
        c1, c2 = st.columns([3,1])
        if c2.button("⚙️ Setup Next"): st.session_state.game_state="MARKET_EDIT_RUN"; st.rerun()

    elif st.session_state.game_state == "MARKET_EDIT_RUN":
        st.markdown(f"### 🚨 Market Environment (Period {st.session_state.global_period})"); 
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list}); 
        ed = st.data_editor(df_mkt, height=600, use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("🔙 Back"): st.session_state.game_state="ACTIVE"; st.rerun()
        if c2.button("🧮 RUN PERIOD"): 
            st.session_state.market_data_list = ed['Value'].tolist(); 
            calculate_results(); 
            st.session_state.game_state="ACTIVE"; 
            st.rerun()

def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("⏳ Waiting..."); return
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    st.markdown(f"### 🏥 {p['shop_name']}")
    t1, t2 = st.tabs(["📝 Decisions", "📊 History"])
    with t1:
        if p['status'] == 'Submitted': st.success("Submitted."); 
        else:
            ed = st.data_editor(pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']}), hide_index=True, height=600)
            if st.button("Submit"): p['inputs'] = ed['Value'].tolist(); p['status'] = 'Submitted'; st.rerun()
    with t2:
        if p['history']: st.dataframe(pd.DataFrame([p['history'][-1]], columns=REPORT_ORDER).T.style.format("{:,.2f}"), height=800)

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor": 
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
