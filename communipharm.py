import streamlit as st
import pandas as pd
import numpy as np
import math

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V36 (Scenario Edition)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.9em; }
    .metric-header { font-weight: bold; background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# --- LILLY DIGEST BENCHMARKS ---
LILLY_BENCHMARKS = {
    "Gross Margin %": 32.5,
    "Payroll Expenses %": 13.5,
    "Rent %": 2.8,
    "Net Profit %": 3.5,
    "Inventory Turnover": 5.5,
    "Current Ratio": 2.5,
    "ROA": 10.0,
    "ROE": 15.0
}

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

# --- WEIGHT CONFIGURATION ---
RX_DEFAULT = {
    "Factor": ["PastPrice", "Price", "Promo", "Hours", "Delivery", "Records", "Credit", "Inventory", "MktShare", "Efficiency"],
    "Medical Center":    [10, 5, 11, 7, 10, 15, 3, 10, 23, 6],
    "Neighborhood":      [22, 5, 13, 11, 6, 8, 2, 11, 16, 6],
    "Shopping Center":   [25, 10, 15, 12, 1, 1, 1, 10, 5, 10]
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
# 3. HELPER FUNCTIONS (PARSER & INIT)
# ==========================================

# --- 3.1 Scenario Parser ---
def parse_scenario_file(file_content):
    """Parses HISTC1.P1 raw content into structured store data"""
    try:
        # Clean and split into float tokens
        raw_data = file_content.replace('\n', ' ').replace('\r', ' ')
        tokens = [float(x) for x in raw_data.split() if x.replace('.', '', 1).replace('-', '', 1).replace('E', '', 1).isdigit()]
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return []

    stores_data = []
    i = 0
    # Pattern scanning: Look for [Price 10-40] [0] [Cash] ... [Location@8]
    while i < len(tokens) - 20:
        # Heuristic: Price is usually 10-40, next is 0, index+8 is loc (1,2,3)
        price_chk = (10 < tokens[i] < 40)
        zero_chk = (tokens[i+1] == 0)
        loc_chk = (tokens[i+8] in [1, 2, 3])
        
        if price_chk and zero_chk and loc_chk:
            try:
                s = {}
                s['prev_price'] = tokens[i]     # Index 0
                s['cash']       = tokens[i+2]   # Index 2
                s['inv_rx']     = tokens[i+3]   # Index 3
                s['inv_otc']    = tokens[i+4]   # Index 4
                s['notes_pay']  = tokens[i+5]   # Index 5 (Liability)
                s['fix_asset']  = tokens[i+6]   # Index 6
                s['loc_code']   = int(tokens[i+8]) # Index 8
                s['ap']         = tokens[i+9]   # Index 9
                s['lt_debt']    = tokens[i+10]  # Index 10
                s['retained']   = tokens[i+11]  # Index 11
                s['ar']         = tokens[i+12]  # Index 12
                # Note: Prev share is further down, approx index 16
                s['prev_share'] = tokens[i+16] * 100 if (i+16) < len(tokens) else 15.0
                
                stores_data.append(s)
                i += 50 # Skip ahead to find next block
            except IndexError:
                break
        else:
            i += 1
    return stores_data

# --- 3.2 Inputs & Init Functions ---
def get_starting_inputs():
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 1.0, 25.0, 1.0, 10.0, 3000.0, 30.0, 40.0, 60.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_teams_manual(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        financials = {
            'cash': 15000.0, 'investments': 2000.0, 'acct_receivable': 45000.0, 'acct_receivable_3rd': 10000.0,
            'inventory_rx': 55000.0, 'inventory_otc': 25000.0,
            'fixed_assets': 50000.0, 'acct_payable': 30000.0,
            'notes_payable': 0.0, 'long_term_debt': 100000.0, 'retained_earnings': 138000.0
        }
        prev_stats = { 
            'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 
            'rx_per_hr': 5.0, 'otc_markup': 45.0,
            'ad_index': 1.0, 'cogs_rx': 40000.0, 'avg_inv_rx': 50000.0,
            'cogs_otc': 20000.0, 'avg_inv_otc': 25000.0
        }
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': prev_stats, 'history': [] 
        }

def initialize_teams_from_scenario(scenarios):
    st.session_state.players = {}
    st.session_state.global_period = 1 
    
    for i, data in enumerate(scenarios):
        team_num = i + 1
        team_id = f"team_{team_num}"
        
        # Init Financials from Scenario Data
        financials = {
            'cash': data['cash'], 
            'investments': 0.0,
            'acct_receivable': data['ar'], 
            'acct_receivable_3rd': 5000.0, # Estimate split
            'inventory_rx': data['inv_rx'], 
            'inventory_otc': data['inv_otc'],
            'fixed_assets': data['fix_asset'], 
            'acct_payable': data['ap'],
            'notes_payable': data['notes_pay'], 
            'long_term_debt': data['lt_debt'], 
            'retained_earnings': data['retained']
        }
        
        # Init Stats
        prev_stats = { 
            'avg_price': data['prev_price'], 
            'mkt_share': data['prev_share'], 
            'rx_per_hr': 6.0, 
            'otc_markup': 45.0,
            'ad_index': 1.0, 
            'cogs_rx': data['inv_rx'] * 0.8, 
            'avg_inv_rx': data['inv_rx'],
            'cogs_otc': data['inv_otc'] * 0.8, 
            'avg_inv_otc': data['inv_otc']
        }
        
        # Create Player
        st.session_state.players[team_id] = {
            'id': team_id, 
            'shop_name': f"Store {team_num} ({LOC_MAP[data['loc_code']]})", 
            'location_code': data['loc_code'], # Locked Location
            'status': 'Pending',
            'period': 1, 
            'inputs': get_starting_inputs(), 
            'financials': financials,
            'prev_stats': prev_stats, 
            'history': [] 
        }

# --- 3.3 Report Generator (NEW) ---
def generate_master_report(players):
    """สร้างตารางสรุปข้อมูลทั้งหมด (Master Table) ตามรายการที่ Instructor ต้องการ"""
    data = []
    
    # ดึงค่า Market Data ปัจจุบัน
    mkt = st.session_state.market_data_list
    base_rx_cost = mkt[0]
    
    for p_id, p in players.items():
        if not p['history']: continue
        
        last = p['history'][-1] # ข้อมูลผลลัพธ์งวดล่าสุด
        inp = p['inputs']       # ข้อมูลการตัดสินใจ (Inputs)
        fin = p['financials']   # งบการเงินปัจจุบัน

        # --- ดึงตัวเลขและคำนวณ ---
        tot_sales = last['total_rev']
        rx_sales = last['rev_rx']
        oth_sales = last['rev_otc']
        
        # Rx Stats
        rx_vol_est = rx_sales / last['avg_price'] if last['avg_price'] > 0 else 0
        avg_rx_pr = last['avg_price']
        # Cost per unit (รวม Slippage แล้ว)
        rx_ing_cost = (last['cogs_rx'] / rx_vol_est) if rx_vol_est > 0 else base_rx_cost
        
        # Margins
        rx_gm_pct = ((rx_sales - last['cogs_rx']) / rx_sales * 100) if rx_sales > 0 else 0
        # สมมติ 3rd Party GM ต่ำกว่าปกติเล็กน้อย หรือใช้ค่าเฉลี่ย
        party_gm_pct = rx_gm_pct * 0.95 
        
        # Volume Breakdown (Estimate)
        tot_rxs = int(rx_vol_est)
        party_rxs = int(tot_rxs * (mkt[3]/100)) # ใช้ % จาก Market Data

        # Ratios & Financials
        total_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['fixed_assets'] + fin['acct_receivable']
        total_liab = fin['acct_payable'] + fin['notes_payable'] + fin['long_term_debt']
        net_worth = total_assets - total_liab
        
        curr_assets = fin['cash'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        current_ratio = (curr_assets / curr_liab) if curr_liab > 0 else 0
        acid_test = ((fin['cash'] + fin['acct_receivable']) / curr_liab) if curr_liab > 0 else 0
        turnover = (last['total_cogs'] / (fin['inventory_rx'] + fin['inventory_otc'])) if (fin['inventory_rx'] + fin['inventory_otc']) > 0 else 0
        
        roi = (last['net_profit'] / total_assets * 100) if total_assets > 0 else 0
        roa = roi # ในโมเดลนี้สินทรัพย์รวมใกล้เคียงเงินลงทุน
        debt_nw = (total_liab / net_worth) if net_worth > 0 else 0

        # --- จัดลง Dictionary ตาม Format ที่ต้องการ ---
        row = {
            "Store": p['shop_name'],
            "TOT SALES": tot_sales,
            "Rx SALES": rx_sales,
            "OTH SALES": oth_sales,
            "Avg Rx Pr": avg_rx_pr,
            "Rx Ing $": rx_ing_cost,
            "Rx GM%": rx_gm_pct,
            "3-Pty GM%": party_gm_pct,
            "Tot #Rx's": tot_rxs,
            "3-Pty #Rx": party_rxs,
            "Copay Dis": inp[2],  # Index 2: Copay Discount
            "OTC M'kup": inp[13], # Index 13: Markup Other
            "Rx Mkt Sh": last['Rx Mkt Sh'],
            "Store Hrs": inp[6],  # Index 6: Hours Open
            "A/P Paid": inp[28],  # Index 28: Pay A/P
            "M'age Pay": inp[23], # Index 23: Mortgage
            "Loan": fin['notes_payable'], # Short Term Loan
            "Mgr Hrs": inp[22],   # Index 22: Mgr Hrs/Week
            "RP OverT": 0.0,      # (คำนวณละเอียดใน Logic หลักแล้ว แต่ไม่ได้เก็บแยกตัวแปรไว้ ขอใส่ 0 ไว้ก่อน)
            "RP Hr Pay": inp[17], # Index 17: Pharm Wage
            "Clk OverT": 0.0,
            "Clk Wage": inp[19],  # Index 19: Clerk Wage
            "Adv Exp": inp[7],    # Index 7: Promo Exp
            "Net Worth": net_worth,
            "Cash Flow": last['cf_end'] - last['cf_start'],
            "E Rx Pur": 0.0, # ต้องดึงจาก Logic (ใน v36 รวมไปใน Purchases แล้ว)
            "E OTC Pur": 0.0,
            "RATIO: Current": current_ratio,
            "RATIO: Acid Test": acid_test,
            "RATIO: Turnover": turnover,
            "RATIO: ROI %": roi,
            "RATIO: ROA %": roa,
            "RATIO: G Margin %": last['kpi_gm_pct'],
            "RATIO: Profit %": last['kpi_np_pct'],
            "RATIO: Debt/NW": debt_nw,
            "LOCATION": LOC_MAP[p['location_code']]
        }
        data.append(row)

    if not data: return pd.DataFrame()
    return pd.DataFrame(data).set_index("Store").T

# ==========================================
# 4. LOGIC ENGINE (V32 Hybrid)
# ==========================================
def calculate_results():
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    mkt = st.session_state.market_data_list
    
    # --- Market Data Unpacking ---
    BASE_COST_RX = mkt[0]; PCT_3RD_PARTY = mkt[3]/100.0
    MAX_AD_EXP = mkt[4]
    INT_RATE_LOAN = mkt[8]/100.0; 
    AVG_RX_VOL = mkt[9]; AVG_OTC_VOL = mkt[10]
    SLIPPAGE_RATE = mkt[11]/100.0
    WEEKS_PER_PERIOD = 52 / mkt[12] if mkt[12] > 0 else 13
    LAG_3RD_PARTY = mkt[13]/100.0; LAG_AR = mkt[14]/100.0
    INFLATION = mkt[19]/100.0
    RX_PURCH_INDEX = mkt[20]/100.0; OTC_PURCH_INDEX = mkt[21]/100.0
    SAVINGS_RATE = mkt[22]/100.0; CD_RATE = mkt[24]/100.0; SALES_PER_CLERK = mkt[25]
    BENEFIT_PCT = mkt[27]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    active_stores = [p for p in store_list if p['location_code'] != 0]
    num_stores = len(active_stores)
    if num_stores == 0: return

    # Update Fixed Expenses with Inflation
    FIXED_RENT_RATE = {k: v * (1 + INFLATION) for k, v in LOC_RENT_RATE.items()}

    # --- PHASE 1: HR ---
    total_rph_wage = sum([p['inputs'][18] for p in active_stores])
    avg_rph_wage = total_rph_wage / num_stores if num_stores else 25.0

    for p in active_stores:
        inp = p['inputs']; fin = p['financials']
        # Returns
        fin['inventory_rx'] = max(0, fin['inventory_rx'] - inp[26])
        fin['inventory_otc'] = max(0, fin['inventory_otc'] - inp[27])
        fin['cash'] += (inp[26] * 0.8) + (inp[27] * 0.8)
        
        # Wage Penalty
        ben_cost_factor = 1 + BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        my_rph_real_wage = inp[18] * ben_cost_factor
        
        p['eff_rph'] = max(0, inp[17] - 1.0) if my_rph_real_wage < (0.9 * avg_rph_wage) else inp[17]
        p['eff_clk'] = inp[19] # Simplify clerk logic
        p['wage_penalty'] = (inp[17] - p['eff_rph']) > 0

    # --- PHASE 2: MARKET SHARE ---
    ranking_data = []
    
    # HMO Auction
    hmo_bids = [(p['id'], p['inputs'][35]) for p in active_stores if p['inputs'][35] > 0]
    hmo_winners = []
    if hmo_bids:
        hmo_bids.sort(key=lambda x: x[1])
        min_bid = hmo_bids[0][1]
        hmo_winners = [x[0] for x in hmo_bids if x[1] == min_bid]

    # Calculate Factors
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']
        
        rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        ad_factor = (inp[7] / MAX_AD_EXP) + (prev.get('ad_index', 1.0) * 0.533)
        p['curr_ad_index'] = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        
        inv_level_rx = fin['inventory_rx']; inv_level_otc = fin['inventory_otc']

        ranking_data.append({
            'id': tid, 'loc': p['location_code'],
            'price': rx_price,
            'past_price': prev.get('avg_price', 15.0),
            'promo': p['curr_ad_index'],
            'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': inv_level_rx, 'inv_otc': inv_level_otc,
            'prev_share': prev['mkt_share'],
            'efficiency': prev.get('rx_per_hr', 5.0),
            'otc_markup': inp[13],
            'prev_otc_markup': prev.get('otc_markup', 45.0)
        })
    
    df_comp = pd.DataFrame(ranking_data)
    
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)
        
    rx_shares = {}; otc_shares = {}
    
    if not df_comp.empty:
        # Rx Ranking
        df_comp['R_Price'] = get_points(df_comp['price'], True)
        df_comp['R_PastPrice'] = get_points(df_comp['past_price'], True)
        df_comp['R_Promo'] = get_points(df_comp['promo'], False)
        df_comp['R_Hours'] = get_points(df_comp['hours'], False)
        df_comp['R_Delivery'] = get_points(df_comp['delivery'], False)
        df_comp['R_Records'] = get_points(df_comp['records'], False)
        df_comp['R_Credit'] = get_points(df_comp['credit'], False)
        df_comp['R_Inventory'] = get_points(df_comp['inventory'], False)
        df_comp['R_Share'] = get_points(df_comp['prev_share'], False)
        df_comp['R_Eff'] = get_points(df_comp['efficiency'], False)

        # OTC Ranking
        df_comp['RO_Markup'] = get_points(df_comp['otc_markup'], True)
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], True)
        df_comp['RO_Promo'] = df_comp['R_Promo']
        df_comp['RO_Hours'] = df_comp['R_Hours']
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], False)
        df_comp['RO_RxShare'] = df_comp['R_Share']

    # Final Shares
    total_rx_score = 0; total_otc_score = 0
    rx_scores = {}; otc_scores = {}

    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        
        # Rx
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        score_rx = (row['R_Price'] * w_rx['Price']) + (row['R_PastPrice'] * w_rx['PastPrice']) + \
                   (row['R_Promo'] * w_rx['Promo']) + (row['R_Hours'] * w_rx['Hours']) + \
                   (row['R_Delivery'] * w_rx['Delivery']) + (row['R_Records'] * w_rx['Records']) + \
                   (row['R_Credit'] * w_rx['Credit']) + (row['R_Inventory'] * w_rx['Inventory']) + \
                   (row['R_Share'] * w_rx['MktShare']) + (row['R_Eff'] * w_rx['Efficiency'])
        
        if st.session_state.players[tid]['inputs'][33]: score_rx *= 1.05
        rx_scores[tid] = score_rx; total_rx_score += score_rx

        # OTC
        w_otc = otc_w_df.set_index("Factor")[loc_name]
        score_otc = (row['RO_Markup'] * w_otc['PresMarkup']) + (row['RO_PrevMarkup'] * w_otc['PrevMarkup']) + \
                    (row['RO_Promo'] * w_otc['AdIndex']) + (row['RO_Hours'] * w_otc['Hours']) + \
                    (row['RO_Inventory'] * w_otc['Inventory']) + (row['RO_RxShare'] * w_otc['RxShare'])
        
        otc_scores[tid] = score_otc; total_otc_score += score_otc

    for tid in active_stores:
        tid_str = tid['id']
        rx_shares[tid_str] = rx_scores[tid_str] / total_rx_score if total_rx_score > 0 else 1.0/num_stores
        otc_shares[tid_str] = otc_scores[tid_str] / total_otc_score if total_otc_score > 0 else 1.0/num_stores

    # --- PHASE 3: OPERATIONS ---
    total_rx_mkt = AVG_RX_VOL * num_stores; total_otc_mkt = AVG_OTC_VOL * num_stores
    
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']; prev = p['prev_stats']
        
        # Sales
        my_rx_share = rx_shares.get(tid, 0); my_otc_share = otc_shares.get(tid, 0)
        base_rx_vol = total_rx_mkt * my_rx_share
        hmo_vol = (200 / len(hmo_winners)) if tid in hmo_winners else 0
        total_rx_vol = base_rx_vol + hmo_vol
        
        total_otc_sales = (total_otc_mkt * my_otc_share) 
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        # Revenue Breakdown (For Reports)
        rev_rx_normal = base_rx_vol * unit_price
        rev_rx_hmo = hmo_vol * inp[35]
        total_rx_sales = rev_rx_normal + rev_rx_hmo
        total_sales = total_rx_sales + total_otc_sales
        
        # COGS & Stockout
        cogs_rx_total = total_rx_vol * BASE_COST_RX
        cogs_otc_total = total_otc_sales / (1 + inp[13]/100)
        
        req_inv_rx = cogs_rx_total * (1 + RX_PURCH_INDEX)
        avail_inv_rx = fin['inventory_rx'] + inp[14]
        emer_purch_rx = max(0, req_inv_rx - avail_inv_rx)
        
        req_inv_otc = cogs_otc_total * (1 + OTC_PURCH_INDEX)
        avail_inv_otc = fin['inventory_otc'] + inp[15]
        emer_purch_otc = max(0, req_inv_otc - avail_inv_otc)
        
        # Slippage
        mgr_control_factor = 1.0 + (inp[21]/100.0)
        actual_slippage = total_sales * SLIPPAGE_RATE * mgr_control_factor
        cogs_rx_total += (actual_slippage * 0.5)
        cogs_otc_total += (actual_slippage * 0.5)

        # OT
        std_rate = 10.0 if inp[4] else 12.5
        capacity_rx = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD) * std_rate
        rph_ot_hours = max(0, (total_rx_vol - capacity_rx) / std_rate)
        
        # --- PHASE 4: FINANCIALS ---
        # Expenses Breakdown
        wage_rph = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD * inp[18]) + (rph_ot_hours * inp[18] * 1.5)
        wage_clk = (p['eff_clk'] * 40 * WEEKS_PER_PERIOD * inp[20])
        total_wages = wage_rph + wage_clk
        ben_cost = total_wages * (BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0))
        
        rent = total_sales * FIXED_RENT_RATE.get(p['location_code'], 0.03)
        bad_debt = (total_sales * 0.01) + inp[29]
        utilities = 3000 * (1 + INFLATION)
        promo = inp[7]
        mgr_salary = inp[20] * 3
        mortgage = inp[23]
        
        total_opex = total_wages + ben_cost + rent + utilities + promo + mgr_salary + bad_debt + mortgage
        
        gm = total_sales - (cogs_rx_total + cogs_otc_total)
        intr_exp = (fin['long_term_debt'] + fin['notes_payable']) * INT_RATE_LOAN
        intr_inc = (fin['investments'] * CD_RATE)
        
        net_profit = gm - total_opex - intr_exp + intr_inc
        
        # Cash Flow (Direct Method)
        cash_start = fin['cash']
        # Inflow
        inflow_sales = (total_sales * 0.8) # Approx Cash Sales
        inflow_ar = fin['acct_receivable'] * (1 - LAG_AR)
        inflow_debt_recovered = inp[30]
        inflow_interest = intr_inc
        total_cash_in = inflow_sales + inflow_ar + inflow_debt_recovered + inflow_interest
        
        # Outflow
        outflow_ap = inp[28]
        outflow_wages = total_wages + ben_cost + mgr_salary
        outflow_rent = rent
        outflow_promo = promo
        outflow_util = utilities
        outflow_purch = emer_purch_rx + emer_purch_otc
        outflow_mortgage = mortgage
        total_cash_out = outflow_ap + outflow_wages + outflow_rent + outflow_promo + outflow_util + outflow_purch + outflow_mortgage + intr_exp
        
        fin['cash'] = cash_start + total_cash_in - total_cash_out
        
        # Emergency Loan
        e_loan = 0
        if fin['cash'] < inp[25]:
            e_loan = inp[25] - fin['cash']
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan

        # BS Update
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_purch_rx) - cogs_rx_total
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_purch_otc) - cogs_otc_total
        fin['acct_payable'] = (fin['acct_payable'] - inp[28]) + inp[14] + inp[15]
        
        new_ar = total_sales * 0.2
        fin['acct_receivable'] = (fin['acct_receivable'] * LAG_AR) + new_ar
        fin['retained_earnings'] += net_profit
        
        # History
        p['prev_stats'].update({
            'avg_price': unit_price,
            'mkt_share': my_rx_share * 100,
            'otc_markup': inp[13],
            'rx_per_hr': total_rx_vol / (p['eff_rph']*40*WEEKS_PER_PERIOD) if p['eff_rph'] else 0
        })
        
        # --- SAVE DETAILED METRICS ---
        metrics = {
            # Income Statement
            "rev_rx": total_rx_sales, "rev_otc": total_otc_sales, "total_rev": total_sales,
            "cogs_rx": cogs_rx_total, "cogs_otc": cogs_otc_total, "total_cogs": cogs_rx_total + cogs_otc_total,
            "gross_margin": gm,
            "exp_wages": total_wages, "exp_ben": ben_cost, "exp_mgr": mgr_salary,
            "exp_rent": rent, "exp_util": utilities, "exp_promo": promo,
            "exp_bad_debt": bad_debt, "exp_mortgage": mortgage,
            "exp_interest": intr_exp, "inc_interest": intr_inc,
            "net_profit": net_profit,
            
            # Balance Sheet
            "bs_cash": fin['cash'], "bs_ar": fin['acct_receivable'] + fin['acct_receivable_3rd'],
            "bs_inv_rx": fin['inventory_rx'], "bs_inv_otc": fin['inventory_otc'],
            "bs_invest": fin['investments'], "bs_fixed": fin['fixed_assets'],
            "bs_ap": fin['acct_payable'], "bs_notes": fin['notes_payable'], 
            "bs_lt_debt": fin['long_term_debt'], "bs_equity": fin['retained_earnings'],
            
            # Cash Flow
            "cf_start": cash_start, "cf_in": total_cash_in, "cf_out": total_cash_out,
            "cf_eloan": e_loan, "cf_end": fin['cash'],
            
            # KPIs
            "kpi_gm_pct": (gm/total_sales*100) if total_sales else 0,
            "kpi_payroll_pct": ((total_wages+ben_cost+mgr_salary)/total_sales*100) if total_sales else 0,
            "kpi_rent_pct": (rent/total_sales*100) if total_sales else 0,
            "kpi_np_pct": (net_profit/total_sales*100) if total_sales else 0,
            
            # Extra Data for Report
            "avg_price": unit_price,
            "Rx Mkt Sh": my_rx_share * 100,
            "LOCATION": LOC_MAP[p['location_code']]
        }
        p['history'].append(metrics)
        p['status'] = 'Pending'; p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 5. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V36")
    st.caption("Scenario Edition")
    if st.button("🔄 FACTORY RESET", type="primary"): st.session_state.clear(); st.rerun()

