import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONSTANTS & BASELINE DATA
# ==========================================
st.set_page_config(page_title="PharmaSim V53.0 (Tabbed UI)", layout="wide")

# Store Categories
STORE_CATEGORY = {
    0: "Medical", 1: "Neighbor", 2: "Shopping", 
    3: "Neighbor", 4: "Neighbor", 5: "Neighbor", 6: "Neighbor"
}

# Weights
WEIGHTS = {
    "Medical": {"rx_price": 5, "adv": 11, "hours": 7, "delivery": 10, "records": 15, "credit": 3, "inventory": 10, "prev_share": 23, "otc_markup": 5, "otc_adv": 5, "otc_hours": 3},
    "Neighbor": {"rx_price": 5, "adv": 12, "hours": 10, "delivery": 6, "records": 8, "credit": 2, "inventory": 10, "prev_share": 15, "otc_markup": 15, "otc_adv": 10, "otc_hours": 15},
    "Shopping": {"rx_price": 10, "adv": 15, "hours": 12, "delivery": 1, "records": 1, "credit": 1, "inventory": 10, "prev_share": 5, "otc_markup": 20, "otc_adv": 10, "otc_hours": 15}
}

# Baseline Inputs
BASELINE_INPUTS = [
    {"markup": 60, "promo": 600, "hours": 46, "del": 1, "rec": 1, "cred": 1},
    {"markup": 30, "promo": 1500, "hours": 60, "del": 1, "rec": 1, "cred": 0},
    {"markup": 30, "promo": 1900, "hours": 70, "del": 0, "rec": 1, "cred": 0},
    {"markup": 40, "promo": 1500, "hours": 70, "del": 0, "rec": 0, "cred": 0},
    {"markup": 35, "promo": 2200, "hours": 90, "del": 0, "rec": 0, "cred": 1},
    {"markup": 38, "promo": 3000, "hours": 75, "del": 0, "rec": 1, "cred": 0},
    {"markup": 49, "promo": 600, "hours": 48, "del": 0, "rec": 1, "cred": 1}
]

# Baseline Targets
BASELINE_TARGETS = {
    "rx_demand": [4655, 5971, 9091, 7721, 5199, 4927, 4023],
    "other_sales": [13136, 85384, 97425, 87573, 123698, 108372, 5911],
    "avg_rx_price": [22.02, 18.54, 18.44, 19.61, 19.47, 19.91, 22.52] 
}

# Initial Financial State
INIT_FINANCIALS = {
    "cash": [8746, 2500, 2500, 2200, 2500, 2200, 5000],
    "inventory": [128000, 140000, 150000, 145000, 130000, 135000, 110000],
    "ap": [60889, 102000, 61626, 115000, 98000, 95000, 58000],
    "ar": [22000, 35000, 40000, 38000, 36000, 32000, 18000]
}

# Env Mapping
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
    "ROI", "ROA", "G Margin", "Profit", "Debt/NW", "LOCATION"
]

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
if 'game_state' not in st.session_state:
    st.session_state.game_state = "SETUP"
    st.session_state.current_period = 1
    st.session_state.num_stores = 7
    st.session_state.market_env = {item['key']: item['value'] for item in ENV_MAPPING}
    st.session_state.players = {} 

