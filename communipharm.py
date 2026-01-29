import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 0. CONFIG & UTILS
# ==========================================
st.set_page_config(page_title="PharmaSim V56.0 (Accounting Logic Fix)", layout="wide")

def force_reset():
    st.session_state.clear()
    st.rerun()

def safe_fmt(x):
    if isinstance(x, (int, float)):
        return "{:,.2f}".format(x)
    return str(x)

def get_current_date_str():
    if 'market_env' in st.session_state:
        d = st.session_state.market_env.get('date_day', 30)
        m = st.session_state.market_env.get('date_month', 6)
        y = st.session_state.market_env.get('date_year', 89)
        return f"{int(d)}/{int(m)}/19{int(y)}"
    return "30/06/1989"

# ==========================================
# 1. CONSTANTS & DATA
# ==========================================
STORE_CATEGORY = {
    0: "Medical", 1: "Neighbor", 2: "Shopping", 
    3: "Neighbor", 4: "Neighbor", 5: "Neighbor", 6: "Neighbor"
}

WEIGHTS = {
    "Medical": {"rx_price": 5, "adv": 11, "hours": 7, "delivery": 10, "records": 15, "credit": 3, "inventory": 10, "prev_share": 23, "otc_markup": 5, "otc_adv": 5, "otc_hours": 3},
    "Neighbor": {"rx_price": 5, "adv": 12, "hours": 10, "delivery": 6, "records": 8, "credit": 2, "inventory": 10, "prev_share": 15, "otc_markup": 15, "otc_adv": 10, "otc_hours": 15},
    "Shopping": {"rx_price": 10, "adv": 15, "hours": 12, "delivery": 1, "records": 1, "credit": 1, "inventory": 10, "prev_share": 5, "otc_markup": 20, "otc_adv": 10, "otc_hours": 15}
}

# Baseline Inputs based on user's inputc1p1
BASELINE_INPUTS = [
    {"markup": 60, "promo": 600, "hours": 46, "del": 1, "rec": 1, "cred": 1, "pharm": 0, "clerk": 1.2, "ap_paid": 60889, "rx_pur": 40000, "otc_pur": 16000},
    {"markup": 30, "promo": 1500, "hours": 60, "del": 1, "rec": 1, "cred": 0, "pharm": 1, "clerk": 6.6, "ap_paid": 102000, "rx_pur": 60000, "otc_pur": 80000},
    {"markup": 30, "promo": 1900, "hours": 70, "del": 0, "rec": 1, "cred": 0, "pharm": 1.3, "clerk": 7.0, "ap_paid": 61626, "rx_pur": 65000, "otc_pur": 120000},
    {"markup": 40, "promo": 1500, "hours": 70, "del": 0, "rec": 0, "cred": 0, "pharm": 1.5, "clerk": 6.5, "ap_paid": 115000, "rx_pur": 65000, "otc_pur": 145000},
    {"markup": 35, "promo": 2200, "hours": 90, "del": 0, "rec": 0, "cred": 1, "pharm": 1.5, "clerk": 8.9, "ap_paid": 98000, "rx_pur": 85000, "otc_pur": 145000},
    {"markup": 38, "promo": 3000, "hours": 75, "del": 0, "rec": 1, "cred": 0, "pharm": 1.75, "clerk": 8.0, "ap_paid": 95000, "rx_pur": 65000, "otc_pur": 175000},
    {"markup": 49, "promo": 600, "hours": 48, "del": 0, "rec": 1, "cred": 1, "pharm": 1, "clerk": 1.0, "ap_paid": 58000, "rx_pur": 40000, "otc_pur": 24000}
]

BASELINE_TARGETS = {
    "rx_demand": [4655, 5971, 9091, 7721, 5199, 4927, 4023],
    "other_sales": [13136, 85384, 97425, 87573, 123698, 108372, 5911],
}

