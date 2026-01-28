import streamlit as st
import pandas as pd
import numpy as np
import math

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V36.14 (Hardcoded Data)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.9em; }
    .metric-header { font-weight: bold; background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.025}

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

# --- WEIGHTS (Tuned for Store 3 & 5) ---
RX_DEFAULT = {
    "Factor": ["PastPrice", "Price", "Promo", "Hours", "Delivery", "Records", "Credit", "Inventory", "MktShare", "Efficiency"],
    "Medical Center":    [5, 20, 11, 7, 10, 15, 3, 10, 15, 6], 
    "Neighborhood":      [5, 45, 13, 11, 6, 8, 2, 11, 10, 6],  
    "Shopping Center":   [5, 20, 15, 12, 1, 1, 1, 10, 5, 10]
}
OTC_DEFAULT = {
    "Factor": ["PrevMarkup", "PresMarkup", "AdIndex", "Hours", "Inventory", "RxShare"],
    "Medical Center":    [2, 4, 4, 2, 3, 5],
    "Neighborhood":      [15, 15, 10, 15, 10, 15], 
    "Shopping Center":   [20, 20, 10, 15, 20, 15]    
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
        11.23, 2.0, 2.90, 25.0, 1500.0, 30.0, 20.0, 10.0,
        2.5, 6000.0, 48000.0, 2.0, 4.0, 15.0, 30.0,
        10.0, 1.0, 1.0, 2024.0, 3.0, 50.0, 50.0, 
        2.0, 10.5, 5.0, 120.0, 100.0, 15.0
    ]

if 'rx_weights_df' not in st.session_state: st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state: st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

# ==========================================
# 3. HELPER FUNCTIONS (HARDCODED DATA)
# ==========================================

def get_static_scenario_data():
    """Returns the EXACT data from Hisc1p1.xlsx - Sheet1.csv provided by user."""
    # Data structure: List of dicts representing each store
    # Calculated Equity = (Cash + Inv + Fix + AR + OtherAssets) - (AP + Loan + Mortgage)
    
    data = [
        # Store 1
        {
            'id': 'team_1', 'loc': 1, 'prev_price': 22.01529, 'prev_share': 11.78,
            'cash': 7423.156, 'inv_rx': 59918.04, 'inv_otc': 12322.0, 'notes_pay': 0.0, 'mortgage': 50000.0,
            'ap': 60889.39, 'fix_asset': 32344.0, 'ar': 13211.0, 'ar_3rd': 14322.0,
            'investments': 10000.0 + 121.0 + 6000.0 # CD + Savings + MutualFund
        },
        # Store 2
        {
            'id': 'team_2', 'loc': 2, 'prev_price': 18.04057, 'prev_share': 13.17,
            'cash': 2500.0, 'inv_rx': 76168.09, 'inv_otc': 86544.0, 'notes_pay': 0.0, 'mortgage': 70000.0,
            'ap': 102000.0, 'fix_asset': 37677.0, 'ar': 53.76, 'ar_3rd': 26186.79,
            'investments': 0.0 + 3232.0 + 0.0
        },
        # Store 3
        {
            'id': 'team_3', 'loc': 2, 'prev_price': 18.04057, 'prev_share': 20.69,
            'cash': 2500.0, 'inv_rx': 60957.88, 'inv_otc': 117639.2, 'notes_pay': 2322.0, 'mortgage': 70000.0,
            'ap': 61626.0, 'fix_asset': 37655.0, 'ar': 371.952, 'ar_3rd': 23233.0,
            'investments': 10000.0 + 0.0 + 9000.0
        },
        # Store 4
        {
            'id': 'team_4', 'loc': 2, 'prev_price': 19.46354, 'prev_share': 18.45,
            'cash': 2200.0, 'inv_rx': 67308.29, 'inv_otc': 154192.0, 'notes_pay': 2322.0, 'mortgage': 70000.0,
            'ap': 142260.2, 'fix_asset': 40233.0, 'ar': 859.152, 'ar_3rd': 23433.0,
            'investments': 0.0 + 4523.14 + 6000.0
        },
        # Store 5
        {
            'id': 'team_5', 'loc': 3, 'prev_price': 19.27427, 'prev_share': 11.25,
            'cash': 2500.0, 'inv_rx': 65466.0, 'inv_otc': 98999.0, 'notes_pay': 0.0, 'mortgage': 90200.0,
            'ap': 123222.0, 'fix_asset': 45322.0, 'ar': 0.0, 'ar_3rd': 12322.0,
            'investments': 0.0 + 2232.0 + 0.0
        },
        # Store 6
        {
            'id': 'team_6', 'loc': 3, 'prev_price': 19.10998, 'prev_share': 14.07,
            'cash': 2200.0, 'inv_rx': 95436.2, 'inv_otc': 99999.0, 'notes_pay': 0.0, 'mortgage': 90900.0,
            'ap': 102000.0, 'fix_asset': 51233.0, 'ar': 4343.0, 'ar_3rd': 22323.0,
            'investments': 30000.0 + 2122.0 + 0.0
        },
        # Store 7
        {
            'id': 'team_7', 'loc': 1, 'prev_price': 22.01529, 'prev_share': 10.56,
            'cash': 1323.0, 'inv_rx': 68224.16, 'inv_otc': 21222.0, 'notes_pay': 0.0, 'mortgage': 50433.0,
            'ap': 32444.0, 'fix_asset': 34566.0, 'ar': 27174.01, 'ar_3rd': 12344.0,
            'investments': 10000.0 + 2333.0 + 0.0
        }
    ]
    return data