def init_game(n_stores):
    st.session_state.players = {}
    st.session_state.current_period = 1
    st.session_state.market_env = {item['key']: item['value'] for item in ENV_MAPPING}
    
    for i in range(n_stores):
        ref_idx = i if i < 7 else 0 
        base = BASELINE_INPUTS[ref_idx]
        
        default_inputs = [0.0] * 36
        default_inputs[0] = float(base['markup'])
        default_inputs[3] = float(base['del'])
        default_inputs[4] = float(base['rec'])
        default_inputs[5] = float(base['cred'])
        default_inputs[6] = float(base['hours'])
        default_inputs[7] = float(base['promo'])
        default_inputs[14] = 40000.0 if ref_idx == 0 else 60000.0
        default_inputs[15] = 16000.0 if ref_idx == 0 else 80000.0
        default_inputs[28] = float(INIT_FINANCIALS['ap'][ref_idx])
        default_inputs[16] = 1.0 if ref_idx != 0 else 0.0
        default_inputs[17] = 20.0
        default_inputs[18] = 4.0
        default_inputs[19] = 5.0
        default_inputs[20] = 8000.0

        init_nw = INIT_FINANCIALS['cash'][ref_idx] + INIT_FINANCIALS['inventory'][ref_idx] + INIT_FINANCIALS['ar'][ref_idx] - INIT_FINANCIALS['ap'][ref_idx]

        st.session_state.players[i] = {
            "name": f"Store {i+1}",
            "type": STORE_CATEGORY.get(ref_idx, "Neighbor"),
            "inputs": default_inputs,
            "financials": {
                "cash": INIT_FINANCIALS['cash'][ref_idx],
                "inventory": INIT_FINANCIALS['inventory'][ref_idx],
                "ar": INIT_FINANCIALS['ar'][ref_idx], 
                "ap": INIT_FINANCIALS['ap'][ref_idx],
                "loan": 0,
                "net_worth": init_nw
            },
            "status": "Pending",
            "history": []
        }
    st.session_state.num_stores = n_stores
    st.session_state.game_state = "ACTIVE"

def reset_game():
    st.session_state.game_state = "SETUP"
    st.session_state.players = {}
    st.session_state.current_period = 1
    st.rerun()

