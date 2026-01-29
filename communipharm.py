import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONSTANTS & BASELINE DATA
# ==========================================
st.set_page_config(page_title="PharmaSim V48.0 (Complete Env)", layout="wide")

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
    "ap": [60889, 102000, 61626, 115000, 98000, 95000, 58000]
}

# --- ENV CONFIG MAPPING (Complete List) ---
# Key = Internal Variable Name, Label = Display Name in Table, Value = Default from instruc1p1
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
]

INPUT_LABELS = [
    "Prescription Markup (%)", "Promotional Expenditures ($)", "Hours Pharmacy Open Per Week",
    "Number Pharmacists Employed", "Pharmacist's Hourly Pay Rate ($)",
    "Number Sales Clerks Employed", "Sales Clerk's Hourly Pay Rate ($)",
    "Delivery Service (1=Yes,0=No)", "Patient Records (1=Yes,0=No)", "Store Offers Credit (1=Yes,0=No)",
    "Prescription Inventory Purchases ($)", "Other Inventory Purchases ($)", "Payment of Accounts Payable ($)"
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
        default_inputs = [
            base['markup'], base['promo'], base['hours'], 
            2.0, 20.0, 4.0, 5.0,
            base['del'], base['rec'], base['cred'],
            40000, 16000, INIT_FINANCIALS['ap'][ref_idx]
        ]
        
        init_nw = INIT_FINANCIALS['cash'][ref_idx] + INIT_FINANCIALS['inventory'][ref_idx] - INIT_FINANCIALS['ap'][ref_idx]

        st.session_state.players[i] = {
            "name": f"Store {i+1}",
            "type": STORE_CATEGORY.get(ref_idx, "Neighbor"),
            "inputs": default_inputs,
            "financials": {
                "cash": INIT_FINANCIALS['cash'][ref_idx],
                "inventory": INIT_FINANCIALS['inventory'][ref_idx],
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
    
    # Use max_promo from environment
    max_promo_val = env.get('max_promo', 1200)
    score_adv = (np.log1p(promo) / np.log1p(max_promo_val)) * w["adv"]
    
    score_hours = (hours / 50) * w["hours"]
    score_service = (delivery * w["delivery"]) + (records * w["records"]) + (credit * w["credit"])
    score_fixed = w["inventory"] + w["prev_share"]
    return score_price + score_adv + score_hours + score_service + score_fixed

def run_period_simulation():
    env = st.session_state.market_env
    
    for pid, p in st.session_state.players.items():
        ref_idx = pid if pid < 7 else 0
        inp = p['inputs']
        fin = p['financials']
        
        # Inputs
        curr_markup = inp[0]; curr_promo = inp[1]; curr_hours = inp[2]
        curr_del = inp[7]; curr_rec = inp[8]; curr_cred = inp[9]
        
        # Demand Logic
        cat = STORE_CATEGORY.get(ref_idx, "Neighbor")
        w = WEIGHTS[cat]
        base_in = BASELINE_INPUTS[ref_idx]
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env)
        base_env = {item['key']: item['value'] for item in ENV_MAPPING}
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], base_env)
        
        ratio = curr_score / base_score
        
        otc_price_ratio = (1 + base_in['markup']/100) / (1 + curr_markup/100)
        otc_promo_ratio = np.log1p(curr_promo) / np.log1p(base_in['promo'])
        otc_mult = (otc_price_ratio * 0.4) + (otc_promo_ratio * 0.6)
        
        # Sales
        actual_rx_vol = BASELINE_TARGETS['rx_demand'][ref_idx] * ratio
        actual_other_sales = BASELINE_TARGETS['other_sales'][ref_idx] * otc_mult
        
        base_p1_price = BASELINE_TARGETS['avg_rx_price'][ref_idx]
        price_factor = (1 + curr_markup/100) / (1 + base_in['markup']/100)
        actual_rx_price = base_p1_price * price_factor
        
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        # Profit
        cogs_rx = sales_rx / (1 + curr_markup/100)
        cogs_other = actual_other_sales * 0.7 
        gross_profit = total_sales - (cogs_rx + cogs_other)
        
        # Expenses
        pharmacists = max(inp[3], 1.0)
        sales_clerks = inp[5]
        wage_pharm = inp[4]; wage_clerk = inp[6]
        
        weeks = 52 / env['periods_per_year']
        base_wages = (pharmacists * wage_pharm * curr_hours * weeks) + (sales_clerks * wage_clerk * curr_hours * weeks)
        benefits = base_wages * (env['ss_wc_rate'] / 100.0)
        rent = total_sales * (0.045 if pid == 0 else 0.03)
        misc_ops = (total_sales * 0.015 + 2000) * (env['inflation'] / 1.0) 
        
        purchases = inp[10] + inp[11]
        ap_payment = inp[12]
        
        # Cash Flow Logic with 3rd Party Impact
        # Basic Collection logic: if 3rd party % is high, collection is slower (simulated)
        collection_rate = 0.95 - (max(0, env['pct_3rd_party'] - 40) * 0.005)
        cash_in = total_sales * collection_rate
        
        total_opex_pre_interest = base_wages + benefits + rent + curr_promo + misc_ops
        temp_cash_out = total_opex_pre_interest + ap_payment
        temp_ending_cash = fin['cash'] + (cash_in - temp_cash_out)
        
        loan = 0
        interest = 0
        if temp_ending_cash < 2500:
            loan = 2500 - temp_ending_cash
            temp_ending_cash = 2500
            interest = loan * ((env['interest_rate']/100)/env['periods_per_year'])
        
        total_opex = total_opex_pre_interest + interest
        net_profit = gross_profit - total_opex
        
        # Update Fin
        fin['cash'] = temp_ending_cash
        fin['ap'] = fin['ap'] + purchases - ap_payment
        fin['inventory'] = fin['inventory'] + purchases - (cogs_rx + cogs_other)
        fin['loan'] += loan
        
        assets = fin['cash'] + fin['inventory'] + (total_sales * (1-collection_rate))
        liabilities = fin['ap'] + fin['loan']
        net_worth = assets - liabilities
        
        fin['net_worth'] = net_worth
        
        p['history'].append({
            "Period": st.session_state.current_period,
            "TOT SALES": total_sales,
            "NET PROFIT": net_profit,
            "Net Worth": net_worth,
            "Cash": fin['cash'],
            "Loan": fin['loan']
        })
        p['status'] = "Pending"
        
    st.session_state.current_period += 1

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def get_leaderboard():
    data = []
    for pid, p in st.session_state.players.items():
        nw = p['financials']['net_worth']
        np_val = p['history'][-1]['NET PROFIT'] if p['history'] else 0
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
        st.subheader("🏆 Live Leaderboard")
        st.dataframe(get_leaderboard().style.format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)
        st.divider()
        
        # --- TABLE BASED ENV CONTROL ---
        st.subheader(f"⚙️ Environment Control: Period {st.session_state.current_period}")
        st.caption("Double click any value to edit. Press ENTER to move to next row.")
        
        # Construct Table Data
        current_env_data = []
        for item in ENV_MAPPING:
            current_val = st.session_state.market_env.get(item['key'], item['value'])
            current_env_data.append({"Variable Name": item['label'], "Value": current_val, "Key": item['key']})
            
        df_env = pd.DataFrame(current_env_data)
        
        edited_df = st.data_editor(
            df_env[["Variable Name", "Value"]],
            use_container_width=True,
            height=800, # Increased height for full list
            column_config={
                "Variable Name": st.column_config.TextColumn("Variable", disabled=True),
                "Value": st.column_config.NumberColumn("Value", format="%.2f")
            }
        )
        
        if st.button("💾 Save Environment Changes"):
            for index, row in edited_df.iterrows():
                key = ENV_MAPPING[index]['key']
                st.session_state.market_env[key] = row['Value']
            st.success("Environment Updated Successfully!")

        # Status & Run
        st.divider()
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
        st.caption("Edit values in the table below. Press Enter to confirm/move.")
        df_input = pd.DataFrame({"Decision Parameter": INPUT_LABELS, "Value": player['inputs']})
        
        edited_inputs = st.data_editor(
            df_input,
            height=500,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Decision Parameter": st.column_config.TextColumn(disabled=True),
                "Value": st.column_config.NumberColumn(format="%.2f")
            }
        )
        
        if st.button("✅ Submit Decisions", type="primary"):
            player['inputs'] = edited_inputs['Value'].tolist()
            player['status'] = "Submitted"
            st.success("Decisions Submitted Successfully!"); st.rerun()
                
    with tab2:
        if player['history']:
            st.subheader("Performance History")
            hist = pd.DataFrame(player['history']).set_index("Period")
            st.dataframe(hist.style.format("{:,.2f}"), use_container_width=True)
            
            last = player['history'][-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Net Worth", f"${last['Net Worth']:,.0f}")
            c2.metric("Net Profit", f"${last['NET PROFIT']:,.0f}")
            c3.metric("Cash on Hand", f"${last['Cash']:,.0f}")
        else:
            st.info("Results will appear here after Period 1 is processed.")
            
    with tab3:
        st.dataframe(get_leaderboard().style.apply(lambda x: ['background: #e6ffe6' if x['Store Name'] == player['name'] else '' for i in x], axis=1).format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)

# ==========================================
# 6. MAIN APP
# ==========================================
st.sidebar.title("💊 PharmaSim V48")
role = st.sidebar.radio("Role:", ["Student", "Instructor"])

if role == "Instructor":
    if st.sidebar.text_input("🔑 Password", type="password") == "admin": render_instructor()
    else: st.info("Login required.")
else: render_student()
