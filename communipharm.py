import streamlit as st
import pandas as pd
import numpy as np
import math

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V36.20 (Full Report)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.060} # Mall rent is usually higher

# Input Labels (Keep consistent)
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

# Weights for Ranking
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

# The specific order user requested
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
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

# Default Market Data (matches previous logic)
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
# 3. INITIALIZATION & DATA
# ==========================================
def get_static_scenario_data():
    """Exact data from Hisc1p1.xlsx"""
    data = [
        {'id': 'team_1', 'loc': 1, 'prev_price': 22.015, 'prev_share': 11.78, 'cash': 7423.15, 'inv_rx': 59918.04, 'inv_otc': 12322.0, 'notes_pay': 0.0, 'mortgage': 50000.0, 'ap': 60889.39, 'fix_asset': 32344.0, 'ar': 13211.0, 'ar_3rd': 14322.0, 'investments': 16121.0},
        {'id': 'team_2', 'loc': 2, 'prev_price': 18.040, 'prev_share': 13.17, 'cash': 2500.0, 'inv_rx': 76168.09, 'inv_otc': 86544.0, 'notes_pay': 0.0, 'mortgage': 70000.0, 'ap': 102000.0, 'fix_asset': 37677.0, 'ar': 53.76, 'ar_3rd': 26186.79, 'investments': 3232.0},
        {'id': 'team_3', 'loc': 2, 'prev_price': 18.040, 'prev_share': 20.69, 'cash': 2500.0, 'inv_rx': 60957.88, 'inv_otc': 117639.2, 'notes_pay': 2322.0, 'mortgage': 70000.0, 'ap': 61626.0, 'fix_asset': 37655.0, 'ar': 371.95, 'ar_3rd': 23233.0, 'investments': 19000.0},
        {'id': 'team_4', 'loc': 2, 'prev_price': 19.463, 'prev_share': 18.45, 'cash': 2200.0, 'inv_rx': 67308.29, 'inv_otc': 154192.0, 'notes_pay': 2322.0, 'mortgage': 70000.0, 'ap': 142260.2, 'fix_asset': 40233.0, 'ar': 859.15, 'ar_3rd': 23433.0, 'investments': 10523.14},
        {'id': 'team_5', 'loc': 3, 'prev_price': 19.274, 'prev_share': 11.25, 'cash': 2500.0, 'inv_rx': 65466.0, 'inv_otc': 98999.0, 'notes_pay': 0.0, 'mortgage': 90200.0, 'ap': 123222.0, 'fix_asset': 45322.0, 'ar': 0.0, 'ar_3rd': 12322.0, 'investments': 2232.0},
        {'id': 'team_6', 'loc': 3, 'prev_price': 19.109, 'prev_share': 14.07, 'cash': 2200.0, 'inv_rx': 95436.2, 'inv_otc': 99999.0, 'notes_pay': 0.0, 'mortgage': 90900.0, 'ap': 102000.0, 'fix_asset': 51233.0, 'ar': 4343.0, 'ar_3rd': 22323.0, 'investments': 32122.0},
        {'id': 'team_7', 'loc': 1, 'prev_price': 22.015, 'prev_share': 10.56, 'cash': 1323.0, 'inv_rx': 68224.16, 'inv_otc': 21222.0, 'notes_pay': 0.0, 'mortgage': 50433.0, 'ap': 32444.0, 'fix_asset': 34566.0, 'ar': 27174.01, 'ar_3rd': 12344.0, 'investments': 12333.0}
    ]
    return data