# FULL 28 ENV VARIABLES
ENV_MAPPING = [
    {"key": "avg_ing_cost", "label": "Average Ingredient Cost ($)", "value": 11.23},
    {"key": "avg_copay", "label": "Average Copay Allowed ($)", "value": 2.0},
    {"key": "avg_3rd_party_fee", "label": "Average Third-Party Fee ($)", "value": 2.75},
    {"key": "pct_3rd_party", "label": "Percent Market Rx’s 3rd-Party (%)", "value": 46.43},
    {"key": "max_promo", "label": "Maximum Promotion Expenditure ($)", "value": 1200},
    {"key": "pct_ar_store1", "label": "% Sales A/R Store Type 1 (%)", "value": 30.2},
    {"key": "pct_ar_store2", "label": "% A/R Sales Store Type 2 (%)", "value": 21.2},
    {"key": "pct_ar_store3", "label": "% A/R Sales Store Type 3 (%)", "value": 9.34},
    {"key": "interest_rate", "label": "Interest Rate for Period (%)", "value": 10.5},
    {"key": "avg_rx_per_store", "label": "Average Number Rx Per Store (#)", "value": 5949},
    {"key": "avg_other_sales", "label": "Average Other Sales Per Store ($)", "value": 74500},
    {"key": "gm_slippage", "label": "Gross Margin Slippage Rate (%)", "value": 0.1},
    {"key": "periods_per_year", "label": "Number Periods per Year (#)", "value": 6},
    {"key": "3rd_party_lag", "label": "Third-Party Lag in Payment (%)", "value": 14.4},
    {"key": "ar_lag", "label": "A/R Lag in Payment (%)", "value": 11.2},
    {"key": "mutual_fund_price", "label": "Mutual Fund Transaction Price ($)", "value": 26.4},
    {"key": "inflation", "label": "Current Inflation Rate (%)", "value": 1.1},
    {"key": "stockout_rx_index", "label": "Stockout Rx Inventory Index", "value": 77},
    {"key": "stockout_other_index", "label": "Stockout Other Inventory Index", "value": 55},
    {"key": "pass_book_rate", "label": "Pass Book Savings Rate (%)", "value": 5.25},
    {"key": "mutual_fund_next", "label": "Mutual Fund Next Period ($)", "value": 27.65},
    {"key": "cd_interest_rate", "label": "Interest Rate on CD’s (%)", "value": 7.88},
    {"key": "avg_sales_per_clerk", "label": "Average Dollar Sales/Clerk ($)", "value": 28.5},
    {"key": "max_rx_price", "label": "Maximum Price for Rx’s ($)", "value": 23.0},
    {"key": "ss_wc_rate", "label": "SS & WC as % of Salary & Wages (%)", "value": 11.0},
    {"key": "date_month", "label": "Closing Date: Month", "value": 6},
    {"key": "date_day", "label": "Closing Date: Day", "value": 30},
    {"key": "date_year", "label": "Closing Date: Year", "value": 89},
]

INPUT_LABELS = [
    "Prescription Markup (%)", "Prescription Professional Fee ($)", "Copayment Discount ($)", 
    "Delivery Service (1=Yes,0=No)", "Patient Records (1=Yes,0=No)", "Store Offers Credit (1=Yes,0=No)", 
    "Hours Pharmacy Open Per Week", "Promotional Expenditures ($)", "% Promotion on Rx Department (%)", 
    "Current Period's Investment ($)", "Investment Project Number", "Investment Withdrawal ($)", 
    "Investment Withdrawal Project Number", "Markup on Other Store Items (%)", 
    "Prescription Inventory Purchases ($)", "Other Inventory Purchases ($)", 
    "Number Pharmacists Employed", "Pharmacist's Hourly Pay Rate ($)", 
    "Number Sales Clerks Employed", "Sales Clerk's Hourly Pay Rate ($)", 
    "Manager's Salary For Period ($)", "Manager's Percent Time Rx Dept (%)", 
    "Number of Hours Worked by Manager Per Week", "Mortgage Payment ($)", 
    "Amount Sent to Collection Agency ($)", "Minimum Cash Balance ($)", 
    "Prescription Inventory Returned ($)", "Other Inventory Returned ($)", 
    "Payment on Accounts Payable ($)", "Long Term Debt Written ($)", 
    "Long Term Debt Payment ($)", "Interest Rate Charged on Accounts Receivable (%)", 
    "Personal Benefits: Life Insurance (1=Yes)", "Health Insurance (1=Yes)", 
    "Participate in Third-Party Rx's (1=Yes)", "Bid for HMO Contract: 0 = No bid ($)"
]

