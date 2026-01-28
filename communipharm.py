import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V36.4 (History Match)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
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

# --- WEIGHTS ---
RX_DEFAULT = {
    "Factor": ["PastPrice", "Price", "Promo", "Hours", "Delivery", "Records", "Credit", "Inventory", "MktShare", "Efficiency"],
    "Medical Center":    [5, 25, 10, 5, 15, 15, 5, 5, 10, 5], 
    "Neighborhood":      [5, 35, 15, 10, 5, 5, 5, 10, 5, 5],  
    "Shopping Center":   [5, 20, 20, 15, 2, 2, 5, 10, 10, 11]
}
OTC_DEFAULT = {
    "Factor": ["PrevMarkup", "PresMarkup", "AdIndex", "Hours", "Inventory", "RxShare"],
    "Medical Center":    [2, 5, 3, 2, 3, 5],
    "Neighborhood":      [15, 15, 15, 15, 10, 10], 
    "Shopping Center":   [15, 15, 15, 20, 15, 10]    
}

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

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
DEFAULT_MKT_DATA = [
    11.23, 2.0, 2.90, 40.0, 3000.0, 30.0, 20.0, 10.0,
    2.5, 6000.0, 85000.0, 2.0, 4.0, 15.0, 30.0,
    10.0, 1.0, 1.0, 2024.0, 3.0, 20.0, 20.0, 
    2.0, 10.5, 5.0, 120.0, 100.0, 15.0
]

if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

if 'market_data_list' not in st.session_state or len(st.session_state.market_data_list) != len(DEFAULT_MKT_DATA):
    st.session_state.market_data_list = list(DEFAULT_MKT_DATA)

if 'rx_weights_df' not in st.session_state: st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state: st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

# ==========================================
# 3. INITIALIZATION WITH HISTORICAL INPUTS
# ==========================================
def get_static_scenario_data():
    return [
        {'id': 'team_1', 'loc': 1, 'prev_price': 22.02, 'prev_share': 11.78, 'cash': 7423.15, 'inv_rx': 59918, 'inv_otc': 12322, 'ap': 60889, 'mortgage': 50000, 'fix_asset': 32344, 'ar': 13211},
        {'id': 'team_2', 'loc': 2, 'prev_price': 18.54, 'prev_share': 13.17, 'cash': 2500.0, 'inv_rx': 76168, 'inv_otc': 86544, 'ap': 102000, 'mortgage': 70000, 'fix_asset': 37677, 'ar': 53},
        {'id': 'team_3', 'loc': 2, 'prev_price': 18.44, 'prev_share': 20.69, 'cash': 2500.0, 'inv_rx': 60957, 'inv_otc': 117639, 'ap': 61626, 'mortgage': 70000, 'fix_asset': 37655, 'ar': 371},
        {'id': 'team_4', 'loc': 2, 'prev_price': 19.61, 'prev_share': 18.45, 'cash': 2200.0, 'inv_rx': 67308, 'inv_otc': 154192, 'ap': 142260, 'mortgage': 70000, 'fix_asset': 40233, 'ar': 859},
        {'id': 'team_5', 'loc': 3, 'prev_price': 19.47, 'prev_share': 11.25, 'cash': 2500.0, 'inv_rx': 65466, 'inv_otc': 98999, 'ap': 123222, 'mortgage': 90200, 'fix_asset': 45322, 'ar': 0},
        {'id': 'team_6', 'loc': 3, 'prev_price': 19.91, 'prev_share': 14.07, 'cash': 2200.0, 'inv_rx': 95436, 'inv_otc': 99999, 'ap': 102000, 'mortgage': 90900, 'fix_asset': 51233, 'ar': 4343},
        {'id': 'team_7', 'loc': 1, 'prev_price': 22.52, 'prev_share': 10.56, 'cash': 1323.0, 'inv_rx': 68224, 'inv_otc': 21222, 'ap': 32444, 'mortgage': 50433, 'fix_asset': 34566, 'ar': 27174}
    ]