def get_starting_inputs():
    # Standard starting inputs to avoid zeros
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 2.0, 25.0, 2.0, 10.0, 3000.0, 30.0, 40.0, 833.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_hardcoded_scenario():
    st.session_state.players = {}
    st.session_state.global_period = 1
    scenarios = get_static_scenario_data()
    
    for s in scenarios:
        total_assets = s['cash'] + s['inv_rx'] + s['inv_otc'] + s['fix_asset'] + s['ar'] + s['ar_3rd'] + s['investments']
        total_liab = s['ap'] + s['notes_pay'] + s['mortgage']
        equity = total_assets - total_liab 
        
        financials = {
            'cash': s['cash'], 'investments': s['investments'],
            'acct_receivable': s['ar'], 'acct_receivable_3rd': s['ar_3rd'],
            'inventory_rx': s['inv_rx'], 'inventory_otc': s['inv_otc'],
            'fixed_assets': s['fix_asset'], 
            'acct_payable': s['ap'], 'notes_payable': s['notes_pay'], 'long_term_debt': s['mortgage'], 
            'retained_earnings': equity
        }
        
        prev_stats = { 
            'avg_price': s['prev_price'], 'mkt_share': s['prev_share'], 
            'rx_per_hr': 6.0, 'otc_markup': 45.0, 'ad_index': 1.0
        }
        
        team_id = s['id']
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {team_id.split('_')[1]} ({LOC_MAP[s['loc']]})", 
            'location_code': s['loc'], 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

# ==========================================
# 4. LOGIC ENGINE (CALCULATION)
# ==========================================