OUTPUT_LABELS = [
    "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", "Rx GM%", "3-Pty GM%",
    "Tot #Rx's", "3-Pty #Rx", "Copay Dis", "OTC M'kup", "Rx Mkt Sh", "Store Hrs",
    "A/P Paid", "M'age Pay", "E. Loan", "Mgr Hrs", "RP OverT", "RP Hr Pay",
    "Clk OverT", "Clk Wage", "Adv Exp", "Net Worth", "Cash Flow",
    "E Rx Pur", "E OTC Pur", "RATIOS", "Current", "Acid Test", "Turnover",
    "ROI", "ROA", "G Margin", "Profit", "Debt/NW", "LOCATION",
    "DEBUG: Cash In", "DEBUG: Cash Out"
]

# ==========================================
# 2. STATE INITIALIZATION
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP"
    st.session_state.current_period = 1
    st.session_state.num_stores = 7
    st.session_state.market_env = {item['key']: item['value'] for item in ENV_MAPPING}
    st.session_state.players = {} 

# ==========================================
# 3. GAME LOGIC FUNCTIONS
# ==========================================
def init_game(n_stores):
    st.session_state.players = {}
    st.session_state.current_period = 1
    st.session_state.market_env = {item['key']: item['value'] for item in ENV_MAPPING}
    
    # Financial Initialization 
    init_cash = [8746, 2500, 2500, 2200, 2500, 2200, 5000]
    
    for i in range(n_stores):
        ref_idx = i if i < 7 else 0 
        base = BASELINE_INPUTS[ref_idx]
        
        d = [0.0] * 36
        d[0] = float(base['markup'])
        d[3] = float(base['del']); d[4] = float(base['rec']); d[5] = float(base['cred'])
        d[6] = float(base['hours']); d[7] = float(base['promo'])
        d[14] = float(base['rx_pur']); d[15] = float(base['otc_pur'])
        d[16] = float(base['pharm']); d[17] = 20.0 
        d[18] = float(base['clerk']); d[19] = 5.0 
        d[20] = 8000.0; d[28] = float(base['ap_paid']) 
        
        init_ap_val = base['ap_paid'] 
        init_ar_val = 22000 
        init_inv = 130000 
        nw_start = init_cash[ref_idx] + init_inv + init_ar_val - init_ap_val
        
        st.session_state.players[i] = {
            "name": f"Store {i+1}",
            "type": STORE_CATEGORY.get(ref_idx, "Neighbor"),
            "inputs": d,
            "financials": {
                "cash": init_cash[ref_idx],
                "inventory": init_inv,
                "ar": init_ar_val, 
                "ap": init_ap_val,
                "loan": 0,
                "net_worth": nw_start
            },
            "status": "Pending",
            "history": []
        }
    st.session_state.num_stores = n_stores
    st.session_state.game_state = "ACTIVE"

def calculate_score(w, markup, promo, hours, delivery, records, credit, env):
    est_price = env['avg_ing_cost'] * (1 + markup/100) 
    score_price = (1.0 / est_price) * w["rx_price"] * 1000 
    max_promo_val = env.get('max_promo', 1200)
    score_adv = (np.log1p(promo) / np.log1p(max_promo_val)) * w["adv"]
    score_hours = (hours / 50) * w["hours"]
    score_service = (delivery * w["delivery"]) + (records * w["records"]) + (credit * w["credit"])
    score_fixed = w["inventory"] + w["prev_share"]
    return score_price + score_adv + score_hours + score_service + score_fixed