def get_calibrated_inputs(team_num):
    """Returns exact inputs from outputc1p1.txt"""
    inp = [0] * 36
    
    # Common
    inp[9] = 0; inp[25] = 1000 # Min Cash
    inp[23] = 833 # Est Mortgage
    
    if team_num == 1:
        # Puts input 28 (Pay A/P) to 60889 as per history
        inp[0] = 50; inp[1] = 5.2; inp[2] = 0; inp[3] = 1; inp[4] = 1; inp[5] = 1 
        inp[6] = 46; inp[7] = 600; inp[13] = 47; inp[17] = 2; inp[18] = 21.00 
        inp[19] = 2; inp[20] = 4.75; inp[28] = 60889; inp[23] = 898 
        inp[14]=45000; inp[15]=10000; inp[21]=3000
        
    elif team_num == 2:
        inp[0] = 50; inp[1] = 2.0; inp[3] = 1; inp[4] = 1; inp[5] = 0
        inp[6] = 60; inp[7] = 1500; inp[13] = 38; inp[17] = 2; inp[18] = 21.00
        inp[19] = 3; inp[20] = 4.75; inp[28] = 102000; inp[23] = 1299
        inp[14]=60000; inp[15]=60000; inp[21]=3000
        
    elif team_num == 3:
        inp[0] = 50; inp[1] = 1.6; inp[2] = 0.25; inp[6] = 70; inp[7] = 1900
        inp[13] = 39; inp[17] = 2; inp[18] = 22.75; inp[19] = 4; inp[20] = 5.00
        inp[28] = 61626; inp[23] = 1200; inp[14] = 10000; inp[15] = 70000; inp[21]=3000

    elif team_num == 4:
        inp[0] = 50; inp[1] = 2.8; inp[2] = 0.25; inp[6] = 70; inp[7] = 1500
        inp[13] = 34; inp[18] = 19.50; inp[20] = 4.75; inp[28] = 142260
        inp[23] = 1200; inp[14] = 20000; inp[15] = 80000; inp[21]=3000

    elif team_num == 5:
        # High Hours (90), Low Price -> High OTC
        inp[0] = 50; inp[1] = 2.7; inp[6] = 90; inp[7] = 2200; inp[13] = 33
        inp[18] = 20.00; inp[20] = 4.75; inp[28] = 123222; inp[23] = 2000
        inp[14] = 50000; inp[15] = 80000; inp[21]=3000

    elif team_num == 6:
        inp[0] = 50; inp[1] = 3.0; inp[6] = 75; inp[7] = 3000; inp[13] = 37
        inp[18] = 22.00; inp[20] = 5.12; inp[28] = 102000; inp[23] = 1300
        inp[14] = 70000; inp[15] = 80000; inp[21]=3000

    elif team_num == 7:
        inp[0] = 50; inp[1] = 5.5; inp[6] = 48; inp[7] = 600; inp[13] = 55
        inp[18] = 19.75; inp[20] = 4.90; inp[28] = 32444; inp[23] = 900
        inp[14] = 60000; inp[15] = 15000; inp[21]=3000

    return inp

