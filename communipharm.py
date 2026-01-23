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
    MUTUAL_FUND_PRICE = mkt[15]
    INFLATION = mkt[19]/100.0
    RX_PURCH_INDEX = mkt[20]/100.0; OTC_PURCH_INDEX = mkt[21]/100.0
    SAVINGS_RATE = mkt[22]/100.0; MF_NEXT = mkt[23]
    CD_RATE = mkt[24]/100.0; SALES_PER_CLERK = mkt[25]
    BENEFIT_PCT = mkt[27]/100.0
    
    store_list = [p for p in st.session_state.players.values()]
    active_stores = [p for p in store_list if p['location_code'] != 0]
    num_stores = len(active_stores)
    if num_stores == 0: return

    # Update Fixed Expenses with Inflation
    FIXED_RENT_RATE = {k: v * (1 + INFLATION) for k, v in LOC_RENT_RATE.items()}

    # =========================================================================
    # PHASE 1: PREPARATION & HR (Wage Penalty & Returns)
    # =========================================================================
    
    # 1.1 Calculate Average Wage in City (Logic: Weighted Average)
    total_rph_wage = 0; total_clk_wage = 0; count_stores = 0
    for p in active_stores:
        inp = p['inputs']
        # Wage + Benefit Cost
        ben_cost_factor = 1 + BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        total_rph_wage += inp[17] * inp[18] * ben_cost_factor
        total_clk_wage += inp[19] * inp[20] * ben_cost_factor
        count_stores += 1
    
    avg_rph_wage = total_rph_wage / count_stores if count_stores else 25.0
    avg_clk_wage = total_clk_wage / count_stores if count_stores else 10.0

    # 1.2 Apply Wage Penalty & Process Returns
    for p in active_stores:
        inp = p['inputs']; fin = p['financials']
        
        # --- Returns Logic ---
        # Deduct returns from Inventory immediately and get 80% Cash Back
        fin['inventory_rx'] = max(0, fin['inventory_rx'] - inp[26])
        fin['inventory_otc'] = max(0, fin['inventory_otc'] - inp[27])
        fin['cash'] += (inp[26] * 0.8) + (inp[27] * 0.8)

        # --- HR Penalty Logic ---
        ben_cost_factor = 1 + BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        my_rph_real_wage = inp[18] * ben_cost_factor
        my_clk_real_wage = inp[20] * ben_cost_factor
        
        # If wage < 90% of avg, lose 1 FTE
        p['eff_rph'] = max(0, inp[17] - 1.0) if my_rph_real_wage < (0.9 * avg_rph_wage) else inp[17]
        p['eff_clk'] = max(0, inp[19] - 1.0) if my_clk_real_wage < (0.9 * avg_clk_wage) else inp[19]
        
        p['wage_penalty'] = (inp[17] - p['eff_rph']) > 0 # Flag for report

    # =========================================================================
    # PHASE 2: DEMAND & MARKET SHARE (Enhanced Scoring)
    # =========================================================================
    
    ranking_data = []
    
    # 2.1 HMO Auction Logic (Winner Takes All)
    # Find lowest non-zero bid
    hmo_bids = [(p['id'], p['inputs'][35]) for p in active_stores if p['inputs'][35] > 0]
    hmo_winner_id = None
    if hmo_bids:
        # Sort by price ascending
        hmo_bids.sort(key=lambda x: x[1])
        min_bid = hmo_bids[0][1]
        # Check for ties
        winners = [x[0] for x in hmo_bids if x[1] == min_bid]
        # Tie-breaker: Random or Split? Let's Split for fairness
        hmo_winners = winners

    # 2.2 Calculate Factors
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']
        
        # Price Calculation
        rx_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        # Ad Index (Hyperbolic Formula)
        # Ad Factor = (Ad $ / Max Ad) + Past Index * 0.533
        ad_factor = (inp[7] / MAX_AD_EXP) + (prev.get('ad_index', 1.0) * 0.533)
        ad_factor = min(2.0, ad_factor) # Cap at 2.0
        curr_ad_index = (0.84 * ad_factor) - (0.16 * (ad_factor ** 2))
        p['curr_ad_index'] = curr_ad_index # Store for next period history
        
        # Inventory Depth (Lower ratio is better)
        # Ratio = Past COGS / Past Avg Inv
        inv_ratio_rx = prev['cogs_rx'] / prev['avg_inv_rx'] if prev['avg_inv_rx'] > 0 else 10.0
        
        ranking_data.append({
            'id': tid, 'loc': p['location_code'],
            'price': rx_price,
            'promo': curr_ad_index, # Use calculated Index
            'hours': inp[6],
            'delivery': inp[3], 'records': inp[4], 'credit': inp[5],
            'inventory': inv_ratio_rx, # Lower is better
            'prev_share': prev['mkt_share']
        })
    
    df_comp = pd.DataFrame(ranking_data)
    
    # Helper: Convert Rank to Points
    def get_points(series, ascending):
        return (num_stores + 1) - series.rank(method='min', ascending=ascending)
        
    if not df_comp.empty:
        df_comp['R_Price'] = get_points(df_comp['price'], ascending=True)
        df_comp['R_Promo'] = get_points(df_comp['promo'], ascending=False)
        df_comp['R_Hours'] = get_points(df_comp['hours'], ascending=False) # Banded logic simplified to rank
        df_comp['R_Delivery'] = get_points(df_comp['delivery'], ascending=False)
        df_comp['R_Records'] = get_points(df_comp['records'], ascending=False)
        df_comp['R_Credit'] = get_points(df_comp['credit'], ascending=False)
        df_comp['R_Inventory'] = get_points(df_comp['inventory'], ascending=True) # Lower ratio = Better (Full Stock)
        df_comp['R_Share'] = get_points(df_comp['prev_share'], ascending=False)

    # Calculate Weighted Scores
    rx_shares = {}; total_market_score = 0
    
    for idx, row in df_comp.iterrows():
        tid = row['id']; loc_name = LOC_MAP[row['loc']]
        w = rx_w_df.set_index("Factor")[loc_name]
        
        # Sum(Rank * Weight)
        score = (row['R_Price'] * w['Price']) + (row['R_Promo'] * w['Promo']) + \
                (row['R_Hours'] * w['Hours']) + (row['R_Delivery'] * w['Delivery']) + \
                (row['R_Records'] * w['Records']) + (row['R_Credit'] * w['Credit']) + \
                (row['R_Inventory'] * w['Inventory']) + (row['R_Share'] * w['MktShare'])
        
        # Service Bonus (Benefits logic - Happy employees = Good Service)
        p_obj = st.session_state.players[tid]
        if p_obj['inputs'][33] or p_obj['inputs'][34]: 
            score *= 1.05 # 5% Bonus score for benefits
            
        rx_shares[tid] = score
        total_market_score += score

    # Final Share Normalization
    for tid in rx_shares:
        rx_shares[tid] = rx_shares[tid] / total_market_score if total_market_score > 0 else 1.0/num_stores

    # =========================================================================
    # PHASE 3: OPERATIONS (Inv, Slippage, OT)
    # =========================================================================
    total_rx_mkt = AVG_RX_VOL * num_stores
    total_otc_mkt = AVG_OTC_VOL * num_stores
    
    for p in active_stores:
        tid = p['id']; inp = p['inputs']; fin = p['financials']; prev = p['prev_stats']
        
        # 3.1 Volume & Sales
        my_rx_share = rx_shares.get(tid, 0)
        base_rx_vol = total_rx_mkt * my_rx_share
        
        # Add HMO Volume
        hmo_vol = 0
        if hmo_bids and tid in hmo_winners:
            # Winner gets extra volume (e.g., 200 scripts split among winners)
            hmo_vol = 200 / len(hmo_winners) 
            
        total_rx_vol = base_rx_vol + hmo_vol
        
        # Price
        unit_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] if inp[0] > 10 else (BASE_COST_RX + inp[0]) + inp[1]
        
        # Revenue Breakdown
        # HMO Sales = Vol * Bid Price
        rev_hmo = hmo_vol * inp[35]
        # Normal Sales
        rev_normal = base_rx_vol * unit_price
        
        total_rx_sales = rev_normal + rev_hmo
        
        # OTC Sales (Linked to Rx Traffic + Promo)
        my_otc_share = my_rx_share # Simplified link
        total_otc_sales = total_otc_mkt * my_otc_share
        
        # 3.2 Inventory & Stockouts (Emergency Purchase)
        # COGS Calculation
        cogs_rx_normal = base_rx_vol * BASE_COST_RX
        cogs_rx_hmo = hmo_vol * BASE_COST_RX
        cogs_rx_total = cogs_rx_normal + cogs_rx_hmo
        
        cogs_otc_total = total_otc_sales / (1 + inp[13]/100)
        
        # Stockout Logic Rx
        # Required Inv = COGS * (1 + Index)
        req_inv_rx = cogs_rx_total * (1 + RX_PURCH_INDEX)
        avail_inv_rx = fin['inventory_rx'] + inp[14] # Beg + Purch
        
        emer_purch_rx = 0
        if avail_inv_rx < req_inv_rx:
            missing = req_inv_rx - avail_inv_rx
            emer_purch_rx = missing 
            # Emergency cost is higher (e.g., 10% premium)
            # We add it to purchases but it hits cash flow harder later
        
        # Stockout Logic OTC
        req_inv_otc = cogs_otc_total * (1 + OTC_PURCH_INDEX)
        avail_inv_otc = fin['inventory_otc'] + inp[15]
        emer_purch_otc = 0
        if avail_inv_otc < req_inv_otc:
            emer_purch_otc = req_inv_otc - avail_inv_otc
            
        # 3.3 Slippage (Manager Time)
        # Logic: If Mgr Time < 20% on Pro, Slippage is normal. If high Pro time, Slippage increases.
        # Formula: Actual Slippage = Base + (Time_Rx * Penalty)
        # Using simplified logic:
        mgr_control_factor = 1.0 + (inp[21]/100.0) # If 100% Rx time -> Factor 2.0 (Double Slippage)
        actual_slippage_amt = (total_rx_sales + total_otc_sales) * SLIPPAGE_RATE * mgr_control_factor
        
        # Update COGS with Slippage (Lost Inventory)
        cogs_otc_total += (actual_slippage_amt * 0.5) # Assume half slippage is Rx, half OTC? Usually OTC is higher.
        cogs_rx_total += (actual_slippage_amt * 0.5)
        
        # 3.4 Overtime Calculation
        hrs_open = inp[6] * WEEKS_PER_PERIOD
        
        # Pharmacist OT
        # Capacity = (FTE * 40 * Weeks) + (Mgr Hrs - Mgr Rx Time?)
        # Let's assume Mgr Hrs are totally added to capacity
        mgr_avail_hrs = inp[22] * WEEKS_PER_PERIOD * (1 - inp[21]/100) # Only non-Rx time manages? No, Manual says Pro time counts for production
        mgr_pro_hrs = inp[22] * WEEKS_PER_PERIOD * (inp[21]/100)
        
        staff_hrs = p['eff_rph'] * 40 * WEEKS_PER_PERIOD
        total_rph_hrs = staff_hrs + mgr_pro_hrs
        
        # Standard: 10/hr (Records) vs 12.5/hr (No Records)
        std_rate = 10.0 if inp[4] else 12.5
        capacity_rx = total_rph_hrs * std_rate
        
        rph_ot_hours = 0
        if total_rx_vol > capacity_rx:
            # Need extra hours
            needed_hrs = (total_rx_vol - capacity_rx) / std_rate
            rph_ot_hours = needed_hrs
            
        # Clerk OT
        # Based on Sales $ / Clerk / Hour
        needed_clk_hrs = (total_rx_sales + total_otc_sales) / SALES_PER_CLERK
        avail_clk_hrs = p['eff_clk'] * 40 * WEEKS_PER_PERIOD
        clk_ot_hours = max(0, needed_clk_hrs - avail_clk_hrs)
        
        # =========================================================================
        # PHASE 4: FINANCIALS (The Bottom Line)
        # =========================================================================
        
        # Expenses
        # 1. Wages
        # Base
        wage_rph_base = p['eff_rph'] * 40 * WEEKS_PER_PERIOD * inp[18]
        wage_clk_base = p['eff_clk'] * 40 * WEEKS_PER_PERIOD * inp[20]
        # OT (1.5x)
        wage_rph_ot = rph_ot_hours * inp[18] * 1.5
        wage_clk_ot = clk_ot_hours * inp[20] * 1.5
        # Benefits
        ben_factor = BENEFIT_PCT + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        total_wages = (wage_rph_base + wage_clk_base + wage_rph_ot + wage_clk_ot)
        cost_benefits = total_wages * ben_factor
        
        # 2. Ops
        rent = (total_rx_sales + total_otc_sales) * LOC_RENT_RATE.get(p['location_code'], 0.03)
        utilities = 3000 * (1+INFLATION) # Example base
        promo = inp[7]
        mgr_sal = inp[20] * 3 # 3 Months? Manual says /mo. Let's assume period = 3 months
        
        # 3. Bad Debt
        # Credit Sales % based on location
        loc_credit_pct = {1: mkt[5], 2: mkt[6], 3: mkt[7]}.get(p['location_code'], 20.0) / 100.0
        credit_sales = (total_rx_sales + total_otc_sales) * loc_credit_pct
        
        # Economic Bad Debt Risk (Randomized small chance)
        bad_debt_expense = 0
        if np.random.random() < 0.05: # 5% chance of bad debt event
            bad_debt_expense = credit_sales * 0.10 # Lose 10% of credit sales
            
        # Write off user specified debt
        bad_debt_expense += inp[29] 
        
        total_opex = total_wages + cost_benefits + rent + utilities + promo + mgr_sal + bad_debt_expense + inp[23] # Mortgage
        
        # Gross Margin
        gm = (total_rx_sales + total_otc_sales) - (cogs_rx_total + cogs_otc_total)
        
        # Interest
        # Loan Interest
        intr_exp = (fin['long_term_debt'] + fin['notes_payable']) * INT_RATE_LOAN
        # Investment Income
        intr_inc = (fin['investments'] * CD_RATE) + (fin['cash'] * SAVINGS_RATE if fin['cash']>0 else 0)
        
        net_profit = gm - total_opex - intr_exp + intr_inc
        
        # --- Cash Flow Logic ---
        cash_start = fin['cash']
        
        # 1. Inflows
        # Cash Sales (Immediate) + Credit Collections (Lagged) + 3rd Party (Lagged)
        # Current Cash %
        pct_cash_sales = 1.0 - loc_credit_pct - (PCT_3RD_PARTY if inp[34] else 0) # Simplify
        cash_in_sales = (total_rx_sales + total_otc_sales) * pct_cash_sales
        
        # Receivables Collection (from previous period)
        cash_in_ar = fin['acct_receivable'] * (1 - LAG_AR) # Collect %
        cash_in_3rd = fin['acct_receivable_3rd'] * (1 - LAG_3RD_PARTY)
        
        # Debt Payment collected
        cash_in_bad_debt = inp[30]
        
        total_inflow = cash_in_sales + cash_in_ar + cash_in_3rd + cash_in_bad_debt + intr_inc
        
        # 2. Outflows
        # A/P Payment (User decision)
        pay_ap = inp[28]
        # Emergency Purchases (Paid immediately or COD)
        pay_emer = emer_purch_rx + emer_purch_otc
        # Expenses (Wages, Rent, etc - usually paid current)
        pay_opex = total_opex - bad_debt_expense # Bad debt is non-cash
        
        total_outflow = pay_ap + pay_emer + pay_opex + intr_exp
        
        fin['cash'] = cash_start + total_inflow - total_outflow
        
        # 3. Update Balance Sheet
        # A/R Update
        new_ar = credit_sales
        fin['acct_receivable'] = (fin['acct_receivable'] * LAG_AR) + new_ar
        
        new_3rd = total_rx_sales * PCT_3RD_PARTY
        fin['acct_receivable_3rd'] = (fin['acct_receivable_3rd'] * LAG_3RD_PARTY) + new_3rd
        
        # Inventory Update
        # End = Beg + Purch + Emer - COGS
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14] + emer_purch_rx) - cogs_rx_total
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15] + emer_purch_otc) - cogs_otc_total
        
        # A/P Update
        # New Purchases added to A/P
        fin['acct_payable'] = (fin['acct_payable'] - pay_ap) + inp[14] + inp[15]
        
        # 4. Emergency Loan Check
        e_loan = 0
        min_cash = inp[25]
        if fin['cash'] < min_cash:
            deficit = min_cash - fin['cash']
            e_loan = deficit
            fin['notes_payable'] += e_loan
            fin['cash'] += e_loan # Bring up to min
            # Penalty Interest next time
            
        fin['retained_earnings'] += net_profit
        
        # Save Stats for Next Period
        p['prev_stats']['avg_inv_rx'] = (fin['inventory_rx'] + prev['avg_inv_rx']) / 2
        p['prev_stats']['cogs_rx'] = cogs_rx_total
        p['prev_stats']['ad_index'] = p['curr_ad_index']
        p['prev_stats']['mkt_share'] = my_rx_share * 100
        
        # --- REPORTING ---
        metrics = {
            "TOT SALES": total_rx_sales + total_otc_sales,
            "Rx SALES": total_rx_sales,
            "HMO Vol": hmo_vol,
            "Net Profit": net_profit,
            "Gross Marg": gm,
            "Cash Flow": fin['cash'] - cash_start,
            "Cash End": fin['cash'],
            "Emerg Loan": e_loan,
            "Emerg Purch": emer_purch_rx + emer_purch_otc,
            "Rx Stockout": req_inv_rx > avail_inv_rx,
            "Wage Pen": p['wage_penalty'],
            "RPh OT Hrs": rph_ot_hours,
            "Clk OT Hrs": clk_ot_hours,
            "Slippage $": actual_slippage_amt,
            "Mkt Share": my_rx_share * 100,
            "LOCATION": LOC_MAP[p['location_code']]
        }
        p['history'].append(metrics)
        p['status'] = 'Pending'
        p['period'] += 1

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