def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    # --- 1. SETUP PHASE ---
    if st.session_state.game_state.startswith("SETUP"):
        if st.session_state.game_state == "SETUP_STEP_1":
            st.markdown("### Step 1: Initialize Teams")
            
            # Option A: Manual
            with st.expander("Manual Setup"):
                n = st.number_input("Number of Teams", 1, 20, 5)
                if st.button("Create Teams"): 
                    initialize_teams_manual(n)
                    st.session_state.game_state="SETUP_STEP_2"
                    st.rerun()

            # Option B: Upload Scenario
            with st.expander("Load Scenario File", expanded=True):
                uploaded_file = st.file_uploader("Upload HISTC1.P1", type=None)
                if st.button("Load & Create"):
                    if uploaded_file:
                        content = uploaded_file.getvalue().decode("utf-8")
                        scenarios = parse_scenario_file(content)
                        if scenarios:
                            initialize_teams_from_scenario(scenarios)
                            st.success(f"Loaded {len(scenarios)} stores.")
                            st.session_state.game_state="SETUP_STEP_2"
                            st.rerun()
                    else:
                        st.error("Please upload a file.")

        elif st.session_state.game_state == "SETUP_STEP_2":
            st.markdown("### Step 2: Check Configuration")
            st.write("Weights & Settings Ready.")
            if st.button("Start Game"): 
                st.session_state.game_state="ACTIVE"
                st.rerun()
    
    # --- 2. ACTIVE PHASE (Dashboard) ---
    elif st.session_state.game_state == "ACTIVE":
        st.success(f"### 🏁 Period {st.session_state.global_period - 1} Results")
        
        # [NEW] เรียกใช้ Master Report แทนตารางเดิม
        if any(p['history'] for p in st.session_state.players.values()):
            df_report = generate_master_report(st.session_state.players)
            if not df_report.empty:
                # [NEW] เรียกใช้ Master Report (แก้ Error formatting)
        if any(p['history'] for p in st.session_state.players.values()):
            df_report = generate_master_report(st.session_state.players)
            if not df_report.empty:
                # ใช้ Lambda Function เช็คก่อนว่าค่าเป็นตัวเลขไหม ถ้าใช่ค่อยจัด Format
                st.dataframe(
                    df_report.style.format(lambda x: "{:,.2f}".format(x) if isinstance(x, (int, float)) else str(x)), 
                    height=600, 
                    use_container_width=True
                )
            else:
                st.warning("No data available yet.")
            else:
                st.warning("No data available yet.")
        
        st.divider()
        col1, col2 = st.columns([3, 1])
        ready_count = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        col1.metric("Students Ready", f"{ready_count}/{len(st.session_state.players)}")
        
        if col2.button("⚙️ Setup Next Period", type="primary"):
            st.session_state.game_state = "MARKET_EDIT_RUN"
            st.rerun()

    # --- 3. MARKET EDIT PHASE ---
    elif st.session_state.game_state == "MARKET_EDIT_RUN":
        st.markdown(f"### 🚨 Market Environment: Period {st.session_state.global_period}")
        st.info("Instructor can modify market variables before running the simulation.")
        
        df_mkt = pd.DataFrame({"Variable": MARKET_LABELS, "Value": st.session_state.market_data_list})
        edited_df = st.data_editor(df_mkt, height=600, use_container_width=True)
        
        col1, col2 = st.columns(2)
        if col1.button("🔙 Back"):
            st.session_state.game_state = "ACTIVE"
            st.rerun()
            
        if col2.button("🧮 RUN SIMULATION", type="primary"):
            st.session_state.market_data_list = edited_df['Value'].tolist()
            calculate_results()
            st.session_state.game_state = "ACTIVE"
            st.rerun()