def initialize_hardcoded_scenario():
    st.session_state.players = {}
    st.session_state.global_period = 1
    scenarios = get_static_scenario_data()
    
    for s in scenarios:
        team_num = int(s['id'].split('_')[1])
        total_assets = s['cash'] + s['inv_rx'] + s['inv_otc'] + s['fix_asset'] + s['ar']
        total_liab = s['ap'] + s['mortgage']
        equity = total_assets - total_liab 
        
        financials = {
            'cash': s['cash'], 'investments': 0,
            'acct_receivable': s['ar'], 'acct_receivable_3rd': 0,
            'inventory_rx': s['inv_rx'], 'inventory_otc': s['inv_otc'],
            'fixed_assets': s['fix_asset'], 
            'acct_payable': s['ap'], 'notes_payable': 0, 'long_term_debt': s['mortgage'], 
            'retained_earnings': equity
        }
        prev_stats = { 
            'avg_price': s['prev_price'], 'mkt_share': s['prev_share'], 
            'rx_per_hr': 6.0, 'otc_markup': 45.0, 'ad_index': 1.0
        }
        
        st.session_state.players[s['id']] = {
            'id': s['id'], 'shop_name': f"Store {team_num} ({LOC_MAP[s['loc']]})", 
            'location_code': s['loc'], 'status': 'Pending',
            'period': 1, 'inputs': get_calibrated_inputs(team_num), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 4. LOGIC ENGINE
# ==========================================
def calculate_results():
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    mkt = st.session_state.market_data_list
    
    BASE_COST_RX = mkt[0]; PCT_3RD_PARTY = mkt[3] / 100.0
    MAX_AD_EXP = mkt[4]; INT_RATE_LOAN = mkt[8]/100.0
    AVG_RX_VOL = mkt[9]; AVG_OTC_VOL = mkt[10]
    SLIPPAGE_RATE = mkt[11]/100.0
    periods_per_year = max(0.1, mkt[12])
    WEEKS_PER_PERIOD = min(52, 52 / periods_per_year)
    LAG_AR = mkt[14]/100.0; INFLATION = mkt[19]/100.0
    STOCKOUT_PENALTY_RX = mkt[20]/100.0; STOCKOUT_PENALTY_OTC = mkt[21]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    active_stores = [p for p in store_list if p['location_code'] != 0]
    num_stores = len(active_stores)
    if num_stores == 0: return

    FIXED_RENT_RATE = {k: v * (1 + INFLATION) for k, v in LOC_RENT_RATE.items()}
    total_rph_wage = sum([p['inputs'][18] for p in active_stores])
    avg_rph_wage = total_rph_wage / num_stores if num_stores else 25.0

    ranking_data = []
    for p in active_stores:
        inp = p['inputs']; fin = p['financials']
        if inp[0] < 10: rx_price = BASE_COST_RX + inp[0] + inp[1]
        else: rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1]
            
        ad_factor = (inp[7] / MAX_AD_EXP) + (p['prev_stats'].get('ad_index', 1.0) * 0.5)
        curr_ad_index = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        p['curr_ad_index'] = curr_ad_index

        ben_factor = 1.0 + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        real_wage = inp[18] * ben_factor
        eff_rph = inp[17] if real_wage >= (0.9 * avg_rph_wage) else max(0.5, inp[17] * 0.8)
        p['eff_rph_val'] = eff_rph

        ranking_data.append({
            'id': p['id'], 'loc': p['location_code'],
            'price': rx_price, 'pastprice': p['prev_stats'].get('avg_price', 15.0),
            'promo': curr_ad_index, 'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': fin['inventory_rx'], 'inv_otc': fin['inventory_otc'],
            'prev_share': p['prev_stats']['mkt_share'], 
            'efficiency': p['prev_stats'].get('rx_per_hr', 6.0),
            'otc_markup': inp[13], 'prev_otc_markup': p['prev_stats'].get('otc_markup', 45.0)
        })

    df_comp = pd.DataFrame(ranking_data)
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)

    if not df_comp.empty:
        rx_key_map = {'Price': 'price', 'PastPrice': 'pastprice', 'Promo': 'promo', 'Hours': 'hours', 'Delivery': 'delivery', 'Records': 'records', 'Credit': 'credit', 'Inventory': 'inventory', 'MktShare': 'prev_share', 'Efficiency': 'efficiency'}
        rx_asc_map = {'Price': True, 'PastPrice': True} 
        for key, col_name in rx_key_map.items():
            asc = rx_asc_map.get(key, False)
            df_comp[f'R_{key}'] = get_points(df_comp[col_name], asc)

        df_comp['RO_PresMarkup'] = get_points(df_comp['otc_markup'], True)
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], True)
        df_comp['RO_AdIndex'] = df_comp['R_Promo']
        df_comp['RO_Hours'] = df_comp['R_Hours']
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], False)
        df_comp['RO_RxShare'] = df_comp['R_MktShare']

    rx_scores = {}; otc_scores = {}
    total_rx_score = 0; total_otc_score = 0
    avg_mkt_price = df_comp['price'].mean()

    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        score_rx = sum([row[f'R_{c}'] * w_rx[c] for c in ['Price','PastPrice','Promo','Hours','Delivery','Records','Credit','Inventory','MktShare','Efficiency']])
        if row['price'] > avg_mkt_price * 1.05: score_rx *= 0.8
        if row['price'] < avg_mkt_price * 0.95: score_rx *= 1.2
        rx_scores[tid] = score_rx; total_rx_score += score_rx

        w_otc = otc_w_df.set_index("Factor")[loc_name]
        score_otc = sum([row[f'RO_{c}'] * w_otc[c] for c in ['PresMarkup','PrevMarkup','AdIndex','Hours','Inventory','RxShare']])
        otc_scores[tid] = score_otc; total_otc_score += score_otc

    total_rx_mkt_vol = AVG_RX_VOL * num_stores
    total_otc_mkt_vol = AVG_OTC_VOL * num_stores

    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        my_rx_share_raw = rx_scores[tid] / total_rx_score
        my_otc_share_raw = otc_scores[tid] / total_otc_score
        loc_type = LOC_MAP[p['location_code']]
        
        base_rx_vol = total_rx_mkt_vol * my_rx_share_raw
        if loc_type == "Medical Center": base_rx_vol *= 1.15
        elif loc_type == "Shopping Center": base_rx_vol *= 0.85
        
        base_otc_sales = total_otc_mkt_vol * my_otc_share_raw
        if loc_type == "Shopping Center": base_otc_sales *= 1.35
        elif loc_type == "Medical Center": base_otc_sales *= 0.15
        
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else BASE_COST_RX + inp[0] + inp[1]
        
        vol_3rd = base_rx_vol * PCT_3RD_PARTY
        vol_pvt = base_rx_vol * (1 - PCT_3RD_PARTY)
        
        rev_rx_pvt = vol_pvt * unit_price
        rev_rx_3rd = vol_3rd * (BASE_COST_RX + mkt[2])
        total_rx_rev = rev_rx_pvt + rev_rx_3rd
        total_otc_rev = base_otc_sales
        total_rev = total_rx_rev + total_otc_rev
        
        rx_cogs_base = base_rx_vol * BASE_COST_RX
        rx_slippage = total_rx_rev * SLIPPAGE_RATE
        rx_cogs_total = rx_cogs_base + rx_slippage
        
        otc_cogs_base = total_otc_rev / (1 + inp[13]/100)
        otc_slippage = total_otc_rev * SLIPPAGE_RATE * 1.2
        otc_cogs_total = otc_cogs_base + otc_slippage
        
        req_rx = rx_cogs_total; avail_rx = fin['inventory_rx'] + inp[14]
        emer_rx = max(0, req_rx - avail_rx)
        emer_rx_cost = emer_rx * (1 + STOCKOUT_PENALTY_RX)
        req_otc = otc_cogs_total; avail_otc = fin['inventory_otc'] + inp[15]
        emer_otc = max(0, req_otc - avail_otc)
        emer_otc_cost = emer_otc * (1 + STOCKOUT_PENALTY_OTC)

        actual_cogs_rx = rx_cogs_total; actual_cogs_otc = otc_cogs_total
        
        wage_rph = (inp[17] * 40 * WEEKS_PER_PERIOD * inp[18])
        rph_ot_cost = 0 
        if base_rx_vol > (inp[17] * 40 * 13 * 6): rph_ot_cost = (base_rx_vol - (inp[17] * 240 * 13)) * inp[18] * 1.5
        wage_clk = (inp[19] * 40 * WEEKS_PER_PERIOD * inp[20])
        clk_ot_cost = 0 
        total_wages = wage_rph + rph_ot_cost + wage_clk + clk_ot_cost
        
        mgr_salary = inp[21] * (52/12)
        rent = total_rev * LOC_RENT_RATE.get(p['location_code'], 0.03)
        utilities = 3000 * (inp[6]/50) 
        promo = inp[7]
        mortgage_pay = inp[23] * 12 
        if mortgage_pay < 1000: mortgage_pay *= 3 
        
        other_exp = total_rev * 0.02 
        total_opex = total_wages + mgr_salary + rent + utilities + promo + mortgage_pay + other_exp
        gross_margin = total_rev - (actual_cogs_rx + actual_cogs_otc)
        
        cash_start = fin['cash']
        cash_sales = total_rev * 0.35
        ar_collection = fin['acct_receivable'] 
        cash_in = cash_sales + ar_collection
        
        ap_payment = inp[28] 
        purchases = inp[14] + inp[15] + emer_rx_cost + emer_otc_cost
        
        # Accounting Fix: Only AP Payment + Opex goes out. Purchases go to AP.
        cash_out = ap_payment + total_opex 
        
        net_cash_flow = cash_in - cash_out
        fin['cash'] += net_cash_flow
        
        eloan = 0
        min_cash_req = inp[25]
        if fin['cash'] < min_cash_req:
            eloan = min_cash_req - fin['cash']
            fin['cash'] = min_cash_req 
            fin['notes_payable'] += eloan 
        
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_rx) - actual_cogs_rx
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_otc) - actual_cogs_otc
        
        new_ar = total_rev * 0.65
        fin['acct_receivable'] = new_ar
        
        # AP Logic: Start AP - Payment + New Purchases
        fin['acct_payable'] = (fin['acct_payable'] - ap_payment) + purchases
        
        interest_exp = (fin['notes_payable'] + fin['long_term_debt']) * (INT_RATE_LOAN / 4)
        net_profit = gross_margin - total_opex - interest_exp
        fin['retained_earnings'] += net_profit
        
        total_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'] + fin['acct_receivable']
        total_liab = fin['acct_payable'] + fin['notes_payable'] + fin['long_term_debt']
        net_worth = total_assets - total_liab

        report = {
            "TOT SALES": total_rev, "Rx SALES": total_rx_rev, "OTH SALES": total_otc_rev,
            "Avg Rx Pr": unit_price, "Rx Ing $": BASE_COST_RX,
            "Rx GM%": ((total_rx_rev - actual_cogs_rx)/total_rx_rev) if total_rx_rev else 0,
            "3-Pty GM%": 0.30, 
            "Tot #Rx's": base_rx_vol, "3-Pty #Rx": vol_3rd, "Copay Dis": inp[2], "OTC M'kup": inp[13]/100,
            "Rx Mkt Sh": my_rx_share_raw, "Store Hrs": inp[6], "A/P Paid": inp[28], "M'age Pay": inp[23],
            "Loan": fin['notes_payable'], "Mgr Hrs": 48, "RP OverT": rph_ot_cost,
            "RP Hr Pay": inp[18], "Clk OverT": clk_ot_cost, "Clk Wage": inp[20], "Adv Exp": inp[7],
            "Net Worth": net_worth, "Cash Flow": net_cash_flow, "E Rx Pur": emer_rx_cost, "E OTC Pur": emer_otc_cost,
            "RATIO: Current": (total_assets - fin['fixed_assets']) / total_liab if total_liab else 0,
            "RATIO: Acid Test": (fin['cash'] + fin['acct_receivable']) / total_liab if total_liab else 0,
            "RATIO: Turnover": (actual_cogs_rx+actual_cogs_otc)/(fin['inventory_rx']+fin['inventory_otc']) if (fin['inventory_rx']+fin['inventory_otc']) else 0,
            "RATIO: ROI %": (net_profit / net_worth) if net_worth else 0,
            "RATIO: ROA %": (net_profit / total_assets) if total_assets else 0,
            "RATIO: G Margin %": (gross_margin / total_rev) if total_rev else 0,
            "RATIO: Profit %": (net_profit / total_rev) if total_rev else 0,
            "RATIO: Debt/NW": (total_liab / net_worth) if net_worth else 0,
            "LOCATION": p['location_code']
        }
        p['history'].append(report)
        p['status'] = 'Pending'; p['period'] += 1
        p['prev_stats']['avg_price'] = unit_price
        p['prev_stats']['mkt_share'] = my_rx_share_raw * 100
        p['prev_stats']['otc_markup'] = inp[13]

    st.session_state.global_period += 1