def calculate_results():
    # --- 1. Load Market Parameters ---
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    mkt = st.session_state.market_data_list
    
    BASE_COST_RX = mkt[0]
    PCT_3RD_PARTY = mkt[3] / 100.0
    MAX_AD_EXP = mkt[4]
    INT_RATE_LOAN = mkt[8]/100.0
    AVG_RX_VOL = mkt[9]
    AVG_OTC_VOL = mkt[10]
    SLIPPAGE_RATE = mkt[11]/100.0
    WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    LAG_AR = mkt[14]/100.0
    INFLATION = mkt[19]/100.0
    STOCKOUT_PENALTY_RX = mkt[20]/100.0
    STOCKOUT_PENALTY_OTC = mkt[21]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    active_stores = [p for p in store_list if p['location_code'] != 0]
    num_stores = len(active_stores)
    if num_stores == 0: return

    # --- 2. Prepare Ranking Data ---
    ranking_data = []
    
    # Pre-calc rents and wages adjustments
    FIXED_RENT_RATE = {k: v * (1 + INFLATION) for k, v in LOC_RENT_RATE.items()}
    total_rph_wage = sum([p['inputs'][18] for p in active_stores])
    avg_rph_wage = total_rph_wage / num_stores if num_stores else 25.0

    for p in active_stores:
        inp = p['inputs']; fin = p['financials']
        
        # Determine Price
        if inp[0] < 10: # Dollar Fee method
            rx_price = BASE_COST_RX + inp[0] + inp[1]
        else: # Percent Markup method
            rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1]
            
        # Ad Effect
        ad_factor = (inp[7] / MAX_AD_EXP) + (p['prev_stats'].get('ad_index', 1.0) * 0.5)
        curr_ad_index = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        p['curr_ad_index'] = curr_ad_index

        # Efficiency
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

    # --- 3. Compute Market Shares (Ranking) ---
    df_comp = pd.DataFrame(ranking_data)
    
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)

    if not df_comp.empty:
        # Rx Rankings
        cols = ['Price', 'PastPrice', 'Promo', 'Hours', 'Delivery', 'Records', 'Credit', 'Inventory', 'Share', 'Eff']
        asc = [True, True, False, False, False, False, False, False, False, False]
        for c, a in zip(cols, asc):
            target = 'prev_share' if c == 'Share' else c.lower().replace('eff', 'efficiency')
            df_comp[f'R_{c}'] = get_points(df_comp[target], a)

        # OTC Rankings
        df_comp['RO_Markup'] = get_points(df_comp['otc_markup'], True)
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], True)
        df_comp['RO_Promo'] = df_comp['R_Promo']; df_comp['RO_Hours'] = df_comp['R_Hours']
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], False)
        df_comp['RO_RxShare'] = df_comp['R_Share']

    # --- 4. Distribute Market Volume ---
    rx_scores = {}; otc_scores = {}
    total_rx_score = 0; total_otc_score = 0
    avg_mkt_price = df_comp['price'].mean()

    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        
        # Rx Score Calculation
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        score_rx = sum([row[f'R_{c}'] * w_rx[c] for c in ['Price','PastPrice','Promo','Hours','Delivery','Records','Credit','Inventory','MktShare','Efficiency']])
        
        # Price Sensitivity Bonus/Penalty
        if row['price'] < avg_mkt_price * 0.95: score_rx *= 1.15
        if row['price'] > avg_mkt_price * 1.05: score_rx *= 0.85
        rx_scores[tid] = score_rx; total_rx_score += score_rx

        # OTC Score Calculation
        w_otc = otc_w_df.set_index("Factor")[loc_name]
        score_otc = sum([row[f'RO_{c}'] * w_otc[c] for c in ['PresMarkup','PrevMarkup','AdIndex','Hours','Inventory','RxShare']])
        otc_scores[tid] = score_otc; total_otc_score += score_otc

    # --- 5. Financial Calculation per Store ---
    total_rx_mkt_vol = AVG_RX_VOL * num_stores
    total_otc_mkt_vol = AVG_OTC_VOL * num_stores

    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        
        # A. Revenue Logic
        # Market Share
        my_rx_share_raw = rx_scores[tid] / total_rx_score
        my_otc_share_raw = otc_scores[tid] / total_otc_score
        
        # Location & Traffic Adjustments (Crucial for "Trends")
        loc_type = LOC_MAP[p['location_code']]
        
        # Rx Volume
        base_rx_vol = total_rx_mkt_vol * my_rx_share_raw
        if loc_type == "Medical Center": base_rx_vol *= 1.10 # Medical centers get more Rx
        elif loc_type == "Shopping Center": base_rx_vol *= 0.85 # Malls get less Rx
        
        # OTC Sales Volume ($)
        base_otc_sales = total_otc_mkt_vol * my_otc_share_raw
        if loc_type == "Shopping Center": base_otc_sales *= 2.5 # Malls get HUGE OTC
        elif loc_type == "Medical Center": base_otc_sales *= 0.2 # Medicals get tiny OTC
        
        # Pricing
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else BASE_COST_RX + inp[0] + inp[1]
        
        # 3rd Party Split
        vol_3rd = base_rx_vol * PCT_3RD_PARTY
        vol_pvt = base_rx_vol * (1 - PCT_3RD_PARTY)
        
        rev_rx_pvt = vol_pvt * unit_price
        rev_rx_3rd = vol_3rd * (BASE_COST_RX + mkt[2]) # Fee based
        total_rx_rev = rev_rx_pvt + rev_rx_3rd
        
        total_otc_rev = base_otc_sales # Already in $
        total_rev = total_rx_rev + total_otc_rev
        
        # B. COGS & Inventory
        # Rx COGS
        rx_cogs_base = base_rx_vol * BASE_COST_RX
        rx_slippage = total_rx_rev * SLIPPAGE_RATE * (1 + (100-inp[21])/100) # Mgr time reduces theft
        rx_cogs_total = rx_cogs_base + rx_slippage
        
        # OTC COGS
        otc_cogs_base = total_otc_rev / (1 + inp[13]/100)
        otc_slippage = total_otc_rev * SLIPPAGE_RATE * 1.5
        otc_cogs_total = otc_cogs_base + otc_slippage
        
        # Emergency Purchase Logic
        req_rx = rx_cogs_total
        avail_rx = fin['inventory_rx'] + inp[14]
        emer_rx = max(0, req_rx - avail_rx)
        if emer_rx > 0: emer_rx *= (1 + STOCKOUT_PENALTY_RX) # Penalty cost
        
        req_otc = otc_cogs_total
        avail_otc = fin['inventory_otc'] + inp[15]
        emer_otc = max(0, req_otc - avail_otc)
        if emer_otc > 0: emer_otc *= (1 + STOCKOUT_PENALTY_OTC)

        actual_cogs_rx = rx_cogs_total # Used for accounting
        actual_cogs_otc = otc_cogs_total
        
        # C. Expenses
        # Payroll
        std_rate = 12.0 # Rx/hr standard
        capacity_rx = (p['eff_rph_val'] * 40 * WEEKS_PER_PERIOD) * std_rate
        rph_ot_hours = max(0, (base_rx_vol - capacity_rx) / std_rate)
        
        wage_rph = (p['eff_rph_val'] * 40 * WEEKS_PER_PERIOD * inp[18]) + (rph_ot_hours * inp[18] * 1.5)
        
        clk_hrs = inp[19] * 40 * WEEKS_PER_PERIOD
        # Heuristic: Need 1 clerk hr per 20 Rx + 1 clerk hr per $500 OTC
        needed_clk_hrs = (base_rx_vol / 15) + (total_otc_rev / 400)
        clk_ot_hours = max(0, needed_clk_hrs - clk_hrs)
        wage_clk = (clk_hrs * inp[20]) + (clk_ot_hours * inp[20] * 1.5)
        
        ben_pct = 0.15 + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        ben_cost = (wage_rph + wage_clk) * ben_pct
        
        mgr_salary = inp[21] * (52/12) # Annualized approx for period
        
        rent = total_rev * FIXED_RENT_RATE.get(p['location_code'], 0.03)
        utilities = 3000 * (1 + INFLATION)
        promo = inp[7]
        mortgage_pay = inp[23] * 12 # Annualized for period
        
        total_opex = wage_rph + wage_clk + ben_cost + mgr_salary + rent + utilities + promo + mortgage_pay
        
        gross_margin = total_rev - (actual_cogs_rx + actual_cogs_otc)
        
        # D. Financial Position Updates
        cash_start = fin['cash']
        
        # Inflows
        cash_sales = total_rev * 0.3 # 30% Cash sales
        ar_collection = fin['acct_receivable'] * (1 - LAG_AR) # Collect old AR
        cash_in = cash_sales + ar_collection
        
        # Outflows
        ap_payment = inp[28] # Pay A/P
        purchases = inp[14] + inp[15] + emer_rx + emer_otc
        cash_out = ap_payment + total_opex + purchases 
        
        net_cash_change = cash_in - cash_out
        
        # End Calculations
        fin['cash'] += net_cash_change
        
        # Emergency Loan Check
        eloan = 0
        if fin['cash'] < inp[25]:
            eloan = inp[25] - fin['cash']
            fin['cash'] += eloan
            fin['notes_payable'] += eloan
        
        # Update Balance Sheet
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_rx) - actual_cogs_rx
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_otc) - actual_cogs_otc
        
        new_ar = total_rev * 0.7 # 70% goes to AR
        fin['acct_receivable'] = (fin['acct_receivable'] * LAG_AR) + new_ar
        
        fin['acct_payable'] = (fin['acct_payable'] - ap_payment) + inp[14] + inp[15]
        
        interest_exp = (fin['notes_payable'] + fin['long_term_debt']) * (INT_RATE_LOAN / 4) # Quarterly
        net_profit = gross_margin - total_opex - interest_exp
        
        fin['retained_earnings'] += net_profit
        
        # E. REPORT GENERATION (THE BIG LIST)
        total_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'] + fin['acct_receivable']
        total_liab = fin['acct_payable'] + fin['notes_payable'] + fin['long_term_debt']
        net_worth = total_assets - total_liab
        curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']

        report = {
            "TOT SALES": total_rev,
            "Rx SALES": total_rx_rev,
            "OTH SALES": total_otc_rev,
            "Avg Rx Pr": unit_price,
            "Rx Ing $": BASE_COST_RX,
            "Rx GM%": ((total_rx_rev - actual_cogs_rx)/total_rx_rev*100) if total_rx_rev else 0,
            "3-Pty GM%": ((rev_rx_3rd - (vol_3rd * BASE_COST_RX))/rev_rx_3rd*100) if rev_rx_3rd else 0,
            "Tot #Rx's": base_rx_vol,
            "3-Pty #Rx": vol_3rd,
            "Copay Dis": inp[2],
            "OTC M'kup": inp[13],
            "Rx Mkt Sh": my_rx_share_raw * 100,
            "Store Hrs": inp[6],
            "A/P Paid": inp[28],
            "M'age Pay": inp[23],
            "Loan": fin['notes_payable'],
            "Mgr Hrs": inp[23],
            "RP OverT": rph_ot_hours,
            "RP Hr Pay": inp[18],
            "Clk OverT": clk_ot_hours,
            "Clk Wage": inp[20],
            "Adv Exp": inp[7],
            "Net Worth": net_worth,
            "Cash Flow": net_cash_change,
            "E Rx Pur": emer_rx,
            "E OTC Pur": emer_otc,
            "RATIO: Current": (curr_assets / curr_liab) if curr_liab else 0,
            "RATIO: Acid Test": ((fin['cash'] + fin['acct_receivable']) / curr_liab) if curr_liab else 0,
            "RATIO: Turnover": ((actual_cogs_rx + actual_cogs_otc) / (fin['inventory_rx'] + fin['inventory_otc'])) if (fin['inventory_rx'] + fin['inventory_otc']) else 0,
            "RATIO: ROI %": (net_profit / total_assets * 100) if total_assets else 0,
            "RATIO: ROA %": (net_profit / total_assets * 100) if total_assets else 0, # Same as ROI for this simplified sim
            "RATIO: G Margin %": (gross_margin / total_rev * 100) if total_rev else 0,
            "RATIO: Profit %": (net_profit / total_rev * 100) if total_rev else 0,
            "RATIO: Debt/NW": (total_liab / net_worth) if net_worth else 0,
            "LOCATION": LOC_MAP[p['location_code']]
        }
        
        # Save History
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
    st.title("💊 Communi-Pharm V36.20")
    st.caption("Full Report + Tuned Logic")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def generate_master_report(players):
    """Generates the wide report with specific row ordering"""
    data = {}
    for p_id, p in players.items():
        if not p['history']: continue
        last = p['history'][-1]
        data[p['shop_name']] = last

    if not data: return pd.DataFrame()
    
    df = pd.DataFrame(data)
    # Reindex to force the specific order requested
    df = df.reindex(REPORT_ORDER)
    return df

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.info("Click below to load the hardcoded scenario.")
        if st.button("🚀 Initialize Teams (Auto-Data)", type="primary"):
            initialize_hardcoded_scenario()
            st.success("Teams initialized.")
            st.session_state.game_state="ACTIVE"
            st.rerun()
    
    elif st.session_state.game_state == "ACTIVE":
        st.success(f"### 🏁 Period {st.session_state.global_period - 1} Results")
        
        if any(p['history'] for p in st.session_state.players.values()):
            df = generate_master_report(st.session_state.players)
            if not df.empty:
                # Format specific rows
                st.dataframe(
                    df.style.format(lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)), 
                    height=800, 
                    use_container_width=True
                )
        
        st.divider()
        c1, c2 = st.columns([3,1])
        c1.metric("Status", f"{sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')}/{len(st.session_state.players)} Teams Ready")
        
        if c2.button("🧮 RUN PERIOD"):
            calculate_results()
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
            # Inputs Form
            df_inputs = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df_inputs, hide_index=True, height=600, use_container_width=True)
            if st.button("Submit Decisions", type="primary"):
                p['inputs'] = ed['Value'].tolist()
                p['status'] = 'Submitted'
                st.rerun()

    with tab2:
        if p['history']:
            # Show the same full report style but vertical for the student
            last = p['history'][-1]
            hist_df = pd.DataFrame([last], columns=REPORT_ORDER).T
            hist_df.columns = ["Value"]
            st.dataframe(hist_df.style.format("{:,.2f}"), height=800)
        else:
            st.info("No history available yet.")

# Main Router
role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor": 
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