def get_starting_inputs():
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 1.0, 25.0, 1.0, 10.0, 3000.0, 30.0, 40.0, 60.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_hardcoded_scenario():
    """Initializes the 7 teams using the hardcoded clean data"""
    st.session_state.players = {}
    st.session_state.global_period = 1
    
    scenarios = get_static_scenario_data()
    
    for s in scenarios:
        # Calculate Equity to Balance Sheet
        total_assets = s['cash'] + s['inv_rx'] + s['inv_otc'] + s['fix_asset'] + s['ar'] + s['ar_3rd'] + s['investments']
        total_liab = s['ap'] + s['notes_pay'] + s['mortgage']
        equity = total_assets - total_liab # Retained Earnings
        
        financials = {
            'cash': s['cash'], 
            'investments': s['investments'],
            'acct_receivable': s['ar'], 
            'acct_receivable_3rd': s['ar_3rd'],
            'inventory_rx': s['inv_rx'], 
            'inventory_otc': s['inv_otc'],
            'fixed_assets': s['fix_asset'], 
            'acct_payable': s['ap'],
            'notes_payable': s['notes_pay'], 
            'long_term_debt': s['mortgage'], 
            'retained_earnings': equity
        }
        
        prev_stats = { 
            'avg_price': s['prev_price'], 
            'mkt_share': s['prev_share'], 
            'rx_per_hr': 6.0, 
            'otc_markup': 45.0, 
            'ad_index': 1.0, 
            'cogs_rx': s['inv_rx'] * 0.8, 
            'avg_inv_rx': s['inv_rx'],
            'cogs_otc': s['inv_otc'] * 0.8, 
            'avg_inv_otc': s['inv_otc']
        }
        
        team_id = s['id']
        st.session_state.players[team_id] = {
            'id': team_id, 
            'shop_name': f"Store {team_id.split('_')[1]} ({LOC_MAP[s['loc']]})", 
            'location_code': s['loc'],
            'status': 'Pending',
            'period': 1, 
            'inputs': get_starting_inputs(), 
            'financials': financials,
            'prev_stats': prev_stats, 
            'history': [] 
        }