def render_student_ui():
    if st.session_state.game_state not in ["ACTIVE", "MARKET_EDIT_RUN"]: 
        st.warning("⏳ Waiting for Instructor..."); return
    
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    # SETUP (Only if Manual Init used, Scenario skips this)
    if p['period'] == 1 and p['status'] == 'Pending' and not p['history'] and p['location_code'] == 0:
        st.info("👋 Welcome! Please set up your store.")
        n = st.text_input("Store Name", p['shop_name'])
        l = st.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Start") and l!=0: 
            p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return
    elif p['period'] == 1 and p['status'] == 'Pending' and not p['history'] and p['location_code'] != 0:
        # Scenario Auto-Start
        st.success(f"🏪 Welcome! You are managing: {p['shop_name']}")
        if st.button("Enter Store"): p['status']='Thinking'; st.rerun()
        return

    st.markdown(f"### 🏥 {p['shop_name']} (Period {p['period']})")
    
    tab1, tab2 = st.tabs(["📝 Decisions", "📊 Financial Reports"])
    
    with tab1:
        if p['status'] == 'Submitted':
            st.success("Decisions Submitted.")
            if st.button("Edit"): p['status']='Thinking'; st.rerun()
        else:
            df = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            ed = st.data_editor(df, hide_index=True, height=500)
            if st.button("Submit", type="primary"):
                p['inputs'] = ed['Value'].tolist(); p['status'] = 'Submitted'; st.rerun()
                
    with tab2:
        if not p['history']: st.info("No reports yet."); return
        last = p['history'][-1]
        
        t1, t2, t3, t4 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow", "Lilly Benchmark"])
        
        with t1:
            st.markdown(f"""
            | Item | Amount |
            |---|---|
            | **Total Revenue** | **${last['total_rev']:,.0f}** |
            | Cost of Goods Sold | (${last['total_cogs']:,.0f}) |
            | **Gross Margin** | **${last['gross_margin']:,.0f}** |
            | Expenses (Wages, Rent, etc) | (${last['exp_wages'] + last['exp_rent'] + last['exp_promo'] + last['exp_util'] + last['exp_mgr'] + last['exp_bad_debt'] + last['exp_ben']:,.0f}) |
            | Interest | (${last['exp_interest'] - last['inc_interest']:,.0f}) |
            | **NET PROFIT** | **${last['net_profit']:,.0f}** |
            """)
            
        with t2:
            st.markdown(f"""
            **Assets**: Cash ${last['bs_cash']:,.0f} | Inventory ${last['bs_inv_rx'] + last['bs_inv_otc']:,.0f} | Fixed ${last['bs_fixed']:,.0f}
            **Liabilities**: A/P ${last['bs_ap']:,.0f} | Loans ${last['bs_lt_debt'] + last['bs_notes']:,.0f}
            **Equity**: ${last['bs_equity']:,.0f}
            """)
            
        with t3:
            st.markdown(f"Start Cash: ${last['cf_start']:,.0f} -> End Cash: ${last['cf_end']:,.0f} (Change: ${last['cf_end'] - last['cf_start']:,.0f})")
            
        with t4:
            c1, c2, c3 = st.columns(3)
            c1.metric("Gross Margin", f"{last['kpi_gm_pct']:.1f}%", f"{last['kpi_gm_pct'] - LILLY_BENCHMARKS['Gross Margin %']:.1f}%")
            c2.metric("Net Profit", f"{last['kpi_np_pct']:.1f}%", f"{last['kpi_np_pct'] - LILLY_BENCHMARKS['Net Profit %']:.1f}%")
            c3.metric("Payroll", f"{last['kpi_payroll_pct']:.1f}%", f"{last['kpi_payroll_pct'] - LILLY_BENCHMARKS['Payroll Expenses %']:.1f}%", delta_color="inverse")

# ROUTER
role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Pwd", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()

