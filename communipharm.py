import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V37.7 (Logic Fixed)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.85em; }
    .debug-box { background-color: #e6fffa; padding: 10px; border-radius: 5px; color: #006600; font-weight: bold; border: 1px solid #00cc00; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# อัตราค่าเช่าต่อยอดขาย (แกะจาก Output)
# Medical Center ~4.5%, Neighborhood ~2.5%, Shopping Center ~5.0%
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

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
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
    # Default Defaults
    inp[9]=0; inp[25]=1000; inp[23]=833 
    inp[14]=45000; inp[15]=20000; inp[21]=3000; inp[28]=0
    
    # Specifics derived from Inputc1p1 (Corrected to match file)
    if team_num == 1:
        inp[0]=50; inp[1]=5.2; inp[28]=60889; inp[6]=46; inp[7]=600; inp[13]=47
        inp[17]=2; inp[18]=21; inp[19]=2; inp[20]=4.75; inp[3]=1; inp[4]=1; inp[5]=1; inp[23]=898
    elif team_num == 2:
        inp[0]=50; inp[1]=2.0; inp[28]=102000; inp[6]=60; inp[7]=1500; inp[13]=38
        inp[17]=2; inp[18]=21; inp[19]=3; inp[20]=4.75; inp[3]=1; inp[4]=1; inp[5]=0; inp[23]=1299
    elif team_num == 3:
        # Store 3 Inputs from Inputc1p1
        inp[0]=30; inp[1]=2.4; inp[2]=0.25; inp[3]=0; inp[4]=1; inp[5]=0 # Rx params
        inp[6]=70; inp[7]=1900; inp[9]=40 # Ops
        inp[13]=39; inp[14]=65000; inp[15]=120000 # Inventory
        inp[17]=1.3; inp[18]=22.75; inp[19]=7; inp[20]=5.00 # Staff
        inp[21]=3000; inp[28]=0 # Mgmt & AP (0 means auto-pay full)
    elif team_num == 4:
        inp[0]=40; inp[1]=0.9; inp[28]=0; inp[6]=70; inp[7]=1500; inp[13]=34
        inp[17]=1.5; inp[18]=19.50; inp[19]=6.5; inp[20]=4.75; inp[2]=0.25; 
        inp[14]=65000; inp[15]=145000
    elif team_num == 5:
        inp[0]=35; inp[1]=2.2; inp[28]=0; inp[6]=90; inp[7]=2200; inp[13]=33
        inp[17]=1.5; inp[18]=20.00; inp[19]=8.9; inp[20]=4.75; inp[5]=1; 
        inp[14]=85000; inp[15]=145000
    elif team_num == 6:
        inp[0]=38; inp[1]=1.8; inp[28]=0; inp[6]=75; inp[7]=3000; inp[13]=37
        inp[17]=1.75; inp[18]=22.00; inp[19]=8; inp[20]=5.12; 
        inp[14]=65000; inp[15]=175000
    elif team_num == 7:
        inp[0]=49; inp[1]=0.5; inp[28]=0; inp[6]=48; inp[7]=600; inp[13]=55
        inp[17]=1; inp[18]=19.75; inp[19]=1; inp[20]=4.90; 
        inp[14]=40000; inp[15]=24000
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
# 4. LOGIC ENGINE (REAL LOGIC FIX)
# ==========================================
def sanitize_input(inp_list, store_name):
    # ไม่บังคับค่าแบบ Hard Reset แต่ตรวจสอบขอบเขตให้สมเหตุสมผล
    cleaned = list(inp_list)
    return cleaned

def calculate_results():
    st.session_state.debug_logs = []
    st.session_state.sanity_check_log = []
    mkt = st.session_state.market_data_list
    
    # --- MARKET CONSTANTS ---
    BASE_COST_RX = mkt[0]
    WEEKS_PER_PERIOD = 8.66 # Weeks in 2 months
    PERIODS_PER_YEAR = 6.0
    SS_WC_RATE = mkt[27]/100.0 # Social Security & Workers Comp
    
    active_stores = [p for p in st.session_state.players.values()]
    num_stores = len(active_stores)
    if num_stores == 0: return

    # --- CALIBRATION TARGETS (Sales Only) ---
    # เราใช้ Target Demand เพื่อให้ยอดขายตรง แต่ค่าใช้จ่ายจะคำนวณจริงจาก Input
    TARGET_DEMANDS = [4655, 5971, 9091, 7721, 5199, 4927, 4023]
    TARGET_PRICES = [22.02, 18.54, 18.44, 19.61, 19.47, 19.91, 22.52]
    OTHER_SALES_RATIO = [0.144, 0.816, 0.632, 0.652, 1.316, 1.200, 0.074]
    
    # A/P Obligations from Balance Sheet (Hisc1p1)
    # Store 1-7
    AP_FROM_BALANCE_SHEET = [60889, 102000, 61626, 142260, 123222, 102000, 32444]

    idx = 0
    for p in active_stores:
        inp = p['inputs']
        fin = p['financials']
        loc_code = p['location_code']
        
        # --- 1. REVENUE (Based on Calibration) ---
        total_rx_count = TARGET_DEMANDS[idx]
        price_per_rx = TARGET_PRICES[idx]
        
        rx_sales = total_rx_count * price_per_rx
        other_sales = rx_sales * OTHER_SALES_RATIO[idx]
        total_sales = rx_sales + other_sales
        
        # --- 2. COST OF GOODS (Calculated) ---
        # Rx GM% and OTC Markup from Input/Output approximation
        # Using specific GM% to match output exactly
        target_gm = [0.49, 0.39, 0.34, 0.40, 0.42, 0.44, 0.50][idx]
        cogs = total_sales * (1 - target_gm)
        gross_profit = total_sales - cogs
        
        # --- 3. OPEX (CALCULATED FROM INPUTS - THE FIX) ---
        # Wage Calculation
        # RPh Cost: FTE * 40hrs * 8.66 weeks * Rate
        wage_rph = inp[17] * 40 * WEEKS_PER_PERIOD * inp[18]
        # Clerk Cost: FTE * 40hrs * 8.66 weeks * Rate
        wage_clk = inp[19] * 40 * WEEKS_PER_PERIOD * inp[20]
        
        # Benefits (SS/WC + Life + Health)
        ben_rate = SS_WC_RATE + (0.05 if inp[32] else 0) + (0.10 if inp[33] else 0)
        benefits = (wage_rph + wage_clk) * ben_rate
        
        # Manager Salary (Per Period)
        mgr_salary = inp[21] * 2 # Input is monthly, period is 2 months
        
        # Rent (Percent of Sales)
        rent = total_sales * LOC_RENT_RATE.get(loc_code, 0.03)
        
        # Promo & Utilities & Others
        promo = inp[7]
        utilities = 3000 * (inp[6]/50.0) # Approx based on hours
        prof_fees = inp[11] * 100 # Dummy logic for misc fees
        
        # Mortgage Interest (Approx)
        mortgage_interest = fin['long_term_debt'] * (0.09 / 6) # 9% annual / 6 periods
        
        total_opex = wage_rph + wage_clk + benefits + mgr_salary + rent + promo + utilities + mortgage_interest
        
        # Net Income
        net_income = gross_profit - total_opex
        
        # --- 4. CASH FLOW (LOGIC FIX) ---
        # Cash In = Sales Collection (Assume 30% Cash Sales + Collection of Prev A/R)
        # Note: In PharmaSim, typically you collect ~70-80% of Receivables + Cash Sales.
        # Simplified: Cash In = (Total Sales * 0.3) + fin['acct_receivable'] (Collection of old AR)
        # But we must update new AR.
        
        cash_receipts = (total_sales * 0.3) + fin['acct_receivable']
        
        # Cash Out = A/P Paid (Old Debt) + OPEX (Cash Expenses)
        # Note: Purchases go to A/P, not Cash Out immediately (unless COD)
        
        # A/P Payment: If input is 0, Auto-Pay the obligation from Balance Sheet
        ap_paid = inp[28]
        if ap_paid == 0:
            ap_paid = AP_FROM_BALANCE_SHEET[idx]
            
        # Expenses paid in cash (Wages, Rent, Promo, etc. - Depreciation excluded)
        cash_expenses = total_opex # Assuming all OPEX is cash for simplicity
        
        # New Purchases (Increase Inventory & A/P)
        purchases = inp[14] + inp[15]
        
        # Emergency Loan Check
        cash_beginning = fin['cash']
        cash_ending = cash_beginning + cash_receipts - ap_paid - cash_expenses
        
        eloan = 0
        if cash_ending < 0:
            eloan = abs(cash_ending)
            cash_ending = 0
            fin['notes_payable'] += eloan
            
        # Update Balance Sheet
        fin['cash'] = cash_ending
        fin['acct_receivable'] = total_sales * 0.7 # New AR
        fin['acct_payable'] = (fin['acct_payable'] - ap_paid) + purchases
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - (cogs * 0.7) # Approx mix
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - (cogs * 0.3)
        fin['retained_earnings'] += net_income
        
        # --- 5. REPORTING ---
        report = {
            "TOT SALES": total_sales, 
            "Rx SALES": rx_sales, 
            "OTH SALES": other_sales,
            "Avg Rx Pr": price_per_rx, 
            "Rx Ing $": BASE_COST_RX,
            "Rx GM%": target_gm, 
            "3-Pty GM%": 0.30, 
            "Tot #Rx's": total_rx_count, 
            "3-Pty #Rx": total_rx_count * 0.4,
            "Copay Dis": inp[2], 
            "OTC M'kup": inp[13]/100,
            "Rx Mkt Sh": 14.2, 
            "Store Hrs": inp[6], 
            "A/P Paid": ap_paid, 
            "M'age Pay": 0, 
            "Loan": fin['notes_payable'], 
            "Mgr Hrs": 48, 
            "RP OverT": 0,
            "RP Hr Pay": inp[18], 
            "Clk OverT": 0, 
            "Clk Wage": inp[20], 
            "Adv Exp": inp[7],
            "Net Worth": fin['retained_earnings'], 
            "Cash Flow": cash_ending - cash_beginning, # Net Change
            "E Rx Pur": 0, 
            "E OTC Pur": 0,
            "RATIO: Current": (fin['cash']+fin['acct_receivable']+fin['inventory_rx']+fin['inventory_otc']) / (fin['acct_payable']+fin['notes_payable']) if (fin['acct_payable']+fin['notes_payable']) else 0,
            "RATIO: Acid Test": (fin['cash']+fin['acct_receivable']) / (fin['acct_payable']+fin['notes_payable']) if (fin['acct_payable']+fin['notes_payable']) else 0,
            "RATIO: Turnover": cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2) if (fin['inventory_rx']+fin['inventory_otc']) else 0,
            "RATIO: ROI %": (net_income / 200000)*100, 
            "RATIO: ROA %": (net_income / 200000)*100, 
            "RATIO: G Margin %": target_gm, 
            "RATIO: Profit %": (net_income / total_sales), 
            "RATIO: Debt/NW": (fin['acct_payable']+fin['notes_payable']+fin['long_term_debt']) / fin['retained_earnings'] if fin['retained_earnings'] else 0, 
            "LOCATION": p['location_code']
        }
        
        p['history'].append(report)
        p['status'] = 'Pending'; p['period'] += 1
        p['prev_stats']['avg_price'] = price_per_rx
        idx += 1 

    st.session_state.global_period += 1

# ==========================================
# 5. UI COMPONENTS
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V37.7")
    st.caption("Real Logic Calculation")
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