def initialize_teams_manual(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        inv_rx = 55000.0; inv_otc = 25000.0; fix_asset = 50000.0
        cash = 15000.0; ar = 55000.0; invest = 2000.0
        total_assets = cash + invest + ar + inv_rx + inv_otc + fix_asset
        equity = total_assets * 0.4; liab = total_assets - equity
        financials = {
            'cash': cash, 'investments': invest, 'acct_receivable': ar * 0.8, 'acct_receivable_3rd': ar * 0.2,
            'inventory_rx': inv_rx, 'inventory_otc': inv_otc, 'fixed_assets': fix_asset, 
            'acct_payable': liab * 0.4, 'notes_payable': 0.0, 'long_term_debt': liab * 0.6, 'retained_earnings': equity 
        }
        prev_stats = { 
            'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 'rx_per_hr': 5.0, 'otc_markup': 45.0,
            'ad_index': 1.0, 'cogs_rx': 40000.0, 'avg_inv_rx': 50000.0, 'cogs_otc': 20000.0, 'avg_inv_otc': 25000.0
        }
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 4. LOGIC ENGINE
# ==========================================
def generate_master_report(players):
    data = []
    mkt = st.session_state.market_data_list
    base_rx_cost = mkt[0]
    for p_id, p in players.items():
        if not p['history']: continue
        last = p['history'][-1]; inp = p['inputs']; fin = p['financials']
        tot_sales = last['total_rev']; rx_sales = last['rev_rx']; oth_sales = last['rev_otc']
        rx_vol_est = rx_sales / last['avg_price'] if last['avg_price'] > 0 else 0
        rx_ing_cost = (last['cogs_rx'] / rx_vol_est) if rx_vol_est > 0 else base_rx_cost
        rx_gm_pct = ((rx_sales - last['cogs_rx']) / rx_sales * 100) if rx_sales > 0 else 0
        
        total_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'] + fin['acct_receivable']
        total_liab = fin['acct_payable'] + fin['notes_payable'] + fin['long_term_debt']
        net_worth = total_assets - total_liab
        curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        current_ratio = (curr_assets / curr_liab) if curr_liab > 0 else 0
        turnover = (last['total_cogs'] / (fin['inventory_rx'] + fin['inventory_otc'])) if (fin['inventory_rx'] + fin['inventory_otc']) > 0 else 0
        roi = (last['net_profit'] / total_assets * 100) if total_assets > 0 else 0

        row = {
            "Store": p['shop_name'], "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": oth_sales,
            "Avg Rx Pr": last['avg_price'], "Rx Ing $": rx_ing_cost, "Rx GM%": rx_gm_pct,
            "Net Worth": net_worth, "Cash Flow": last['cf_end'] - last['cf_start'],
            "RATIO: Current": current_ratio, "RATIO: Turnover": turnover, "RATIO: ROI %": roi,
            "RATIO: Profit %": last['kpi_np_pct'], "LOCATION": LOC_MAP[p['location_code']]
        }
        data.append(row)
    return pd.DataFrame(data).set_index("Store").T if data else pd.DataFrame()

def calculate_results():
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    mkt = st.session_state.market_data_list
    
    BASE_COST_RX = mkt[0]; MAX_AD_EXP = mkt[4]
    INT_RATE_LOAN = mkt[8]/100.0; AVG_RX_VOL = mkt[9]; AVG_OTC_VOL = mkt[10]
    SLIPPAGE_RATE = mkt[11]/100.0; WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    LAG_AR = mkt[14]/100.0; INFLATION = mkt[19]/100.0
    RX_PURCH_INDEX = mkt[20]/100.0; OTC_PURCH_INDEX = mkt[21]/100.0
    CD_RATE = mkt[24]/100.0; BENEFIT_PCT = mkt[27]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    active_stores = [p for p in store_list if p['location_code'] != 0]
    num_stores = len(active_stores)
    if num_stores == 0: return

    FIXED_RENT_RATE = {k: v * (1 + INFLATION) for k, v in LOC_RENT_RATE.items()}
    total_rph_wage = sum([p['inputs'][18] for p in active_stores])
    avg_rph_wage = total_rph_wage / num_stores if num_stores else 25.0

    for p in active_stores:
        inp = p['inputs']; fin = p['financials']
        fin['inventory_rx'] = max(0, fin['inventory_rx'] - inp[26])
        fin['inventory_otc'] = max(0, fin['inventory_otc'] - inp[27])
        fin['cash'] += (inp[26] * 0.8) + (inp[27] * 0.8)
        
        ben_cost_factor = 1 + BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        my_rph_real_wage = inp[18] * ben_cost_factor
        p['eff_rph'] = max(0, inp[17] - 1.0) if my_rph_real_wage < (0.9 * avg_rph_wage) else inp[17]
        p['eff_clk'] = inp[19]

    # --- RANKING ---
    ranking_data = []
    hmo_bids = [(p['id'], p['inputs'][35]) for p in active_stores if p['inputs'][35] > 0]
    hmo_winners = []
    if hmo_bids:
        hmo_bids.sort(key=lambda x: x[1])
        min_bid = hmo_bids[0][1]
        hmo_winners = [x[0] for x in hmo_bids if x[1] == min_bid]

    for p in active_stores:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']
        rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        ad_factor = (inp[7] / MAX_AD_EXP) + (prev.get('ad_index', 1.0) * 0.533)
        p['curr_ad_index'] = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        
        ranking_data.append({
            'id': tid, 'loc': p['location_code'],
            'price': rx_price, 'past_price': prev.get('avg_price', 15.0),
            'promo': p['curr_ad_index'], 'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': fin['inventory_rx'], 'inv_otc': fin['inventory_otc'],
            'prev_share': prev['mkt_share'], 'efficiency': prev.get('rx_per_hr', 5.0),
            'otc_markup': inp[13], 'prev_otc_markup': prev.get('otc_markup', 45.0)
        })
    
    df_comp = pd.DataFrame(ranking_data)
    
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)
        
    rx_shares = {}; otc_shares = {}
    if not df_comp.empty:
        cols = ['Price', 'PastPrice', 'Promo', 'Hours', 'Delivery', 'Records', 'Credit', 'Inventory', 'Share', 'Eff']
        asc = [True, True, False, False, False, False, False, False, False, False]
        for c, a in zip(cols, asc):
            df_comp[f'R_{c}'] = get_points(df_comp[c.lower().replace('share', 'prev_share').replace('eff', 'efficiency')] if c!='Share' else df_comp['prev_share'], a)

        df_comp['RO_Markup'] = get_points(df_comp['otc_markup'], True)
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], True)
        df_comp['RO_Promo'] = df_comp['R_Promo']; df_comp['RO_Hours'] = df_comp['R_Hours']
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], False)
        df_comp['RO_RxShare'] = df_comp['R_Share']

    total_rx_score = 0; total_otc_score = 0
    rx_scores = {}; otc_scores = {}
    avg_mkt_price = df_comp['price'].mean() if not df_comp.empty else 20.0

    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        score_rx = (row['R_Price'] * w_rx['Price']) + (row['R_PastPrice'] * w_rx['PastPrice']) + \
                   (row['R_Promo'] * w_rx['Promo']) + (row['R_Hours'] * w_rx['Hours']) + \
                   (row['R_Delivery'] * w_rx['Delivery']) + (row['R_Records'] * w_rx['Records']) + \
                   (row['R_Credit'] * w_rx['Credit']) + (row['R_Inventory'] * w_rx['Inventory']) + \
                   (row['R_Share'] * w_rx['MktShare']) + (row['R_Eff'] * w_rx['Efficiency'])
        
        if row['price'] < 19.00: score_rx *= 1.35
        elif row['price'] < avg_mkt_price: score_rx *= 1.05
        if loc_name == "Medical Center": score_rx *= 0.80
        if st.session_state.players[tid]['inputs'][33]: score_rx *= 1.05
        rx_scores[tid] = score_rx; total_rx_score += score_rx

        w_otc = otc_w_df.set_index("Factor")[loc_name]
        score_otc = (row['RO_Markup'] * w_otc['PresMarkup']) + (row['RO_PrevMarkup'] * w_otc['PrevMarkup']) + \
                    (row['RO_Promo'] * w_otc['AdIndex']) + (row['RO_Hours'] * w_otc['Hours']) + \
                    (row['RO_Inventory'] * w_otc['Inventory']) + (row['RO_RxShare'] * w_otc['RxShare'])
        otc_scores[tid] = score_otc; total_otc_score += score_otc

    for tid in active_stores:
        tid_str = tid['id']
        rx_shares[tid_str] = rx_scores[tid_str] / total_rx_score if total_rx_score > 0 else 1.0/num_stores
        otc_shares[tid_str] = otc_scores[tid_str] / total_otc_score if total_otc_score > 0 else 1.0/num_stores

    total_rx_mkt = (AVG_RX_VOL * num_stores) * 1.05 
    total_otc_mkt = (AVG_OTC_VOL * num_stores) * 1.05
    
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']; prev = p['prev_stats']
        my_rx_share = rx_shares.get(tid, 0); my_otc_share = otc_shares.get(tid, 0)
        
        base_rx_vol = total_rx_mkt * my_rx_share
        hmo_vol = (200 / len(hmo_winners)) if tid in hmo_winners else 0
        
        if LOC_MAP[p['location_code']] == "Shopping Center":
            base_rx_vol *= 0.70 
            total_otc_sales = (total_otc_mkt * my_otc_share) * 2.2 
        else:
            total_otc_sales = (total_otc_mkt * my_otc_share)

        total_rx_vol = base_rx_vol + hmo_vol
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        rev_rx_normal = base_rx_vol * unit_price
        rev_rx_hmo = hmo_vol * inp[35]
        total_rx_sales = rev_rx_normal + rev_rx_hmo
        total_sales = total_rx_sales + total_otc_sales
        
        cogs_rx_total = total_rx_vol * BASE_COST_RX
        cogs_otc_total = total_otc_sales / (1 + inp[13]/100)
        
        req_inv_rx = cogs_rx_total * (1 + RX_PURCH_INDEX)
        avail_inv_rx = fin['inventory_rx'] + inp[14]
        emer_purch_rx = max(0, req_inv_rx - avail_inv_rx)
        req_inv_otc = cogs_otc_total * (1 + OTC_PURCH_INDEX)
        avail_inv_otc = fin['inventory_otc'] + inp[15]
        emer_purch_otc = max(0, req_inv_otc - avail_inv_otc)
        
        mgr_control_factor = 1.0 + (inp[21]/100.0)
        actual_slippage = total_sales * SLIPPAGE_RATE * mgr_control_factor
        cogs_rx_total += (actual_slippage * 0.5); cogs_otc_total += (actual_slippage * 0.5)

        std_rate = 10.0 if inp[4] else 12.5
        capacity_rx = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD) * std_rate
        rph_ot_hours = max(0, (total_rx_vol - capacity_rx) / std_rate)
        
        wage_rph = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD * inp[18]) + (rph_ot_hours * inp[18] * 1.5)
        wage_clk = (p['eff_clk'] * 40 * WEEKS_PER_PERIOD * inp[20])
        total_wages = wage_rph + wage_clk
        ben_cost = total_wages * (BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0))
        
        rent = total_sales * FIXED_RENT_RATE.get(p['location_code'], 0.03)
        bad_debt = (total_sales * 0.01) + inp[29]
        utilities = 3000 * (1 + INFLATION)
        promo = inp[7]; mgr_salary = inp[21] * 3; mortgage = inp[23]
        
        total_opex = total_wages + ben_cost + rent + utilities + promo + mgr_salary + bad_debt + mortgage
        gm = total_sales - (cogs_rx_total + cogs_otc_total)
        
        intr_st = fin['notes_payable'] * INT_RATE_LOAN
        intr_lt = fin['long_term_debt'] * (INT_RATE_LOAN * 0.5) 
        intr_exp = intr_st + intr_lt
        intr_inc = (fin['investments'] * CD_RATE)
        
        net_profit = gm - total_opex - intr_exp + intr_inc
        
        cash_start = fin['cash']
        inflow_sales = (total_sales * 0.8) 
        inflow_ar = fin['acct_receivable'] * (1 - LAG_AR)
        total_cash_in = inflow_sales + inflow_ar + inp[30] + intr_inc
        
        total_cash_out = inp[28] + total_wages + ben_cost + mgr_salary + rent + promo + utilities + emer_purch_rx + emer_purch_otc + mortgage + intr_exp
        fin['cash'] = cash_start + total_cash_in - total_cash_out
        
        e_loan = 0
        if fin['cash'] < inp[25]:
            e_loan = inp[25] - fin['cash']
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan

        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_purch_rx) - cogs_rx_total
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_purch_otc) - cogs_otc_total
        fin['acct_payable'] = (fin['acct_payable'] - inp[28]) + inp[14] + inp[15]
        
        new_ar = total_sales * 0.2
        fin['acct_receivable'] = (fin['acct_receivable'] * LAG_AR) + new_ar
        fin['retained_earnings'] += net_profit
        
        p['prev_stats'].update({
            'avg_price': unit_price, 'mkt_share': my_rx_share * 100,
            'otc_markup': inp[13], 'rx_per_hr': total_rx_vol / (p['eff_rph']*40*WEEKS_PER_PERIOD) if p['eff_rph'] else 0
        })
        
        metrics = {
            "rev_rx": total_rx_sales, "rev_otc": total_otc_sales, "total_rev": total_sales,
            "cogs_rx": cogs_rx_total, "cogs_otc": cogs_otc_total, "total_cogs": cogs_rx_total + cogs_otc_total,
            "gross_margin": gm, "net_profit": net_profit,
            "bs_cash": fin['cash'], "bs_ar": fin['acct_receivable'] + fin['acct_receivable_3rd'],
            "bs_inv_rx": fin['inventory_rx'], "bs_inv_otc": fin['inventory_otc'],
            "bs_invest": fin['investments'], "bs_fixed": fin['fixed_assets'],
            "bs_ap": fin['acct_payable'], "bs_notes": fin['notes_payable'], 
            "bs_lt_debt": fin['long_term_debt'], "bs_equity": fin['retained_earnings'],
            "cf_start": cash_start, "cf_in": total_cash_in, "cf_out": total_cash_out, "cf_eloan": e_loan, "cf_end": fin['cash'],
            "kpi_gm_pct": (gm/total_sales*100) if total_sales else 0,
            "kpi_payroll_pct": ((total_wages+ben_cost+mgr_salary)/total_sales*100) if total_sales else 0,
            "kpi_rent_pct": (rent/total_sales*100) if total_sales else 0,
            "kpi_np_pct": (net_profit/total_sales*100) if total_sales else 0,
            "avg_price": unit_price, "Rx Mkt Sh": my_rx_share * 100, "LOCATION": LOC_MAP[p['location_code']]
        }
        p['history'].append(metrics)
        p['status'] = 'Pending'; p['period'] += 1
    st.session_state.global_period += 1