def run_period_simulation():
    env = st.session_state.market_env
    total_baseline_rx = sum(BASELINE_TARGETS['rx_demand'])
    
    for pid, p in st.session_state.players.items():
        ref_idx = pid if pid < 7 else 0
        inp = p['inputs']
        fin = p['financials']
        
        # --- INPUTS ---
        curr_markup = inp[0]; copay_disc = inp[2]
        curr_del = inp[3]; curr_rec = inp[4]; curr_cred = inp[5]
        curr_hours = inp[6]; curr_promo = inp[7]
        otc_markup = inp[13] if inp[13] > 0 else 30.0
        rx_purch = inp[14]; otc_purch = inp[15]
        pharmacists = inp[16]; wage_pharm = inp[17]
        clerks = inp[18]; wage_clerk = inp[19]
        mgr_sal = inp[20]; mgr_hours = inp[22]
        mortgage = inp[23]; ap_paid = inp[28]
        
        # --- SALES ---
        cat = STORE_CATEGORY.get(ref_idx, "Neighbor")
        w = WEIGHTS[cat]
        base_in = BASELINE_INPUTS[ref_idx]
        base_env = {item['key']: item['value'] for item in ENV_MAPPING}
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env)
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], base_env)
        
        ratio = curr_score / base_score
        otc_mult = ratio * ((1 + 30/100) / (1 + otc_markup/100))
        
        actual_rx_vol = BASELINE_TARGETS['rx_demand'][ref_idx] * ratio
        actual_other_sales = BASELINE_TARGETS['other_sales'][ref_idx] * otc_mult
        actual_rx_price = env['avg_ing_cost'] * (1 + curr_markup/100)
        
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        # --- COGS & INVENTORY ---
        cogs_rx = sales_rx / (1 + curr_markup/100)
        cogs_other = actual_other_sales / (1 + otc_markup/100)
        total_cogs = cogs_rx + cogs_other
        
        avail_inv = fin['inventory'] + rx_purch + otc_purch
        e_rx_pur = 0; e_otc_pur = 0
        if total_cogs > avail_inv:
            shortage = total_cogs - avail_inv
            e_rx_pur = shortage * 0.7 * 1.1 
            e_otc_pur = shortage * 0.3 * 1.1
            total_cogs = avail_inv 
            
        # --- EXPENSES (Including Benefits & Insurance) ---
        weeks = 52.0 / env['periods_per_year']
        rp_base_hrs = min(curr_hours, 40); rp_ot_hrs = max(0, curr_hours - 40)
        clk_base_hrs = min(curr_hours, 40); clk_ot_hrs = max(0, curr_hours - 40)
        
        base_pharm_cost = pharmacists * rp_base_hrs * wage_pharm * weeks if pharmacists > 0 else 0
        ot_pharm_cost = pharmacists * rp_ot_hrs * wage_pharm * 1.5 * weeks if pharmacists > 0 else 0
        
        base_clerk_cost = clerks * clk_base_hrs * wage_clerk * weeks
        ot_clerk_cost = clerks * clk_ot_hrs * wage_clerk * 1.5 * weeks
        
        total_wages = base_pharm_cost + ot_pharm_cost + base_clerk_cost + ot_clerk_cost
        
        # Benefits: SS/WC + Life/Health Insurance (Inputs 32, 33 - Simplified cost)
        insurance_cost = 0
        if inp[32] == 1: insurance_cost += (pharmacists + clerks) * 100 # Life
        if inp[33] == 1: insurance_cost += (pharmacists + clerks) * 200 # Health
        
        benefits = total_wages * (env['ss_wc_rate'] / 100.0) + insurance_cost
        
        rent = total_sales * (0.045 if pid == 0 else 0.03)
        inf_factor = 1 + (env['inflation'] / 100.0)
        misc_ops = (total_sales * 0.015 + 2000) * inf_factor
        
        opex_cash = total_wages + benefits + rent + curr_promo + misc_ops + mgr_sal + mortgage
        
        # --- CASH FLOW (ACCOUNTING LOGIC FIX) ---
        # 1. Determine Credit vs Cash Sales
        # Credit comes from 3rd Party AND Store Credit
        pct_3rd = env['pct_3rd_party'] / 100.0
        pct_private = 1.0 - pct_3rd
        
        # If Store offers credit, assume 40% of private sales use it
        credit_offer_pct = 0.40 if curr_cred == 1 else 0.0
        
        pct_credit_sales = pct_3rd + (pct_private * credit_offer_pct)
        pct_cash_sales = 1.0 - pct_credit_sales
        
        # 2. Cash Inflow = Cash Sales + Collection of Prev AR
        cash_sales = total_sales * pct_cash_sales
        # Collection: 3rd Party Lag & AR Lag implies not 100% collected immediately
        # We collect most of the OLD AR.
        collection_from_ar = fin['ar'] * 0.90 
        
        cash_in = cash_sales + collection_from_ar
        
        # 3. New AR = Remaining Old AR + New Credit Sales
        new_credit_sales = total_sales * pct_credit_sales
        uncollected_old_ar = fin['ar'] * 0.10
        new_ar = uncollected_old_ar + new_credit_sales
        
        # 4. Outflows
        total_cash_out = opex_cash + ap_paid
        
        net_cash_flow = cash_in - total_cash_out
        temp_ending_cash = fin['cash'] + net_cash_flow
        
        # Emergency Loan Check
        e_loan = 0; interest = 0
        min_cash = inp[25] if inp[25] > 0 else 2500 # Use Input [25]
        
        if temp_ending_cash < min_cash:
            shortfall = min_cash - temp_ending_cash
            e_loan = shortfall
            temp_ending_cash = min_cash
            interest = e_loan * (env['interest_rate']/100.0) / env['periods_per_year']
        
        total_expenses_profit = opex_cash + interest
        gross_profit = total_sales - total_cogs
        net_profit = gross_profit - total_expenses_profit
        
        # --- FINANCIAL UPDATE ---
        fin['cash'] = temp_ending_cash
        fin['loan'] += e_loan
        fin['ap'] = fin['ap'] + rx_purch + otc_purch + e_rx_pur + e_otc_pur - ap_paid
        if fin['ap'] < 0: fin['ap'] = 0
        
        fin['inventory'] = fin['inventory'] + rx_purch + otc_purch + e_rx_pur + e_otc_pur - total_cogs
        fin['ar'] = new_ar
        
        total_assets = fin['cash'] + fin['inventory'] + fin['ar']
        total_liab = fin['ap'] + fin['loan']
        net_worth = total_assets - total_liab
        fin['net_worth'] = net_worth
        
        # --- OUTPUTS ---
        res = {}
        res["TOT SALES"] = total_sales
        res["Rx SALES"] = sales_rx
        res["OTH SALES"] = actual_other_sales
        res["A/P Paid"] = ap_paid
        res["Net Worth"] = net_worth
        res["Cash Flow"] = net_cash_flow
        res["Current"] = total_assets / total_liab if total_liab else 0
        res["Acid Test"] = (fin['cash'] + fin['ar']) / total_liab if total_liab else 0
        annual_cogs = total_cogs * env['periods_per_year']
        res["Turnover"] = annual_cogs / fin['inventory'] if fin['inventory'] else 0
        annual_profit = net_profit * env['periods_per_year']
        res["ROI"] = (annual_profit / net_worth) * 100 if net_worth else 0
        res["ROA"] = (annual_profit / total_assets) * 100 if total_assets else 0
        res["G Margin"] = (gross_profit / total_sales) * 100 if total_sales else 0
        res["Profit"] = net_profit
        res["Debt/NW"] = total_liab / net_worth if net_worth else 0
        res["LOCATION"] = p['type']
        res["DEBUG: Cash In"] = cash_in
        res["DEBUG: Cash Out"] = total_cash_out
        
        res["Avg Rx Pr"] = actual_rx_price
        res["Rx Ing $"] = env['avg_ing_cost']
        res["Rx GM%"] = (sales_rx - cogs_rx)/sales_rx if sales_rx else 0
        res["3-Pty GM%"] = ((actual_rx_price - env['avg_3rd_party_fee']) - env['avg_ing_cost']) / (actual_rx_price - env['avg_3rd_party_fee']) if actual_rx_price else 0
        res["Tot #Rx's"] = actual_rx_vol
        res["3-Pty #Rx"] = actual_rx_vol * (env['pct_3rd_party']/100.0)
        res["Copay Dis"] = copay_disc * actual_rx_vol 
        res["OTC M'kup"] = otc_markup
        res["Rx Mkt Sh"] = (actual_rx_vol / total_baseline_rx) * 100 
        res["Store Hrs"] = curr_hours
        res["M'age Pay"] = mortgage
        res["E. Loan"] = e_loan
        res["Mgr Hrs"] = mgr_hours
        res["RP OverT"] = ot_pharm_cost 
        res["RP Hr Pay"] = wage_pharm
        res["Clk OverT"] = ot_clerk_cost
        res["Clk Wage"] = wage_clerk
        res["Adv Exp"] = curr_promo
        res["E Rx Pur"] = e_rx_pur
        res["E OTC Pur"] = e_otc_pur
        
        p['history'].append(res)
        p['status'] = "Processed"
        
    st.session_state.current_period += 1