# ==========================================
# 3. CORE LOGIC
# ==========================================
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
        
        curr_markup = inp[0]; copay_disc = inp[2]
        curr_del = inp[3]; curr_rec = inp[4]; curr_cred = inp[5]
        curr_hours = inp[6]; curr_promo = inp[7]
        otc_markup = inp[13] if inp[13] > 0 else 30.0
        rx_purch = inp[14]; otc_purch = inp[15]
        pharmacists = inp[16]
        wage_pharm = inp[17]
        clerks = inp[18]; wage_clerk = inp[19]
        mgr_sal = inp[20]; mgr_hours = inp[22]
        mortgage = inp[23]; ap_paid = inp[28]
        
        cat = STORE_CATEGORY.get(ref_idx, "Neighbor")
        w = WEIGHTS[cat]
        base_in = BASELINE_INPUTS[ref_idx]
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env)
        base_env = {item['key']: item['value'] for item in ENV_MAPPING}
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], base_env)
        
        ratio = curr_score / base_score
        otc_price_ratio = (1 + 30/100) / (1 + otc_markup/100) 
        otc_mult = ratio * otc_price_ratio
        
        actual_rx_vol = BASELINE_TARGETS['rx_demand'][ref_idx] * ratio
        actual_other_sales = BASELINE_TARGETS['other_sales'][ref_idx] * otc_mult
        
        avg_ing_cost = env['avg_ing_cost']
        actual_rx_price = avg_ing_cost * (1 + curr_markup/100)
        
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        pct_3rd = env['pct_3rd_party'] / 100.0
        vol_3rd = actual_rx_vol * pct_3rd
        
        cogs_rx = sales_rx / (1 + curr_markup/100)
        cogs_other = actual_other_sales / (1 + otc_markup/100)
        total_cogs = cogs_rx + cogs_other
        
        avail_inv = fin['inventory'] + rx_purch + otc_purch
        e_rx_pur = 0; e_otc_pur = 0
        if total_cogs > avail_inv:
            shortage = total_cogs - avail_inv
            e_rx_pur = shortage * 0.7 * 1.1 
            e_otc_pur = shortage * 0.3 * 1.1
            
        weeks = 52.0 / env['periods_per_year']
        rp_base_hrs = min(curr_hours, 40)
        rp_ot_hrs = max(0, curr_hours - 40)
        
        if pharmacists > 0:
            base_pharm_cost = pharmacists * rp_base_hrs * wage_pharm * weeks
            ot_pharm_cost = pharmacists * rp_ot_hrs * wage_pharm * 1.5 * weeks
        else:
            base_pharm_cost = 0; ot_pharm_cost = 0
            
        clk_base_hrs = min(curr_hours, 40)
        clk_ot_hrs = max(0, curr_hours - 40)
        base_clerk_cost = clerks * clk_base_hrs * wage_clerk * weeks
        ot_clerk_cost = clerks * clk_ot_hrs * wage_clerk * 1.5 * weeks
        
        benefits = (base_pharm_cost + base_clerk_cost + ot_pharm_cost + ot_clerk_cost) * (env['ss_wc_rate'] / 100.0)
        rent = total_sales * (0.045 if pid == 0 else 0.03)
        misc_ops = (total_sales * 0.015 + 2000) * (env['inflation'] / 1.0) 
        
        total_opex_cash = base_pharm_cost + ot_pharm_cost + base_clerk_cost + ot_clerk_cost + benefits + rent + curr_promo + misc_ops + mgr_sal + mortgage
        
        receivables_pool = fin['ar'] + total_sales 
        collection_rate = 0.95 - (max(0, env['pct_3rd_party'] - 40) * 0.005)
        
        cash_in = receivables_pool * collection_rate
        new_ar = receivables_pool - cash_in
        
        total_cash_out = total_opex_cash + ap_paid
        net_cash_flow = cash_in - total_cash_out
        temp_ending_cash = fin['cash'] + net_cash_flow
        
        e_loan = 0
        interest = 0
        if temp_ending_cash < 2500:
            shortfall = 2500 - temp_ending_cash
            e_loan = shortfall
            temp_ending_cash = 2500
            interest = e_loan * ((env['interest_rate']/100)/env['periods_per_year'])
        
        total_expenses_profit = total_opex_cash + interest
        gross_profit = total_sales - total_cogs
        net_profit = gross_profit - total_expenses_profit
        
        fin['cash'] = temp_ending_cash
        fin['loan'] += e_loan
        fin['ap'] = fin['ap'] + (rx_purch + otc_purch + e_rx_pur + e_otc_pur) - ap_paid
        fin['inventory'] = fin['inventory'] + (rx_purch + otc_purch + e_rx_pur + e_otc_pur) - total_cogs
        fin['ar'] = new_ar
        
        total_assets = fin['cash'] + fin['inventory'] + fin['ar']
        total_liab = fin['ap'] + fin['loan']
        net_worth = total_assets - total_liab
        fin['net_worth'] = net_worth
        
        res = {}
        res["TOT SALES"] = total_sales
        res["Rx SALES"] = sales_rx
        res["OTH SALES"] = actual_other_sales
        res["Avg Rx Pr"] = actual_rx_price
        res["Rx Ing $"] = avg_ing_cost
        res["Rx GM%"] = (sales_rx - cogs_rx)/sales_rx if sales_rx else 0
        res["3-Pty GM%"] = ((actual_rx_price - env['avg_3rd_party_fee']) - avg_ing_cost) / (actual_rx_price - env['avg_3rd_party_fee']) if actual_rx_price else 0
        res["Tot #Rx's"] = actual_rx_vol
        res["3-Pty #Rx"] = vol_3rd
        res["Copay Dis"] = copay_disc * actual_rx_vol 
        res["OTC M'kup"] = otc_markup
        res["Rx Mkt Sh"] = (actual_rx_vol / total_baseline_rx) * 100 
        res["Store Hrs"] = curr_hours
        res["A/P Paid"] = ap_paid
        res["M'age Pay"] = mortgage
        res["E. Loan"] = e_loan
        res["Mgr Hrs"] = mgr_hours
        res["RP OverT"] = ot_pharm_cost 
        res["RP Hr Pay"] = wage_pharm
        res["Clk OverT"] = ot_clerk_cost
        res["Clk Wage"] = wage_clerk
        res["Adv Exp"] = curr_promo
        res["Net Worth"] = net_worth
        res["Cash Flow"] = net_cash_flow
        res["E Rx Pur"] = e_rx_pur
        res["E OTC Pur"] = e_otc_pur
        res["RATIOS"] = np.nan 
        
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
        
        p['history'].append(res)
        p['status'] = "Pending"
        
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

def get_current_date_str():
    env = st.session_state.market_env
    d = env.get('date_day', 30)
    m = env.get('date_month', 6)
    y = env.get('date_year', 89)
    return f"{int(d)}/{int(m)}/19{int(y)}"

