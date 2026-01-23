import streamlit as st
import pandas as pd
import numpy as np
import math

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V32 (Enhanced Logic)", layout="wide")

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

# ... (Previous imports and setup)

# ==========================================
# UPDATED WEIGHT CONFIGURATION
# ==========================================
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

# ... (State Management Code remains the same)

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

def get_starting_inputs():
    return [50.0, 3.0, 0.0, 1.0, 1.0, 0.0, 50.0, 1000.0, 50.0, 0.0, 0.0, 0.0, 0.0, 45.0, 40000.0, 20000.0, 1.0, 25.0, 1.0, 10.0, 3000.0, 30.0, 40.0, 60.0, 0.0, 1000.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0]

def initialize_teams(num_teams):
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
        # Enhanced Prev Stats for Logic
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

# ==========================================
# 3. LOGIC ENGINE (MASTER CALCULATION)
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

    # =========================================================================
    # PHASE 1: PREPARATION & HR
    # =========================================================================
    # 1.1 Calculate Average Wage
    total_rph_wage = sum([p['inputs'][18] for p in active_stores])
    avg_rph_wage = total_rph_wage / num_stores if num_stores else 25.0

    # 1.2 Apply Wage Penalty & Process Returns
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

    # =========================================================================
    # PHASE 2: DEMAND & MARKET SHARE (Rx & OTC)
    # =========================================================================
    ranking_data = []
    
    # 2.1 HMO Auction (Winner Takes All)
    hmo_bids = [(p['id'], p['inputs'][35]) for p in active_stores if p['inputs'][35] > 0]
    hmo_winners = []
    if hmo_bids:
        hmo_bids.sort(key=lambda x: x[1])
        min_bid = hmo_bids[0][1]
        hmo_winners = [x[0] for x in hmo_bids if x[1] == min_bid]

    # 2.2 Calculate Raw Factors
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']
        
        rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        # Ad Index
        ad_factor = (inp[7] / MAX_AD_EXP) + (prev.get('ad_index', 1.0) * 0.533)
        p['curr_ad_index'] = min(2.0, (0.84 * ad_factor) - (0.16 * (ad_factor ** 2)))
        
        # Inventory "Level" (Inverse of Turnover, or just raw $)
        # Higher Inventory $ is better for customers (Less stockouts)
        inv_level_rx = fin['inventory_rx'] 
        inv_level_otc = fin['inventory_otc']

        ranking_data.append({
            'id': tid, 'loc': p['location_code'],
            'price': rx_price,
            'past_price': prev.get('avg_price', 15.0),
            'promo': p['curr_ad_index'],
            'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': inv_level_rx, 
            'inv_otc': inv_level_otc,
            'prev_share': prev['mkt_share'],
            'efficiency': prev.get('rx_per_hr', 5.0),
            'otc_markup': inp[13],
            'prev_otc_markup': prev.get('otc_markup', 45.0)
        })
    
    df_comp = pd.DataFrame(ranking_data)
    
    # Helper: Rank to Points
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)
        
    rx_shares = {}; otc_shares = {}
    
    if not df_comp.empty:
        # --- RX RANKING ---
        df_comp['R_Price'] = get_points(df_comp['price'], ascending=True) # Low Price = Good
        df_comp['R_PastPrice'] = get_points(df_comp['past_price'], ascending=True)
        df_comp['R_Promo'] = get_points(df_comp['promo'], ascending=False) # High Index = Good
        df_comp['R_Hours'] = get_points(df_comp['hours'], ascending=False)
        df_comp['R_Delivery'] = get_points(df_comp['delivery'], ascending=False)
        df_comp['R_Records'] = get_points(df_comp['records'], ascending=False)
        df_comp['R_Credit'] = get_points(df_comp['credit'], ascending=False)
        df_comp['R_Inventory'] = get_points(df_comp['inventory'], ascending=False) # High Level = Good
        df_comp['R_Share'] = get_points(df_comp['prev_share'], ascending=False)
        df_comp['R_Eff'] = get_points(df_comp['efficiency'], ascending=False)

        # --- OTC RANKING ---
        df_comp['RO_Markup'] = get_points(df_comp['otc_markup'], ascending=True) # Low Markup = Good
        df_comp['RO_PrevMarkup'] = get_points(df_comp['prev_otc_markup'], ascending=True)
        df_comp['RO_Promo'] = df_comp['R_Promo'] # Reuse Ad Index Rank
        df_comp['RO_Hours'] = df_comp['R_Hours'] # Reuse Hours Rank
        df_comp['RO_Inventory'] = get_points(df_comp['inv_otc'], ascending=False)
        df_comp['RO_RxShare'] = df_comp['R_Share'] # OTC relies on Rx Share Rank

    # 2.3 Calculate Final Shares (Rx and OTC separate)
    total_rx_score = 0; total_otc_score = 0
    rx_scores = {}; otc_scores = {}

    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        
        # --- Rx Score ---
        w_rx = rx_w_df.set_index("Factor")[loc_name]
        score_rx = (row['R_Price'] * w_rx['Price']) + (row['R_PastPrice'] * w_rx['PastPrice']) + \
                   (row['R_Promo'] * w_rx['Promo']) + (row['R_Hours'] * w_rx['Hours']) + \
                   (row['R_Delivery'] * w_rx['Delivery']) + (row['R_Records'] * w_rx['Records']) + \
                   (row['R_Credit'] * w_rx['Credit']) + (row['R_Inventory'] * w_rx['Inventory']) + \
                   (row['R_Share'] * w_rx['MktShare']) + (row['R_Eff'] * w_rx['Efficiency'])
        
        # Benefit Bonus (Service)
        if st.session_state.players[tid]['inputs'][33]: score_rx *= 1.05
            
        rx_scores[tid] = score_rx
        total_rx_score += score_rx

        # --- OTC Score ---
        w_otc = otc_w_df.set_index("Factor")[loc_name]
        score_otc = (row['RO_Markup'] * w_otc['PresMarkup']) + (row['RO_PrevMarkup'] * w_otc['PrevMarkup']) + \
                    (row['RO_Promo'] * w_otc['AdIndex']) + (row['RO_Hours'] * w_otc['Hours']) + \
                    (row['RO_Inventory'] * w_otc['Inventory']) + (row['RO_RxShare'] * w_otc['RxShare'])
        
        otc_scores[tid] = score_otc
        total_otc_score += score_otc

    # Normalize Shares
    for tid in active_stores:
        tid_str = tid['id']
        rx_shares[tid_str] = rx_scores[tid_str] / total_rx_score if total_rx_score > 0 else 1.0/num_stores
        otc_shares[tid_str] = otc_scores[tid_str] / total_otc_score if total_otc_score > 0 else 1.0/num_stores

    # =========================================================================
    # PHASE 3: OPERATIONS
    # =========================================================================
    total_rx_mkt = AVG_RX_VOL * num_stores
    total_otc_mkt = AVG_OTC_VOL * num_stores
    
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']; prev = p['prev_stats']
        
        # Volume Calculation
        my_rx_share = rx_shares.get(tid, 0)
        my_otc_share = otc_shares.get(tid, 0) # Now using calculated OTC share
        
        base_rx_vol = total_rx_mkt * my_rx_share
        hmo_vol = (200 / len(hmo_winners)) if tid in hmo_winners else 0
        total_rx_vol = base_rx_vol + hmo_vol
        
        total_otc_sales = (total_otc_mkt * my_otc_share) # $ Sales directly from share
        
        # Revenue
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        total_rx_sales = (base_rx_vol * unit_price) + (hmo_vol * inp[35])
        
        # COGS & Stockout
        cogs_rx_total = total_rx_vol * BASE_COST_RX
        cogs_otc_total = total_otc_sales / (1 + inp[13]/100)
        
        # Stockout Logic (Rx)
        req_inv_rx = cogs_rx_total * (1 + RX_PURCH_INDEX)
        avail_inv_rx = fin['inventory_rx'] + inp[14]
        emer_purch_rx = max(0, req_inv_rx - avail_inv_rx)
        
        # Stockout Logic (OTC)
        req_inv_otc = cogs_otc_total * (1 + OTC_PURCH_INDEX)
        avail_inv_otc = fin['inventory_otc'] + inp[15]
        emer_purch_otc = max(0, req_inv_otc - avail_inv_otc)
        
        # Slippage
        mgr_control_factor = 1.0 + (inp[21]/100.0)
        actual_slippage = (total_rx_sales + total_otc_sales) * SLIPPAGE_RATE * mgr_control_factor
        cogs_rx_total += (actual_slippage * 0.5)
        cogs_otc_total += (actual_slippage * 0.5)

        # Overtime (Simple RPh)
        std_rate = 10.0 if inp[4] else 12.5
        capacity_rx = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD) * std_rate
        rph_ot_hours = max(0, (total_rx_vol - capacity_rx) / std_rate)
        
        # =========================================================================
        # PHASE 4: FINANCIALS
        # =========================================================================
        # Expenses
        wage_rph = (p['eff_rph'] * 40 * WEEKS_PER_PERIOD * inp[18]) + (rph_ot_hours * inp[18] * 1.5)
        wage_clk = (p['eff_clk'] * 40 * WEEKS_PER_PERIOD * inp[20])
        total_wages = wage_rph + wage_clk
        ben_cost = total_wages * (BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0))
        
        rent = (total_rx_sales + total_otc_sales) * FIXED_RENT_RATE.get(p['location_code'], 0.03)
        bad_debt = ((total_rx_sales + total_otc_sales) * 0.01) + inp[29] # Simplified 1% bad debt + writeoff
        
        total_opex = total_wages + ben_cost + rent + inp[7] + (inp[20]*3) + bad_debt + inp[23] + 3000
        
        gm = (total_rx_sales + total_otc_sales) - (cogs_rx_total + cogs_otc_total)
        intr_exp = (fin['long_term_debt'] + fin['notes_payable']) * INT_RATE_LOAN
        intr_inc = (fin['investments'] * CD_RATE)
        
        net_profit = gm - total_opex - intr_exp + intr_inc
        
        # Cash Flow
        cash_start = fin['cash']
        inflow = total_rx_sales + total_otc_sales + intr_inc + inp[30] # Simplified Sales=Cash for now to fix lag complexity
        outflow = inp[28] + emer_purch_rx + emer_purch_otc + total_opex + intr_exp
        fin['cash'] = cash_start + inflow - outflow
        
        # Emergency Loan
        e_loan = 0
        if fin['cash'] < inp[25]:
            e_loan = inp[25] - fin['cash']
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan

        # Balance Sheet Update
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_purch_rx) - cogs_rx_total
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_purch_otc) - cogs_otc_total
        fin['acct_payable'] = (fin['acct_payable'] - inp[28]) + inp[14] + inp[15]
        fin['retained_earnings'] += net_profit
        
        # History
        p['prev_stats'].update({
            'avg_price': unit_price,
            'mkt_share': my_rx_share * 100,
            'otc_markup': inp[13],
            'rx_per_hr': total_rx_vol / (p['eff_rph']*40*WEEKS_PER_PERIOD) if p['eff_rph'] else 0
        })
        
        metrics = {
            "TOT SALES": total_rx_sales + total_otc_sales,
            "Rx SALES": total_rx_sales,
            "OTC SALES": total_otc_sales,
            "Net Profit": net_profit,
            "Cash Flow": fin['cash'] - cash_start,
            "Rx Mkt Sh": my_rx_share * 100,
            "OTC Mkt Sh": my_otc_share * 100,
            "Emerg Loan": e_loan,
            "LOCATION": LOC_MAP[p['location_code']]
        }
        p['history'].append(metrics)
        p['status'] = 'Pending'; p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI COMPONENTS (Standard)
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V32")
    st.caption("Enhanced Logic Engine")
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
            report_data = {}
            first_active = next((p for p in st.session_state.players.values() if p['history']), None)
            
            if first_active:
                metrics_order = list(first_active['history'][-1].keys())
                for tid, p in st.session_state.players.items():
                    if p['history']:
                        last_metrics = p['history'][-1]
                        report_data[p['shop_name']] = [last_metrics.get(m, 0) for m in metrics_order]
                
                df_rep = pd.DataFrame(report_data, index=metrics_order)
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
    
    # 1. SETUP
    if p['period'] == 1 and p['status'] == 'Pending' and not p['history']:
        st.info("👋 Welcome! Please set up your store.")
        c1, c2 = st.columns(2)
        n = c1.text_input("Store Name", p['shop_name'])
        l = c2.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Start Operations") and l!=0: 
            p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return

    # 2. OPERATIONS
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
            st.write(f"**Results from Period {p['period']-1}**")
            # Highlight Key KPIs
            kpis = ["Net Profit", "Cash Flow", "Rx SALES", "Emerg Loan"]
            cols = st.columns(len(kpis))
            for i, m in enumerate(kpis):
                val = last.get(m, 0)
                cols[i].metric(m, f"${val:,.0f}")
            st.json(last)
        else:
            st.info("No results yet. Submit decisions for Period 1.")

# ROUTER
role = st.sidebar.selectbox("User Role", ["Student", "Instructor"])
if role == "Instructor":
    if st.sidebar.text_input("Password", type="password") == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()