# ==========================================
# 5. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V36.14")
    st.caption("Hardcoded Clean Data")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown("### Step 1: Initialize Teams")
        # Direct initialization button without file upload
        if st.button("🚀 Initialize Teams (Auto-Data)", type="primary"):
            initialize_hardcoded_scenario()
            st.success("Teams initialized with correct financial data.")
            st.session_state.game_state="SETUP_STEP_2"
            st.rerun()

    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown("### Step 2: Check Configuration"); st.write("Ready."); 
        if st.button("Start Game"): st.session_state.game_state="ACTIVE"; st.rerun()
    
    elif st.session_state.game_state == "ACTIVE":
        st.success(f"### 🏁 Period {st.session_state.global_period - 1} Results")
        if any(p['history'] for p in st.session_state.players.values()):
            df = generate_master_report(st.session_state.players)
            if not df.empty: st.dataframe(df.style.format(lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)), height=600, use_container_width=True)
        st.divider(); c1, c2 = st.columns([3,1]); c1.metric("Ready", f"{sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')}/{len(st.session_state.players)}")
        if c2.button("⚙️ Setup Next"): st.session_state.game_state="MARKET_EDIT_RUN"; st.rerun()

    elif st.session_state.game_state == "MARKET_EDIT_RUN":
        st.markdown("### 🚨 Market Environment"); df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list}); ed = st.data_editor(df_mkt, height=600, use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("🔙 Back"): st.session_state.game_state="ACTIVE"; st.rerun()
        if c2.button("🧮 RUN"): st.session_state.market_data_list = ed['Value'].tolist(); calculate_results(); st.session_state.game_state="ACTIVE"; st.rerun()

def render_student_ui():
    if st.session_state.game_state not in ["ACTIVE", "MARKET_EDIT_RUN"]: st.warning("⏳ Waiting..."); return
    t_ids = list(st.session_state.players.keys()); sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name']); p = st.session_state.players[sel_id]
    if p['period'] == 1 and p['status'] == 'Pending' and not p['history']:
        if p['location_code'] == 0:
            n = st.text_input("Name", p['shop_name']); l = st.selectbox("Loc", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
            if st.button("Start") and l!=0: p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        else: st.success(f"Welcome {p['shop_name']}"); 
        if st.button("Enter"): p['status']='Thinking'; st.rerun()
        return
    st.markdown(f"### 🏥 {p['shop_name']} (Period {p['period']})")
    t1, t2 = st.tabs(["📝 Decisions", "📊 Reports"])
    with t1:
        if p['status'] == 'Submitted': st.success("Submitted."); 
        if st.button("Edit"): p['status']='Thinking'; st.rerun()
        else:
            ed = st.data_editor(pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']}), hide_index=True, height=500)
            if st.button("Submit", type="primary"): p['inputs'] = ed['Value'].tolist(); p['status'] = 'Submitted'; st.rerun()
    with t2:
        if not p['history']: st.info("No reports."); return
        last = p['history'][-1]
        t_a, t_b, t_c, t_d = st.tabs(["Income", "Balance", "Cash", "KPI"])
        with t_a: st.markdown(f"**Rev**: ${last['total_rev']:,.0f} | **COGS**: ${last['total_cogs']:,.0f} | **GM**: ${last['gross_margin']:,.0f} | **Net**: ${last['net_profit']:,.0f}")
        with t_b: st.markdown(f"**Assets**: ${last['bs_cash']+last['bs_inv_rx']+last['bs_inv_otc']+last['bs_fixed']:,.0f} | **Liab**: ${last['bs_ap']+last['bs_notes']+last['bs_lt_debt']:,.0f} | **Eq**: ${last['bs_equity']:,.0f}")
        with t_c: st.markdown(f"Start: ${last['cf_start']:,.0f} -> End: ${last['cf_end']:,.0f}")
        with t_d: c1,c2,c3=st.columns(3); c1.metric("GM%", f"{last['kpi_gm_pct']:.1f}%"); c2.metric("NP%", f"{last['kpi_np_pct']:.1f}%"); c3.metric("Rent%", f"{last['kpi_rent_pct']:.1f}%")

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor": 
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
