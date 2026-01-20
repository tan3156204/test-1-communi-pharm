import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Communi-Pharm V30 (Complete Flow)", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .step-header { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
    .step-title { color: #1565c0; font-size: 1.2rem; font-weight: bold; }
    .report-title { font-size: 1.5rem; font-weight: bold; text-align: center; color: #2c3e50; margin-bottom: 20px; }
    .report-section { background-color: #ffffff; padding: 15px; border: 1px solid #ddd; margin-bottom: 15px; }
    .report-header { font-weight: bold; border-bottom: 2px solid #2c3e50; margin-bottom: 10px; padding-bottom: 5px; }
    .fin-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #eee; }
    .fin-label { font-weight: 500; color: #555; }
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

# Default Inputs Structure (36 Items)
INPUT_LABELS = [
    "1. Rx Markup (%)", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0/1)", "5. Pt. Records (0/1)", "6. Credit (0/1)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists", "18. Pharm Wage ($/hr)",
    "19. # Clerks", "20. Clerk Wage ($/hr)", "21. Mgr Salary ($)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($)", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}
LOC_RENT_RATE = {1: 0.045, 2: 0.030, 3: 0.025}

# Weights Defaults
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

# Store Instructor Data (Market Parameters)
if 'inst_data' not in st.session_state:
    st.session_state.inst_data = {
        'rx_cost': 11.23, 'const_fee': 2.90, 'int_rate': 0.025, 
        'rx_market': 6000, 'otc_mult': 8.0, 
        'ben_life': 0.05, 'ben_health': 0.15, 'wage_std_pharm': 25.0, 'wage_std_clerk': 6.0,
        'emer_rate': 400.0, 'ad_limit': 1000.0
    }

if 'rx_weights_df' not in st.session_state:
    st.session_state.rx_weights_df = pd.DataFrame(RX_DEFAULT)
if 'otc_weights_df' not in st.session_state:
    st.session_state.otc_weights_df = pd.DataFrame(OTC_DEFAULT)

def get_starting_inputs():
    # Safe Defaults
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
# 3. LOGIC ENGINE
# ==========================================
def calculate_results():
    store_list = [p for p in st.session_state.players.values()]
    rx_w_df = st.session_state.rx_weights_df
    otc_w_df = st.session_state.otc_weights_df
    
    # Retrieve Dynamic Instructor Data
    I = st.session_state.inst_data
    
    # 1. HMO Bidding
    hmo_bids = {p['id']: p['inputs'][35] for p in store_list if p['inputs'][35] > 0}
    hmo_winner_id = min(hmo_bids, key=hmo_bids.get) if hmo_bids else None

    # 2. Ranking Preparation
    data = []
    # Use first store location for simple weight selection (or loop by loc in full version)
    # Assuming mixed or using Store 1 as reference for now
    loc_code = 1 # Default to Medical Center logic if not specified per store group
    if len(store_list)>0: loc_code = store_list[0]['location_code']
    loc_name = LOC_MAP[loc_code]

    for p in store_list:
        tid = p['id']; inp = p['inputs']; prev = p['prev_stats']; fin = p['financials']
        
        # Price Logic: If Input[0] > 10 => Markup%, Else => Fee$
        # Apply Logic: Cost + Fee OR Cost * (1+Markup)
        if inp[0] > 10: calc_price = I['rx_cost'] * (1 + inp[0]/100)
        else: calc_price = I['rx_cost'] + inp[0]
        
        # Price Floor (Safety)
        final_price = max(calc_price, 5.0) 
        final_price += I['const_fee'] # Add Constant Fee
        
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        
        data.append({
            'id': tid, 'price': final_price, 'promo': inp[7], 'hours': inp[6],
            'inv': inv_level
        })
    
    # Simple Ranking (Inverse Price)
    total_inv_price = sum([1/x['price'] for x in data])
    shares = {x['id']: (1/x['price'])/total_inv_price for x in data}
    
    # 3. Financials
    for p in store_list:
        tid = p['id']; inp = p['inputs']; fin = p['financials']
        share = shares[tid]
        
        # Apply HMO Bonus
        if tid == hmo_winner_id: share *= 1.15
        
        # Sales
        rx_count = I['rx_market'] * len(store_list) * share
        
        # Re-calc Price for Revenue
        if inp[0] > 10: p_price = I['rx_cost'] * (1 + inp[0]/100)
        else: p_price = I['rx_cost'] + inp[0]
        p_price = max(p_price, 5.0) + I['const_fee']
        
        rx_sales = rx_count * p_price
        otc_sales = (I['rx_market'] * len(store_list) * 8.0) * share * (I['otc_mult']/8.0) # Scale
        tot_sales = rx_sales + otc_sales
        
        # COGS
        cost_rx = rx_sales / (p_price/I['rx_cost']) 
        cost_otc = otc_sales * 0.65 
        gross_margin = tot_sales - (cost_rx + cost_otc)
        
        # --- STAFFING (90% Rule & Overtime) ---
        hrs_open = inp[6]
        
        # Pharmacist
        pharm_fte = inp[16]
        # Rule: If wage < 90% of Standard, lose 1 staff
        if inp[17] < (I['wage_std_pharm'] * 0.9): pharm_fte = max(0, pharm_fte - 1)
        
        avail_pharm_hours = (pharm_fte * 40 * 13) + (inp[22]/100 * inp[22] * 13) # Staff + Mgr (approx)
        req_pharm_hours = rx_count / 10.0 # 10 Rx/hr
        
        pharm_ot_hours = 0; emergency_cost = 0
        if avail_pharm_hours < req_pharm_hours:
            shortage = req_pharm_hours - avail_pharm_hours
            pharm_ot_hours = shortage
            emergency_cost = shortage * I['emer_rate'] * 1.5 # OT
            
        reg_pharm_wage = avail_pharm_hours * inp[17]
        total_pharm_cost = reg_pharm_wage + emergency_cost
        
        # Clerk
        clerk_fte = inp[18]
        # Rule: If wage < 90% of Standard, lose 1 staff
        if inp[19] < (I['wage_std_clerk'] * 0.9): clerk_fte = max(0, clerk_fte - 1)
        
        avail_clerk_hours = clerk_fte * 40 * 13
        req_clerk_hours = tot_sales / 25.30
        clerk_ot = max(0, req_clerk_hours - avail_clerk_hours)
        total_clerk_cost = (avail_clerk_hours * inp[19]) + (clerk_ot * inp[19] * 1.5)
        
        total_wages = total_pharm_cost + total_clerk_cost
        
        # Benefits
        ben_cost = 0
        if inp[32]==1: ben_cost += total_wages * I['ben_life']
        if inp[33]==1: ben_cost += total_wages * I['ben_health']
        
        # Expenses
        rent = tot_sales * 0.045
        expenses = total_wages + ben_cost + rent + inp[7] + inp[20] + inp[23] + 3000
        
        depr = fin['fixed_assets']*0.02
        bad_debt = inp[29]
        int_exp = (fin['long_term_debt']+fin['notes_payable']) * I['int_rate']
        
        total_opex = expenses + depr + int_exp + bad_debt
        net_profit = gross_margin - total_opex + (fin['investments'] * 0.015)
        
        # Cash
        fin['investments'] += (inp[9]-inp[11])
        fin['inventory_rx'] = max(0, fin['inventory_rx']+inp[14]-cost_rx) # Simplest Inv Logic
        fin['inventory_otc'] = max(0, fin['inventory_otc']+inp[15]-cost_otc)
        
        cash_flow_ops = tot_sales - (expenses + int_exp)
        fin['cash'] += (cash_flow_ops - inp[28] - inp[9] - inp[30])
        
        fin['acct_payable'] += (inp[14]+inp[15]-inp[28])
        fin['long_term_debt'] -= inp[30]
        
        e_loan = 0
        if fin['cash'] < 0:
            e_loan = abs(fin['cash']) + 5000
            fin['notes_payable'] += e_loan; fin['cash'] += e_loan
            penalty = e_loan * 0.20
            net_profit -= penalty; fin['retained_earnings'] -= penalty
            total_opex += penalty

        fin['retained_earnings'] += net_profit
        
        # Store History
        nw = fin['retained_earnings'] if fin['retained_earnings'] != 0 else 1
        curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc']
        curr_liab = fin['acct_payable'] + fin['notes_payable']
        
        def safe(n,d): return n/d if d!=0 else 0
        
        p['history'].append({
            "Period": st.session_state.global_period,
            # Instructor Report Metrics
            "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
            "Avg Rx Pr": p_price, "Rx Ing $": I['rx_cost'], 
            "Rx GM%": safe(rx_sales-cost_rx, rx_sales)*100, "3-Pty GM%": 0,
            "Tot #Rx's": rx_count, "3-Pty #Rx": 0,
            "Copay Dis": inp[2], "OTC M'kup": inp[13],
            "Rx Mkt Sh": share*100, "Store Hrs": hrs_open,
            "A/P Paid": inp[28], "M'age Pay": inp[23], "E. Loan": e_loan,
            "Mgr Hrs": inp[22], "RP OverT": pharm_ot_hours, "RP Hr Pay": I['emer_rate'] if pharm_ot_hours>0 else inp[17],
            "Clk OverT": clerk_ot, "Clk Wage": inp[19], "Adv Exp": inp[7],
            "Net Worth": nw, "Cash Flow": cash_flow_ops,
            "E Rx Pur": inp[14], "E OTC Pur": inp[15],
            
            # Ratios
            "Current": safe(curr_assets, curr_liab), "Acid Test": safe(fin['cash'], curr_liab),
            "Turnover": safe(cost_rx+cost_otc, (fin['inventory_rx']+fin['inventory_otc'])/2),
            "ROI": safe(net_profit, nw)*100, "ROA": safe(net_profit, curr_assets+fin['fixed_assets'])*100,
            "G Margin": safe(gross_margin, tot_sales)*100, "Profit": safe(net_profit, tot_sales)*100,
            "Debt/NW": safe(fin['long_term_debt']+curr_liab, nw), "LOCATION": LOC_MAP[p['location_code']],
            
            # Student Report Details
            "HMO Winner": (tid == hmo_winner_id),
            "Income_Statement": {
                "Sales": {"Rx": rx_sales, "Other": otc_sales, "Total": tot_sales},
                "COGS": {"Rx": cost_rx, "Other": cost_otc, "Total": cost_rx+cost_otc},
                "Gross Margin": gross_margin,
                "Expenses": {"Wages": total_wages, "Rent": rent, "Other": expenses-total_wages-rent, "Penalty": penalty if e_loan else 0},
                "Total Expenses": total_opex, "Net Profit": net_profit
            },
            "Balance_Sheet": {
                "Assets": {"Cash": fin['cash'], "Inv": fin['inventory_rx']+fin['inventory_otc']},
                "Liabilities": {"AP": fin['acct_payable'], "Debt": fin['long_term_debt']},
                "Equity": fin['retained_earnings']
            }
        })
        p['status'] = 'Pending'
    st.session_state.global_period += 1

# ==========================================
# 4. SIDEBAR & RESET
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V30")
    if st.button("🔄 HARD RESET", type="primary"): st.session_state.clear(); st.rerun()

# ==========================================
# 5. INSTRUCTOR UI (FULL FLOW)
# ==========================================
def render_instructor_ui():
    st.header("👨‍🏫 Instructor Dashboard")
    
    # STEP 1: TEAMS
    if st.session_state.game_state == "SETUP_STEP_1":
        st.markdown('<div class="step-header"><span class="step-title">Step 1: Teams</span></div>', unsafe_allow_html=True)
        n = st.number_input("Number of Teams", 1, 20, 5)
        if st.button("Next ➡️", type="primary"):
            initialize_teams(n); st.session_state.game_state = "SETUP_STEP_2"; st.rerun()

    # STEP 2: MARKET DATA (NEW!)
    elif st.session_state.game_state == "SETUP_STEP_2":
        st.markdown('<div class="step-header"><span class="step-title">Step 2: Market Scenarios (Instructor Data)</span></div>', unsafe_allow_html=True)
        st.info("กำหนดค่าสภาพตลาดและเศรษฐกิจสำหรับ Period นี้")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💊 Rx & Sales")
            rx_cost = st.number_input("Rx Ingredient Cost ($)", value=11.23)
            const_fee = st.number_input("Constant Service Fee ($)", value=2.90)
            rx_mkt = st.number_input("Avg Rx Volume (Units/Store)", value=6000)
            otc_mult = st.number_input("OTC Market Multiplier", value=8.0)
            ad_limit = st.number_input("Ad Expenditure Limit ($)", value=1000.0)
        with col2:
            st.subheader("💰 Financials & Wages")
            int_rate = st.number_input("Interest Rate (%)", value=2.5) / 100.0
            wage_ph = st.number_input("Std. Pharm Wage ($/hr)", value=25.0)
            wage_cl = st.number_input("Std. Clerk Wage ($/hr)", value=6.0)
            emer_rt = st.number_input("Emergency/OT Rate ($/hr)", value=400.0)
            ben_l = st.number_input("Benefit: Life (%)", value=5.0) / 100.0
            ben_h = st.number_input("Benefit: Health (%)", value=15.0) / 100.0

        c1, c2 = st.columns([1, 5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_1"; st.rerun()
        if c2.button("Next ➡️", type="primary"):
            # Save Data
            st.session_state.inst_data.update({
                'rx_cost': rx_cost, 'const_fee': const_fee, 'rx_market': rx_mkt, 'otc_mult': otc_mult,
                'int_rate': int_rate, 'wage_std_pharm': wage_ph, 'wage_std_clerk': wage_cl,
                'emer_rate': emer_rt, 'ben_life': ben_l, 'ben_health': ben_h, 'ad_limit': ad_limit
            })
            st.session_state.game_state = "SETUP_STEP_3"
            st.rerun()

    # STEP 3: WEIGHTS
    elif st.session_state.game_state == "SETUP_STEP_3":
        st.markdown('<div class="step-header"><span class="step-title">Step 3: Weights Config</span></div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["Rx", "OTC"])
        with t1: e1 = st.data_editor(st.session_state.rx_weights_df)
        with t2: e2 = st.data_editor(st.session_state.otc_weights_df)
        
        c1, c2 = st.columns([1, 5])
        if c1.button("⬅️ Back"): st.session_state.game_state="SETUP_STEP_2"; st.rerun()
        if c2.button("💾 Start Game", type="primary"):
            st.session_state.rx_weights_df=e1; st.session_state.otc_weights_df=e2; st.session_state.game_state="ACTIVE"; st.rerun()

    # ACTIVE DASHBOARD
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
            
            def fmt(val, idx):
                if idx == "LOCATION": return str(val)
                if any(x in idx for x in ["GM%", "Mkt Sh", "ROI", "Profit", "G Margin"]): return f"{val:.2f}%"
                if any(x in idx for x in ["SALES", "Cash", "Pay", "Loan", "Worth", "Pur", "$", "Exp"]): return f"${val:,.0f}"
                return f"{val:.2f}" if isinstance(val, float) else f"{val}"

            for col in df_sum.columns:
                df_sum[col] = [fmt(v, i) for i, v in zip(df_sum.index, df_sum[col])]
            
            st.table(df_sum)
        
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        st.metric("Ready Teams", f"{ready}/{len(st.session_state.players)}")
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
        if st.button("Confirm"): 
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
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='report-header'>INCOME STATEMENT</div>", unsafe_allow_html=True)
                st.write(f"Total Sales: ${inc['Sales']['Total']:,.0f}")
                st.write(f"Gross Margin: ${inc['Gross Margin']:,.0f}")
                st.write(f"Net Profit: ${inc['Net Profit']:,.0f}")
            with col2:
                st.markdown("<div class='report-header'>BALANCE SHEET</div>", unsafe_allow_html=True)
                st.write(f"Total Assets: ${sum(bal['Assets'].values()):,.0f}")
                st.write(f"Total Liab: ${sum(bal['Liabilities'].values()):,.0f}")
                st.write(f"Equity: ${bal['Equity']:,.0f}")
        else: st.info("No results.")

# ==========================================
# 7. ROUTER
# ==========================================
role = st.sidebar.selectbox("Role", ["Student", "Instructor"])
if role == "Instructor":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD: render_instructor_ui()
else: render_student_ui()