def get_leaderboard():
    data = []
    for pid, p in st.session_state.players.items():
        nw = p['financials']['net_worth']
        np_val = p['history'][-1]['Profit'] if p['history'] else 0
        data.append({"Store Name": p['name'], "Net Worth": nw, "Last Profit": np_val})
    df = pd.DataFrame(data).sort_values("Net Worth", ascending=False)
    ranks = ["🥇 1st", "🥈 2nd", "🥉 3rd"] + [f"{i+1}th" for i in range(3, len(df))]
    df.insert(0, "Rank", ranks[:len(df)])
    return df

# ==========================================
# 4. UI FUNCTIONS
# ==========================================
def render_instructor():
    st.header(f"👨‍🏫 Instructor Dashboard (Date: {get_current_date_str()})")
    
    if st.session_state.game_state == "SETUP":
        st.info("Step 1: Game Initialization")
        with st.form("setup_form"):
            n = st.number_input("Number of Stores (Max 7)", 1, 7, 7)
            if st.form_submit_button("✅ Start New Game"):
                init_game(n)
                st.rerun()
    else:
        tab1, tab2, tab3 = st.tabs(["📊 Reports", "⚙️ Environment", "🎮 Controls"])
        
        with tab1:
            st.subheader("📊 Full Market Report")
            if st.session_state.current_period > 1:
                combined_data = {}
                for pid, p in st.session_state.players.items():
                    if p['history']:
                        last_res = p['history'][-1]
                        combined_data[p['name']] = [last_res.get(k, 0) for k in OUTPUT_LABELS]
                
                df_combined = pd.DataFrame(combined_data, index=OUTPUT_LABELS)
                st.dataframe(df_combined.style.format(safe_fmt).apply(
                    lambda x: ['background-color: #ffcccc' if (x.name == "Cash Flow" and float(v) < 0) else '' for v in x], axis=1
                ), use_container_width=True, height=1000)
            else:
                st.info("Run Period 1 First")

        with tab2:
            st.subheader("⚙️ Market Variables")
            current_env_data = []
            for item in ENV_MAPPING:
                key = item['key']
                val = st.session_state.market_env.get(key, item['value'])
                current_env_data.append({"Variable Name": item['label'], "Value": val, "Key": key})
            
            df_env = pd.DataFrame(current_env_data)
            edited_df = st.data_editor(
                df_env[["Variable Name", "Value"]],
                use_container_width=True, height=800,
                column_config={"Variable Name": st.column_config.TextColumn("Variable", disabled=True), "Value": st.column_config.NumberColumn("Value", format="%.2f")}
            )
            
            if st.button("💾 Save Environment Changes"):
                for index, row in edited_df.iterrows():
                    key = current_env_data[index]['Key']
                    st.session_state.market_env[key] = row['Value']
                st.success("Environment Updated Successfully!")

        with tab3:
            st.subheader("🎮 Simulation Control")
            c1, c2 = st.columns([3, 1])
            with c1:
                status_data = [{"Store": p['name'], "Status": p['status']} for p in st.session_state.players.values()]
                st.dataframe(pd.DataFrame(status_data).T, use_container_width=True)
            with c2:
                if st.button("▶️ RUN PERIOD", type="primary", use_container_width=True):
                    run_period_simulation()
                    st.rerun()
            st.divider()
            if st.button("🔴 END GAME & RESET", type="secondary"):
                st.session_state.clear()
                st.rerun()