# ==========================================
# 5. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V36.4")
    st.caption("Historical Inputs Match")
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
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.info("Load Historical Scenario.")
        if st.button("🚀 Initialize Scenario", type="primary"):
            initialize_hardcoded_scenario()
            st.success("Teams initialized.")
            st.session_state.game_state="ACTIVE"
            st.rerun()
    
    elif st.session_state.game_state == "ACTIVE":
        st.success(f"### 🏁 Period {st.session_state.global_period - 1} Results")
        if any(p['history'] for p in st.session_state.players.values()):
            df = generate_master_report(st.session_state.players)
            if not df.empty:
                st.dataframe(df.style.format(lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)), height=800, use_container_width=True)
        st.divider()
        c1, c2 = st.columns([3,1])
        c1.metric("Status", f"{sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')}/{len(st.session_state.players)} Teams Ready")
        if c2.button("⚙️ Setup Next Period", type="primary"):
            st.session_state.game_state = "MARKET_EDIT_RUN"
            st.rerun()

    elif st.session_state.game_state == "MARKET_EDIT_RUN":
        st.markdown(f"### 🚨 Market Environment (Period {st.session_state.global_period})"); 
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list}); 
        ed = st.data_editor(df_mkt, height=600, use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("🔙 Back"): st.session_state.game_state="ACTIVE"; st.rerun()
        if c2.button("🧮 RUN PERIOD", type="primary"): 
            st.session_state.market_data_list = ed['Value'].tolist(); 
            calculate_results(); 
            st.session_state.game_state="ACTIVE"; 
            st.rerun()

def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("⏳ Waiting for instructor..."); return
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    st.markdown(f"### 🏥 {p['shop_name']} (Period {p['period']})")
    tab1, tab2 = st.tabs(["📝 Decisions", "📊 History"])
    with tab1:
        if p['status'] == 'Submitted': 
            st.success("Decisions Submitted.")
            if st.button("Unlock to Edit"): p['status']='Thinking'; st.rerun()
        else:
            df_inputs = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df_inputs, hide_index=True, height=600, use_container_width=True)
            if st.button("Submit Decisions", type="primary"):
                p['inputs'] = ed['Value'].tolist()
                p['status'] = 'Submitted'
                st.rerun()
    with tab2:
        if p['history']:
            last = p['history'][-1]
            hist_df = pd.DataFrame([last], columns=REPORT_ORDER).T
            hist_df.columns = ["Value"]
            st.dataframe(hist_df.style.format("{:,.2f}"), height=800)
        else: st.info("No history available yet.")

role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor": 
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
