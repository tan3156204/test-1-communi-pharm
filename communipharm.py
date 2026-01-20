import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V28 (Full Config)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .step-title { color: #1565c0; font-size: 1.2rem; font-weight: bold; }
    .report-title { font-size: 1.5rem; font-weight: bold; text-align: center; color: #2c3e50; margin-bottom: 20px; }
    .report-section { background-color: #ffffff; padding: 15px; border: 1px solid #ddd; margin-bottom: 15px; }
    .report-header { font-weight: bold; border-bottom: 2px solid #2c3e50; margin-bottom: 10px; padding-bottom: 5px; }
    .fin-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #eee; }
    .fin-value { font-family: 'Courier New', monospace; font-weight: bold; }
    .double-underline { border-bottom: 3px double #000; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white;}
    .badge-pending { background-color: #9e9e9e; }
    .badge-submitted { background-color: #4caf50; }
    .hmo-badge { background-color: #d1c4e9; color: #512da8; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8em; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0=No, 1=Yes)", "5. Pt. Records (0=No, 1=Yes)", "6. Credit (0=No, 1=Yes)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($)",
    "19. # Clerks", "20. Clerk Wage ($)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0=No, 1=Yes)",
    "34. Ben: Health (0=No, 1=Yes)", "35. 3rd Party (0=No, 1=Yes)", "36. HMO Bid ($)"
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
# 2. STATE MANAGEMENT & DEFAULTS
# ==========================================
# Initialize Instructor Data (Default Values from Manual/PDF)
DEFAULT_ENV = {
    "Number of Next Period": 2,
    "Average Ingredient Cost ($)": 11.23,
    "Average Copay Allowed ($)": 5.00,
    "Average Third-Party Fee ($)": 4.50,
    "Percent Market Rx’s 3rd-Party (%)": 25.0,
    "Maximum Promotion Expenditure ($)": 1500.0,
    "% Sales A/R Store Type 1 (%)": 10.0,
    "% A/R Sales Store Type 2 (%)": 20.0,
    "% A/R Sales Store Type 3 (%)": 5.0,
    "Interest Rate for Period (%)": 2.5,
    "Average Number Rx Per Store (#)": 6000,
    "Average Other Sales Per Store ($)": 48000,
    "Gross Margin Slippage Rate (%)": 0.10,
    "Number Periods per Year (#)": 6,
    "Third-Party Lag in Payment (%)": 14.40,
    "A/R Lag in Payment (%)": 11.20,
    "Mutual Fund Transaction Price ($)": 10.0,
    "Closing Date Month": 3, "Day": 31, "Year": 1990,
    "Current Inflation Rate (%)": 1.0,
    "Stockout Rx Inventory Index": 50.0,
    "Stockout Other Inventory Index": 50.0,
    "Pass Book Savings Rate (%)": 1.5,
    "Mutual Fund Next Period ($)": 10.5,
    "Interest Rate on CD’s (%)": 2.0,
    "Average Dollar Sales/Clerk ($)": 25.30,
    "Maximum Price for Rx’s ($)": 100.0,
    "SS & WC as % of Salary & Wages (%)": 8.5
}

if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP_STEP_1"
    st.session_state.global_period = 1
    st.session_state.players = {}

if 'instructor_env' not in st.session_state:
    st.session_state.instructor_env = DEFAULT_ENV.copy()
if 'rx_weights_df' not in st.session_state:
    st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state:
    st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

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
        st.session_state.players[team_id] = {
            'id': team_id, 'shop_name': f"Store {i}", 'location_code': 0, 'status': 'Pending',
            'period': 1, 'inputs': get_starting_inputs(), 'financials': financials,
            'prev_stats': { 'avg_price': 15.00, 'mkt_share': 100.0/num_teams, 'rx_per_hr': 5.0, 'otc_markup': 45.0 },
            'history': [] 
        }

# ==========================================
# 3. LOGIC ENGINE (Updated with Env Variables)
# ==========================================
def calculate_results(store_list, rx_w_df, otc_w_df, env):
    # Variables from Environment
    base_cost_rx = env["Average Ingredient Cost ($)"]
    const_fee = env["Average Third-Party Fee ($)"] # Proxy for base fee? No, manual says this is 3rd party. Using as constant fee base for now.
    # Actually, Manual implies Ingredient Cost is base.
    
    # 1. HMO Bidding
    hmo_bids = {p['id']: p['p']['inputs'][35] for p in store_list if p['p']['inputs'][35] > 0}
    hmo_winner_id = min(hmo_bids, key=hmo_bids.get) if hmo_bids else None

    # 2. Ranking
    data = []
    loc_code = store_list[0]['p']['location_code']
    loc_name = LOC_MAP[loc_code]

    for p in store_list:
        tid = p['id']; inp = p['p']['inputs']; prev = p['p']['prev_stats']; fin = p['p']['financials']
        curr_price = (base_cost_rx * (1 + inp[0]/100)) + inp[1] + 2.90 # 2.90 is fixed constant fee in model
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        data.append({
            'id': tid, 'price_past': prev['avg_price'], 'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3], 'records': inp[4], 'credit': inp[5], 
            'inventory': inv_level, 'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr'],
            'otc_markup_past': prev.get('otc_markup', 45.0), 'otc_markup_pres': inp[13], 'advertising': inp[7]
        })
    df_comp = pd.DataFrame(data)

    # Weights
    rx_weights = rx_w_df.set_index("Factor")[loc_name].values
    otc_weights = otc_w_df.set_index("Factor")[loc_name].values

    # Scoring
    df_rx_ranks = pd.DataFrame({'id': df_comp['id']})
    def get_rank(series, ascending): return series.rank(method='min', ascending=ascending)
    df_rx_ranks['r0'] = get_rank(df_comp['price_past'], False); df_rx_ranks['r1'] = get_rank(df_comp['price_pres'], False)
    cols = ['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']
    for i, col in enumerate(cols): df_rx_ranks[f'r{i+2}'] = get_rank(df_comp[col], True)
    
    rx_scores = {row['id']: sum(row[f'r{i}'] * rx_weights[i] for i in range(10)) for index, row in df_rx_ranks.iterrows()}
    if hmo_winner_id in rx_scores: rx_scores[hmo_winner_id] *= 1.15
    total_rx = sum(rx_scores.values())
    rx_shares = {k: (v/total_rx if total_rx else 0) for k,v in rx_scores.items()}

    df_otc_ranks = pd.DataFrame({'id': df_comp['id']})
    df_otc_ranks['o0'] = get_rank(df_comp['otc_markup_past'], False); df_otc_ranks['o1'] = get_rank(df_comp['otc_markup_pres'], False)
    df_otc_ranks['o2'] = get_rank(df_comp['advertising'], True); df_otc_ranks['o3'] = get_rank(df_comp['hours'], True)
    df_otc_ranks['o4'] = get_rank(df_comp['inventory'], True)
    df_comp['rx_share_result'] = df_comp['id'].map(rx_shares)
    df_otc_ranks['o5'] = get_rank(df_comp['rx_share_result'], True)
    
    otc_scores = {row['id']: sum(row[f'o{i}'] * otc_weights[i] for i in range(6)) for index, row in df_otc_ranks.iterrows()}
    total_otc = sum(otc_scores.values())
    otc_shares = {k: (v/total_otc if total_otc else 0) for k,v in otc_scores.items()}

    # 3. Financials
    # Market Size from ENV
    avg_rx_vol = env["Average Number Rx Per Store (#)"]
    avg_otc_vol = env["Average Other Sales Per Store ($)"]
    base_rx_market = len(store_list) * avg_rx_vol
    base_otc_market_usd = len(store_list) * avg_otc_vol
    
    weeks_per_period = 52 / env["Number Periods per Year (#)"] # e.g. 52/6 = 8.66 weeks? Or hardcoded 13? Let's use 13 for quarterly
    # Manual says "Bimonthly-- 6 periods" -> ~8.6 weeks. But code used 13. Let's adjust to Env.
    # Actually most sims use quarterly logic (13 weeks) but label it bimonthly. I'll stick to 13 to be safe or derived?
    # Let's derive: weeks = 52 / periods
    weeks_actual = 52 / env["Number Periods per Year (#)"]

    for s_data in store_list:
        tid = s_data['id']; p = s_data['p']; inp = p['inputs']; fin = p['financials']
        my_rx_share = rx_shares[tid]; my_otc_share = otc_shares[tid]
        
        rx_count = base_rx_market * my_rx_share
        avg_rx_price = (base_cost_rx*(1+inp[0]/100))+inp[1]+2.90
        rx_sales = rx_count * avg_rx_price
        loc_mult = 1.5 if loc_code == 3 else 1.0
        otc_sales = base_otc_market_usd * loc_mult * my_otc_share
        tot_sales = rx_sales + otc_sales
        
        cost_rx = rx_sales / (1+inp[0]/100); cost_otc = otc_sales / (1+inp[13]/100)
        tot_cogs = cost_rx + cost_otc
        gross_margin = tot_sales - tot_cogs
        
        # Slippage
        slippage = gross_margin * (env["Gross Margin Slippage Rate (%)"] / 100.0)
        gross_margin -= slippage
        
        wages_base = ((inp[17]*inp[18]) + (inp[19]*inp[20])) * inp[6] * weeks_actual
        if inp[6]>40: wages_base *= 1.1
        
        # Benefits (Env Base + Student Selection)
        base_ben = env["SS & WC as % of Salary & Wages (%)"] / 100.0
        if inp[32]==1: base_ben += 0.05
        if inp[33]==1: base_ben += 0.15
        ben_cost = wages_base * base_ben
        
        rent_exp = tot_sales * LOC_RENT_RATE.get(loc_code, 0.0)
        promo_exp = inp[7]; mgr_salary = inp[21]; mortgage = inp[24]
        
        depr = fin['fixed_assets']*0.02
        bad_debt = inp[29]
        int_exp = (fin['long_term_debt']+fin['notes_payable']) * (env["Interest Rate for Period (%)"]/100.0)
        
        total_expenses = wages_base + ben_cost + rent_exp + promo_exp + mgr_salary + mortgage + 3000 + depr + int_exp + bad_debt
        
        # Investment Income
        invest_income = fin['investments'] * (env["Interest Rate on CD’s (%)"]/100.0) # Using CD rate for simplicity
        net_profit = gross_margin - total_expenses + invest_income
        
        # Cash Flow
        fin['investments'] += (inp[9]-inp[11])
        max_rx_ret = fin['inventory_rx']*0.25; max_otc_ret=fin['inventory_otc']*0.25
        act_rx_ret = min(inp[26], max_rx_ret); act_otc_ret = min(inp[27], max_otc_ret)
        
        fin['inventory_rx'] = max(0, fin['inventory_rx']+inp[14]-act_rx_ret-cost_rx)
        fin['inventory_otc'] = max(0, fin['inventory_otc']+inp[15]-act_otc_ret-cost_otc)
        
        cash_in = (tot_sales*0.9) + act_rx_ret + act_otc_ret + inp[11]
        cash_out_ops = wages_base + ben_cost + rent_exp + promo_exp + mgr_salary + mortgage + 3000 + int_exp
        cash_out = cash_out_ops + inp[28] + inp[9] + inp[30]
        
        fin['cash'] += (cash_in - cash_out)
        fin['acct_payable'] += (inp[14]+inp[15]-inp[28])
        fin['acct_receivable'] += (tot_sales*0.1 - bad_debt)
        fin['long_term_debt'] -= inp[30]
        
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 2000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
            penalty = e_loan * 0.20
            net_profit -= penalty; fin['retained_earnings'] -= penalty
            total_expenses += penalty

        fin['retained_earnings'] += net_profit
        
        # Packaging
        nw = fin['retained_earnings']
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        overtime_hrs = max(0, inp[6] - 40)

        p['history'].append({
            "Period": st.session_state.global_period,
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Avg Rx Pr": avg_rx_price, "Rx Ing $": base_cost_rx, 
            "Rx GM%": ((rx_sales-cost_rx)/rx_sales)*100 if rx_sales else 0,
            "3-Pty GM%": 0.0, "Tot #Rx's": rx_count, "3-Pty #Rx": rx_count * (env["Percent Market Rx’s 3rd-Party (%)"]/100.0),
            "Copay Dis": inp[2], "OTC M'kup": inp[13],
            "Rx Mkt Sh": my_rx_share*100, "Store Hrs": inp[6],
            "A/P Paid": inp[28], "M'age Pay": mortgage, "E. Loan": e_loan,
            "Mgr Hrs": inp[22], "RP OverT": overtime_hrs, "RP Hr Pay": inp[17],
            "Clk OverT": overtime_hrs, "Clk Wage": inp[19], "Adv Exp": promo_exp,
            "Net Worth": nw, "Cash Flow": cash_in - cash_out,
            "E Rx Pur": inp[14], "E OTC Pur": inp[15],
            "Current": curr_assets/curr_liab if curr_liab else 0,
            "Acid Test": (fin['cash']+fin['acct_receivable']+fin['investments'])/curr_liab if curr_liab else 0,
            "Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2) if (fin['inventory_rx']+fin['inventory_otc']) else 0,
            "ROI": (net_profit/nw*100) if nw else 0,
            "ROA": (net_profit/(curr_assets+fin['fixed_assets']))*100,
            "G Margin": (gross_margin/tot_sales)*100,
            "Profit": (net_profit/tot_sales)*100,
            "Debt/NW": (fin['long_term_debt']+curr_liab)/nw if nw else 0,
            "LOCATION": LOC_MAP[loc_code],
            "HMO Winner": (tid == hmo_winner_id),
            "Income_Statement": {
                "Sales": {"Rx": rx_sales, "Other": otc_sales, "Total": tot_sales},
                "COGS": {"Rx": cost_rx, "Other": cost_otc, "Total": tot_cogs},
                "Gross Margin": gross_margin,
                "Expenses": {
                    "Wages": wages_base, "Mgr Salary": mgr_salary, "Rent": rent_exp, "Util": 800, "Phone": 300, "Repairs": 400, "Insur": 500, "Tax": 400, "Supply": 600, "Adv": promo_exp, "Depr": depr, "Int": int_exp, "Bad": bad_debt, "Mort": mortgage, "Ben": ben_cost, "Pen": e_loan*0.2
                },
                "Total Expenses": total_expenses, "Inv Income": invest_income, "Net Profit": net_profit
            },
            "Balance_Sheet": {
                "Assets": {"Cash": fin['cash'], "AR": fin['acct_receivable'], "InvRx": fin['inventory_rx'], "InvOth": fin['inventory_otc'], "Invest": fin['investments'], "Fix": fin['fixed_assets']},
                "Liabilities": {"AP": fin['acct_payable'], "Notes": fin['notes_payable'], "LTD": fin['long_term_debt']},
                "Equity": fin['retained_earnings']
            }
        })
        p['status'] = 'Pending'

def run_simulation_step():
    rx_w = st.session_state.rx_weights_df; otc_w = st.session_state.otc_weights_df; env = st.session_state.instructor_env
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['location_code'] != 0: stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
    for loc in stores_by_loc:
        if stores_by_loc[loc]: calculate_results(stores_by_loc[loc], rx_w, otc_w, env)
    st.session_state.global_period += 1

# ==========================================
# 4. SIDEBAR & UI ROUTER
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V28")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

# ==========================================
# 5. INSTRUCTOR UI
# ==========================================
def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown('<div class="step-header">Step 1: Game Initialization</div>', unsafe_allow_html=True)
        num_teams = st.number_input("Number of Teams", 1, 20, 5)
        if st.button("Next ➡️", type="primary"):
            initialize_teams(num_teams); st.session_state.game_state = "SETUP_STEP_2"; st.rerun()

    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown('<div class="step-header">Step 2: Environment Configuration</div>', unsafe_allow_html=True)
        
        # Environment Editor
        env_df = pd.DataFrame(list(st.session_state.instructor_env.items()), columns=["Variable", "Value"])
        edited_env = st.data_editor(env_df, height=500, use_container_width=True)
        
        st.markdown("---")
        st.markdown('<div class="step-header">Step 3: Weights Configuration</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Rx Weights", "OTC Weights"])
        with tab1: e_rx = st.data_editor(st.session_state.rx_weights_df)
        with tab2: e_otc = st.data_editor(st.session_state.otc_weights_df)
        
        if st.button("💾 Save & Start Game", type="primary"):
            # Convert Env DF back to dict
            new_env = dict(zip(edited_env["Variable"], edited_env["Value"]))
            st.session_state.instructor_env = new_env
            st.session_state.rx_weights_df = e_rx
            st.session_state.otc_weights_df = e_otc
            st.session_state.game_state = "ACTIVE"
            st.toast("Configuration Saved!", icon="✅"); st.rerun()

    elif st.session_state.game_state == "ACTIVE":
        st.write(f"### City Summary - Period {st.session_state.global_period-1}")
        
        has_results = any(p['history'] for p in st.session_state.players.values())
        if has_results:
            metrics_order = [
                "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", "Rx GM%", "3-Pty GM%",
                "Tot #Rx's", "3-Pty #Rx", "Copay Dis", "OTC M'kup", "Rx Mkt Sh", "Store Hrs",
                "A/P Paid", "M'age Pay", "E. Loan", "Mgr Hrs", "RP OverT", "RP Hr Pay", 
                "Clk OverT", "Clk Wage", "Adv Exp", "Net Worth", "Cash Flow", "E Rx Pur", "E OTC Pur",
                "Current", "Acid Test", "Turnover", "ROI", "ROA", "G Margin", "Profit", "Debt/NW", "LOCATION"
            ]
            summary_data = {}
            for tid, p in st.session_state.players.items():
                if p['history']:
                    last = p['history'][-1]
                    summary_data[p['shop_name']] = [last.get(m, 0) for m in metrics_order]
            df_sum = pd.DataFrame(summary_data, index=metrics_order)
            
            # Format
            def fmt(val, idx):
                if idx=="LOCATION": return str(val)
                if any(x in idx for x in ["GM%","Mkt","ROI","Profit","Margin"]): return f"{val:.2f}%"
                if any(x in idx for x in ["SALES","Cash","Pay","Loan","Worth","Pur","$","Exp"]): return f"${val:,.0f}"
                return f"{val:.2f}" if isinstance(val,float) else f"{val}"
            
            for col in df_sum.columns: df_sum[col] = [fmt(v, i) for i, v in zip(df_sum.index, df_sum[col])]
            st.table(df_sum)
        
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        st.metric("Ready", f"{ready}/{len(st.session_state.players)}")
        if st.button("🚀 Run Period"): run_simulation_step(); st.rerun()

# ==========================================
# 6. STUDENT UI
# ==========================================
def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("Waiting for Instructor"); return
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    if p['period'] == 1 and p['status'] == 'Pending':
        c1, c2 = st.columns(2)
        n = c1.text_input("Store Name", p['shop_name']); l = c2.selectbox("Location", [0,1,2,3], format_func=lambda x: LOC_MAP[x])
        if st.button("Start"): 
            if l!=0: p['shop_name']=n; p['location_code']=l; p['status']='Thinking'; st.rerun()
        return

    tab1, tab2 = st.tabs(["Decisions", "Report"])
    with tab1:
        if p['status'] == 'Submitted': st.success("Submitted!"); st.button("Unsubmit", on_click=lambda: p.update({'status':'Thinking'}))
        else:
            df_inp = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            edited = st.data_editor(df_inp, hide_index=True, height=600)
            if st.button("Submit"): p['inputs']=edited['Value'].tolist(); p['status']='Submitted'; st.rerun()
    
    with tab2:
        if p['history']:
            last = p['history'][-1]
            inc = last['Income_Statement']; bal = last['Balance_Sheet']
            st.markdown(f"<div class='report-title'>Report Period {last['Period']}</div>", unsafe_allow_html=True)
            if last['HMO Winner']: st.success("🏆 HMO Winner!")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='report-header'>INCOME STATEMENT</div>", unsafe_allow_html=True)
                st.write(f"Total Sales: ${inc['Sales']['Total']:,.0f}")
                st.write(f"Gross Margin: ${inc['Gross Margin']:,.0f}")
                st.write(f"Total Expenses: ${inc['Total Expenses']:,.0f}")
                st.markdown(f"**Net Profit: ${inc['Net Profit']:,.0f}**")
            with c2:
                st.markdown("<div class='report-header'>BALANCE SHEET</div>", unsafe_allow_html=True)
                st.write(f"Cash: ${bal['Assets']['Cash']:,.0f}")
                st.write(f"Total Assets: ${sum(bal['Assets'].values()):,.0f}")
                st.write(f"Liabilities: ${sum(bal['Liabilities'].values()):,.0f}")
                st.write(f"Equity: ${bal['Equity']:,.0f}")
        else: st.info("No report.")

# ==========================================
# 7. ROUTER
# ==========================================
role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