def render_student():
    if st.session_state.get('game_state') != "ACTIVE" or not st.session_state.get('players'):
        st.warning("⏳ Waiting for Instructor...")
        return

    st.header(f"🛒 Student Interface (Period {st.session_state.current_period})")
    store_ids = list(st.session_state.players.keys())
    labels = {i: f"{st.session_state.players[i]['name']} ({st.session_state.players[i]['status']})" for i in store_ids}
    sel_id = st.selectbox("Select Store:", store_ids, format_func=lambda x: labels[x])
    player = st.session_state.players[sel_id]
    
    tab1, tab2, tab3 = st.tabs(["📝 Input Decisions", "📊 Output/Results", "🏆 Rankings"])
    
    with tab1:
        st.caption("Edit values below. Press Enter to confirm/move.")
        df_input = pd.DataFrame({"Decision Parameter": INPUT_LABELS, "Value": player['inputs']})
        edited_inputs = st.data_editor(
            df_input, height=800, use_container_width=True, hide_index=True,
            column_config={"Decision Parameter": st.column_config.TextColumn(disabled=True), "Value": st.column_config.NumberColumn(format="%.2f")}
        )
        if st.button("✅ Submit Decisions", type="primary"):
            player['inputs'] = edited_inputs['Value'].tolist()
            player['status'] = "Submitted"
            st.success("Decisions Submitted Successfully!"); st.rerun()
                
    with tab2:
        if player['history']:
            st.subheader("Performance Report")
            data_dict = {}
            for i, h in enumerate(player['history']):
                p_label = f"Period {h.get('Period', i+1)}"
                data_dict[p_label] = [h.get(k, 0) for k in OUTPUT_LABELS]
            
            df_out = pd.DataFrame(data_dict, index=OUTPUT_LABELS)
            st.dataframe(df_out.style.format(safe_fmt), use_container_width=True, height=1000)
            
            st.info("🕵️ Debugging Cash Flow:")
            last_h = player['history'][-1]
            st.write(f"Cash In: {safe_fmt(last_h.get('DEBUG: Cash In', 0))}")
            st.write(f"Cash Out: {safe_fmt(last_h.get('DEBUG: Cash Out', 0))}")
            st.write(f"Net Cash Flow: {safe_fmt(last_h.get('Cash Flow', 0))}")
        else:
            st.info("Results will appear here after Period 1 is processed.")
            
    with tab3:
        st.dataframe(get_leaderboard(), use_container_width=True)

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
st.sidebar.title("💊 PharmaSim V56.0")

if st.sidebar.button("🔴 FORCE RESET & CLEAR DATA", type="primary"):
    force_reset()

role = st.sidebar.radio("Role:", ["Student", "Instructor"])

if role == "Instructor":
    if st.sidebar.text_input("🔑 Password", type="password") == "admin": render_instructor()
    else: st.info("Login required.")
else:
    render_student()