def safe_format(x):
    if isinstance(x, (int, float)):
        return "{:,.2f}".format(x)
    return str(x)

# ==========================================
# 5. UI LAYOUT
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
        # --- TABBED INTERFACE (NEW) ---
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Reports", "⚙️ Environment Settings", "🎮 Game Controls"])
        
        with tab1:
            st.subheader("🏆 Live Leaderboard")
            st.dataframe(get_leaderboard().style.format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)
            st.divider()
            
            st.subheader(f"📊 Full Market Report (Period {st.session_state.current_period - 1})")
            if st.session_state.current_period > 1:
                combined_data = {}
                for pid, p in st.session_state.players.items():
                    if p['history']:
                        last_res = p['history'][-1]
                        combined_data[p['name']] = [last_res.get(k, 0) for k in OUTPUT_LABELS]
                
                df_combined = pd.DataFrame(combined_data, index=OUTPUT_LABELS)
                st.dataframe(df_combined.style.format(safe_format), use_container_width=True, height=1000)
            else:
                st.info("No data available yet. Run Period 1 first.")
        
        with tab2:
            st.subheader(f"⚙️ Environment Control: Period {st.session_state.current_period}")
            st.caption("Double click any value to edit. Press ENTER to move to next row.")
            
            current_env_data = []
            for item in ENV_MAPPING:
                current_val = st.session_state.market_env.get(item['key'], item['value'])
                current_env_data.append({"Variable Name": item['label'], "Value": current_val, "Key": item['key']})
                
            df_env = pd.DataFrame(current_env_data)
            edited_df = st.data_editor(
                df_env[["Variable Name", "Value"]],
                use_container_width=True, height=600,
                column_config={"Variable Name": st.column_config.TextColumn("Variable", disabled=True), "Value": st.column_config.NumberColumn("Value", format="%.2f")}
            )
            if st.button("💾 Save Environment Changes"):
                for index, row in edited_df.iterrows():
                    key = ENV_MAPPING[index]['key']
                    st.session_state.market_env[key] = row['Value']
                st.success("Environment Updated Successfully!")

        with tab3:
            st.subheader("🎮 Simulation Control")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write("Student Status:")
                status_data = [{"Store": p['name'], "Status": p['status']} for p in st.session_state.players.values()]
                st.dataframe(pd.DataFrame(status_data).T, use_container_width=True)
            with c2:
                st.write("Actions:")
                if st.button("▶️ RUN PERIOD", type="primary", use_container_width=True):
                    run_period_simulation()
                    st.rerun()
            st.divider()
            if st.button("🔴 END GAME & RESET", type="secondary"):
                reset_game()

def render_student():
    if st.session_state.game_state == "SETUP":
        st.warning("⏳ Waiting for Instructor...")
        return

    st.header(f"🛒 Student Interface (Period {st.session_state.current_period} - Ends {get_current_date_str()})")
    store_ids = list(st.session_state.players.keys())
    labels = {i: f"{st.session_state.players[i]['name']} ({st.session_state.players[i]['status']})" for i in store_ids}
    sel_id = st.selectbox("Select Store:", store_ids, format_func=lambda x: labels[x])
    player = st.session_state.players[sel_id]
    
    new_name = st.text_input("Store Name:", value=player['name'])
    if new_name != player['name']: player['name'] = new_name; st.rerun()
        
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
            st.dataframe(df_out.style.format(safe_format), use_container_width=True, height=1000)
        else:
            st.info("Results will appear here after Period 1 is processed.")
            
    with tab3:
        st.dataframe(get_leaderboard().style.apply(lambda x: ['background: #e6ffe6' if x['Store Name'] == player['name'] else '' for i in x], axis=1).format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)

# ==========================================
# 6. MAIN APP
# ==========================================
st.sidebar.title("💊 PharmaSim V53 (Fixed UI)")
role = st.sidebar.radio("Role:", ["Student", "Instructor"])

if role == "Instructor":
    if st.sidebar.text_input("🔑 Password", type="password") == "admin": render_instructor()
    else: st.info("Login required.")
else: render_student()
