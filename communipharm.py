import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V24 (Authentic Reports)", layout="wide")

# CSS Styling (Report Style)
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .report-title { font-size: 1.5rem; font-weight: bold; text-align: center; color: #2c3e50; margin-bottom: 20px; }
    .report-section { background-color: #ffffff; padding: 15px; border: 1px solid #ddd; margin-bottom: 15px; }
    .report-header { font-weight: bold; border-bottom: 2px solid #2c3e50; margin-bottom: 10px; padding-bottom: 5px; }
    .fin-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #eee; }
    .fin-label { font-weight: 500; color: #555; }
    .fin-value { font-family: 'Courier New', monospace; font-weight: bold; }
    .double-underline { border-bottom: 3px double #000; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# --- Constants ---
WEEKS_PER_PERIOD = 13
BASE_COST_RX = 11.23
CONST_FEE = 2.90
BENEFIT_RATE_LIFE = 0.05
BENEFIT_RATE_HEALTH = 0.15
INVESTMENT_RETURN = 0.015

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

# Weights
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
# 3. LOGIC ENGINE (V21 - Exact Logic)
# ==========================================
def calculate_results(store_list, rx_w_df, otc_w_df):
    data = []
    loc_code = store_list[0]['p']['location_code']
    loc_name = LOC_MAP[loc_code]

    # --- 1. Ranking Prep ---
    for p in store_list:
        tid = p['id']; inp = p['p']['inputs']; prev = p['p']['prev_stats']; fin = p['p']['financials']
        curr_price = (BASE_COST_RX * (1 + inp[0]/100)) + inp[1] + CONST_FEE
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        data.append({
            'id': tid, 'price_past': prev['avg_price'], 'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3], 'records': inp[4], 'credit': inp[5], 
            'inventory': inv_level, 'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr'],
            'otc_markup_past': prev.get('otc_markup', 45.0), 'otc_markup_pres': inp[13], 'advertising': inp[7]
        })
    df_comp = pd.DataFrame(data)

    # --- 2. Scoring ---
    rx_weights = rx_w_df.set_index("Factor")[loc_name].values
    otc_weights = otc_w_df.set_index("Factor")[loc_name].values

    df_rx_ranks = pd.DataFrame({'id': df_comp['id']})
    def get_rank(series, ascending): return series.rank(method='min', ascending=ascending)
    df_rx_ranks['r0'] = get_rank(df_comp['price_past'], False); df_rx_ranks['r1'] = get_rank(df_comp['price_pres'], False)
    cols = ['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']
    for i, col in enumerate(cols): df_rx_ranks[f'r{i+2}'] = get_rank(df_comp[col], True)
    
    rx_scores = {row['id']: sum(row[f'r{i}'] * rx_weights[i] for i in range(10)) for index, row in df_rx_ranks.iterrows()}
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

    # --- 3. Financials (Detailed for PDF) ---
    base_rx_market = len(store_list) * 6000
    base_otc_market_usd = base_rx_market * 8.0
    
    for s_data in store_list:
        tid = s_data['id']; p = s_data['p']; inp = p['inputs']; fin = p['financials']
        my_rx_share = rx_shares[tid]; my_otc_share = otc_shares[tid]
        
        rx_count = base_rx_market * my_rx_share
        avg_rx_price = (BASE_COST_RX*(1+inp[0]/100))+inp[1]+CONST_FEE
        rx_sales = rx_count * avg_rx_price
        loc_mult = 1.5 if loc_code == 3 else 1.0
        otc_sales = base_otc_market_usd * loc_mult * my_otc_share
        tot_sales = rx_sales + otc_sales
        
        cost_rx = rx_sales / (1+inp[0]/100); cost_otc = otc_sales / (1+inp[13]/100)
        tot_cogs = cost_rx + cost_otc
        gross_margin = tot_sales - tot_cogs
        
        # Expenses Breakdown
        wages_base = ((inp[17]*inp[18]) + (inp[19]*inp[20])) * inp[6] * WEEKS_PER_PERIOD
        if inp[6]>40: wages_base *= 1.1
        ben_cost = 0
        if inp[32]==1: ben_cost += wages_base * BENEFIT_RATE_LIFE
        if inp[33]==1: ben_cost += wages_base * BENEFIT_RATE_HEALTH
        
        rent_exp = tot_sales * LOC_RENT_RATE.get(loc_code, 0.0)
        promo_exp = inp[7]
        mgr_salary = inp[21]
        
        # Simplified Fixed Exp breakdown for display (Visual only to match PDF look)
        # Total Fixed Ops = Mgr + Mortgage + 3000 (Util/Other)
        # We will split 3000 into smaller buckets for the report
        util_exp = 800; phone_exp = 300; repair_exp = 400; ins_exp = 500; tax_exp = 400; supply_exp = 600
        # Mortgage is separate input
        mortgage = inp[24]
        
        depr = fin['fixed_assets']*0.02
        bad_debt = inp[29]
        int_exp = (fin['long_term_debt']+fin['notes_payable'])*0.025
        
        total_expenses = wages_base + ben_cost + rent_exp + promo_exp + mgr_salary + mortgage + 3000 + depr + int_exp + bad_debt
        
        invest_income = fin['investments']*INVESTMENT_RETURN
        net_profit = gross_margin - total_expenses + invest_income
        
        # Cash Flow & Balance Sheet Update
        fin['investments'] += (inp[9]-inp[11])
        max_rx_ret = fin['inventory_rx']*0.25; max_otc_ret=fin['inventory_otc']*0.25
        act_rx_ret = min(inp[26], max_rx_ret); act_otc_ret = min(inp[27], max_otc_ret)
        
        fin['inventory_rx'] = max(0, fin['inventory_rx']+inp[14]-act_rx_ret-cost_rx)
        fin['inventory_otc'] = max(0, fin['inventory_otc']+inp[15]-act_otc_ret-cost_otc)
        
        cash_in = (tot_sales*0.9) + act_rx_ret + act_otc_ret + inp[11]
        # Cash Out: Expenses (minus non-cash) + Pay AP + New Invest + Debt Pay
        cash_out_items = (total_expenses - depr - bad_debt - int_exp) # interest handled usually
        # Re-calc cash out precisely:
        cash_out = (wages_base + ben_cost + rent_exp + promo_exp + mgr_salary + mortgage + 3000 + int_exp) + inp[28] + inp[9] + inp[30]
        
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
            total_expenses += penalty # Add to expense for display

        fin['retained_earnings'] += net_profit
        
        # --- PREPARE DETAILED REPORT DATA ---
        nw = fin['retained_earnings']
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        # Save comprehensive data for UI
        p['history'].append({
            "Period": st.session_state.global_period,
            # Metrics for Instructor Table
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Avg Rx Pr": avg_rx_price, "Rx Ing $": BASE_COST_RX, 
            "Rx Mkt Sh": my_rx_share*100, "OTC Mkt Sh": my_otc_share*100,
            "Net Profit": net_profit, "ROI": (net_profit/nw*100) if nw else 0,
            "Store Hrs": inp[6], "# Pharm": inp[16], "# Clerks": inp[18],
            "Wage/Hr": (wages_base/(inp[6]*13))/ (inp[16]+inp[18]) if (inp[16]+inp[18]) else 0, # Approx
            "Pt. Rec": inp[4], "Del Ser": inp[3], "Store Credit": inp[5], "Copay Dsct": inp[2],
            "Ins Life": inp[32], "Ins Hlt": inp[33],
            
            # Detailed Financials for Student Report
            "Income_Statement": {
                "Sales": {"Rx": rx_sales, "Other": otc_sales, "Total": tot_sales},
                "COGS": {"Rx": cost_rx, "Other": cost_otc, "Total": tot_cogs},
                "Gross Margin": gross_margin,
                "Expenses": {
                    "Wages (Pharm/Clerk)": wages_base, "Manager Salary": mgr_salary, 
                    "Rent": rent_exp, "Utilities": util_exp, "Phone": phone_exp, "Repairs": repair_exp,
                    "Insurance": ins_exp, "Taxes": tax_exp, "Supplies": supply_exp, "Advertising": promo_exp,
                    "Depreciation": depr, "Interest": int_exp, "Bad Debts": bad_debt, "Mortgage Interest": mortgage,
                    "Employee Benefits": ben_cost, "Emergency Penalty": e_loan*0.20 if e_loan else 0
                },
                "Total Expenses": total_expenses,
                "Inv Income": invest_income,
                "Net Profit": net_profit
            },
            "Balance_Sheet": {
                "Assets": {
                    "Cash": fin['cash'], "Accts Receivable": fin['acct_receivable'], 
                    "Inventory (Rx)": fin['inventory_rx'], "Inventory (Other)": fin['inventory_otc'],
                    "Investments (CDs)": fin['investments'], "Fixed Assets (Net)": fin['fixed_assets']
                },
                "Liabilities": {
                    "Accts Payable": fin['acct_payable'], "Notes Payable (Emerg)": fin['notes_payable'],
                    "Long Term Debt": fin['long_term_debt']
                },
                "Equity": fin['retained_earnings']
            },
            "Ratios": {
                "Current Ratio": curr_assets/curr_liab if curr_liab else 0,
                "Acid Test": (fin['cash']+fin['acct_receivable']+fin['investments'])/curr_liab if curr_liab else 0,
                "Inv Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2) if (fin['inventory_rx']+fin['inventory_otc']) else 0,
                "Net Profit %": (net_profit/tot_sales)*100,
                "Gross Margin %": (gross_margin/tot_sales)*100,
                "Return on Assets": (net_profit/(curr_assets+fin['fixed_assets']))*100,
                "Debt/Net Worth": (fin['long_term_debt']+curr_liab)/nw if nw else 0
            }
        })
        p['status'] = 'Pending'

def run_simulation_step():
    rx_w = st.session_state.rx_weights_df; otc_w = st.session_state.otc_weights_df
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['location_code'] != 0: stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
    for loc in stores_by_loc:
        if stores_by_loc[loc]: calculate_results(stores_by_loc[loc], rx_w, otc_w)
    st.session_state.global_period += 1

# ==========================================
# 4. SIDEBAR & UI ROUTER
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm UI+")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

# ==========================================
# 5. INSTRUCTOR UI (Page 2 Style Summary)
# ==========================================
def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP_STEP_1":
        st.info("Setup Step 1: Create Teams"); n = st.number_input("Teams", 1, 20, 3)
        if st.button("Next"): initialize_teams(n); st.session_state.game_state="SETUP_STEP_2"; st.rerun()
    elif st.session_state.game_state == "SETUP_STEP_2":
        st.info("Setup Step 2: Config"); 
        if st.button("Start Game"): st.session_state.game_state="ACTIVE"; st.rerun()
    elif st.session_state.game_state == "ACTIVE":
        st.write(f"### City Summary - Period {st.session_state.global_period-1}")
        
        # Check if results exist
        has_results = any(p['history'] for p in st.session_state.players.values())
        if has_results:
            # Build CITY SUMMARY Table (Rows=Metrics, Cols=Stores)
            metrics = [
                "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", 
                "Rx Mkt Sh", "OTC Mkt Sh", "Net Profit", "ROI", "Store Hrs", 
                "# Pharm", "# Clerks", "Wage/Hr", "Pt. Rec", "Del Ser", 
                "Store Credit", "Copay Dsct", "Ins Life", "Ins Hlt"
            ]
            
            summary_data = {}
            for tid, p in st.session_state.players.items():
                if p['history']:
                    last = p['history'][-1]
                    col_name = p['shop_name']
                    summary_data[col_name] = [last.get(m, 0) for m in metrics]
            
            df_summary = pd.DataFrame(summary_data, index=metrics)
            
            # Format Numbers
            def format_val(val, metric):
                if "SALES" in metric or "Profit" in metric: return f"${val:,.0f}"
                if "Mkt Sh" in metric or "ROI" in metric: return f"{val:.2f}%"
                if "$" in metric or "Pr" in metric or "Wage" in metric: return f"${val:.2f}"
                return f"{val:.0f}" if isinstance(val, (int, float)) else val

            # Apply formatting
            for col in df_summary.columns:
                df_summary[col] = [format_val(v, i) for i, v in zip(df_summary.index, df_summary[col])]
            
            st.table(df_summary)
        
        # Control
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        st.metric("Ready", f"{ready}/{len(st.session_state.players)}")
        if st.button("🚀 Run Period"): run_simulation_step(); st.rerun()

# ==========================================
# 6. STUDENT UI (Pages 3-7 Style Report)
# ==========================================
def render_student_ui():
    if st.session_state.game_state != "ACTIVE": st.warning("Waiting for start"); return
    
    t_ids = list(st.session_state.players.keys())
    sel_id = st.selectbox("Select Team", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    p = st.session_state.players[sel_id]
    
    if p['period'] == 1 and p['status'] == 'Pending':
        st.info("Setup P1"); 
        if st.button("Start P1"): p['status']='Thinking'; st.rerun()
        return

    tab1, tab2 = st.tabs(["📝 Decisions", "📊 Financial Report"])
    
    with tab1:
        if p['status'] == 'Submitted': st.success("Submitted!"); st.button("Unsubmit", on_click=lambda: p.update({'status':'Thinking'}))
        else:
            df_inp = pd.DataFrame({"Label": INPUT_LABELS, "Value": p['inputs']})
            edited = st.data_editor(df_inp, hide_index=True, height=600)
            if st.button("Submit"): p['inputs']=edited['Value'].tolist(); p['status']='Submitted'; st.rerun()

    with tab2:
        if p['history']:
            last = p['history'][-1]
            inc = last['Income_Statement']
            bal = last['Balance_Sheet']
            rat = last['Ratios']
            
            st.markdown(f"<div class='report-title'>CONFIDENTIAL FINANCIAL REPORT<br>{p['shop_name']} - Period {last['Period']}</div>", unsafe_allow_html=True)
            
            # --- INCOME STATEMENT ---
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown("<div class='report-header'>INCOME STATEMENT</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**REVENUE**")
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Rx Sales</span><span class='fin-value'>${inc['Sales']['Rx']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Other Sales</span><span class='fin-value'>${inc['Sales']['Other']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row' style='border-top:1px solid #000'><span class='fin-label'>TOTAL SALES</span><span class='fin-value'>${inc['Sales']['Total']:,.0f}</span></div>", unsafe_allow_html=True)
                
                st.write("**COST OF GOODS SOLD**")
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Rx Cost</span><span class='fin-value'>${inc['COGS']['Rx']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Other Cost</span><span class='fin-value'>${inc['COGS']['Other']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row' style='border-top:1px solid #000'><span class='fin-label'>TOTAL COGS</span><span class='fin-value'>${inc['COGS']['Total']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row' style='background:#f9f9f9'><span class='fin-label'>GROSS MARGIN</span><span class='fin-value'>${inc['Gross Margin']:,.0f}</span></div>", unsafe_allow_html=True)

            with col2:
                st.write("**OPERATING EXPENSES**")
                for k, v in inc['Expenses'].items():
                    if v > 0:
                        st.markdown(f"<div class='fin-row'><span class='fin-label'>{k}</span><span class='fin-value'>${v:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row' style='border-top:1px solid #000'><span class='fin-label'>TOTAL EXPENSES</span><span class='fin-value'>${inc['Total Expenses']:,.0f}</span></div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Investment Income</span><span class='fin-value'>+ ${inc['Inv Income']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row double-underline' style='font-size:1.1em'><span class='fin-label'>NET PROFIT</span><span class='fin-value'>${inc['Net Profit']:,.0f}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # --- BALANCE SHEET ---
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown("<div class='report-header'>BALANCE SHEET</div>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                st.write("**ASSETS**")
                for k, v in bal['Assets'].items():
                    st.markdown(f"<div class='fin-row'><span class='fin-label'>{k}</span><span class='fin-value'>${v:,.0f}</span></div>", unsafe_allow_html=True)
                tot_ast = sum(bal['Assets'].values())
                st.markdown(f"<div class='fin-row double-underline'><span class='fin-label'>TOTAL ASSETS</span><span class='fin-value'>${tot_ast:,.0f}</span></div>", unsafe_allow_html=True)
            with b2:
                st.write("**LIABILITIES & EQUITY**")
                for k, v in bal['Liabilities'].items():
                    st.markdown(f"<div class='fin-row'><span class='fin-label'>{k}</span><span class='fin-value'>${v:,.0f}</span></div>", unsafe_allow_html=True)
                tot_liab = sum(bal['Liabilities'].values())
                st.markdown(f"<div class='fin-row' style='border-top:1px solid #000'><span class='fin-label'>Total Liabilities</span><span class='fin-value'>${tot_liab:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row'><span class='fin-label'>Owner's Equity</span><span class='fin-value'>${bal['Equity']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fin-row double-underline'><span class='fin-label'>TOTAL LIAB & EQUITY</span><span class='fin-value'>${tot_liab + bal['Equity']:,.0f}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # --- RATIOS ---
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown("<div class='report-header'>OPERATIONAL INDICATORS</div>", unsafe_allow_html=True)
            r1, r2, r3, r4 = st.columns(4)
            rkeys = list(rat.keys())
            for i, k in enumerate(rkeys):
                val = rat[k]
                col = [r1, r2, r3, r4][i % 4]
                col.metric(k, f"{val:.2f}")
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("No report generated yet.")

# ==========================================
# 7. ROUTER
# ==========================================
role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD: render_instructor_ui()
else:
    render_student_ui()
