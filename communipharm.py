import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONSTANTS & BASELINE DATA
# ==========================================
st.set_page_config(page_title="PharmaSim V43.0 (Leaderboard)", layout="wide")

# Store Categories & Weights
STORE_CATEGORY = {
    0: "Medical", 1: "Neighbor", 2: "Shopping", 
    3: "Neighbor", 4: "Neighbor", 5: "Neighbor", 6: "Neighbor"
}
WEIGHTS = {
    "Medical": {"rx_price": 5, "adv": 11, "hours": 7, "delivery": 10, "records": 15, "credit": 3, "inventory": 10, "prev_share": 23, "otc_markup": 5, "otc_adv": 5, "otc_hours": 3},
    "Neighbor": {"rx_price": 5, "adv": 12, "hours": 10, "delivery": 6, "records": 8, "credit": 2, "inventory": 10, "prev_share": 15, "otc_markup": 15, "otc_adv": 10, "otc_hours": 15},
    "Shopping": {"rx_price": 10, "adv": 15, "hours": 12, "delivery": 1, "records": 1, "credit": 1, "inventory": 10, "prev_share": 5, "otc_markup": 20, "otc_adv": 10, "otc_hours": 15}
}

# Baseline Inputs (Reference P1)
BASELINE_INPUTS = [
    {"markup": 60, "promo": 600, "hours": 46, "del": 1, "rec": 1, "cred": 1},
    {"markup": 30, "promo": 1500, "hours": 60, "del": 1, "rec": 1, "cred": 0},
    {"markup": 30, "promo": 1900, "hours": 70, "del": 0, "rec": 1, "cred": 0},
    {"markup": 40, "promo": 1500, "hours": 70, "del": 0, "rec": 0, "cred": 0},
    {"markup": 35, "promo": 2200, "hours": 90, "del": 0, "rec": 0, "cred": 1},
    {"markup": 38, "promo": 3000, "hours": 75, "del": 0, "rec": 1, "cred": 0},
    {"markup": 49, "promo": 600, "hours": 48, "del": 0, "rec": 1, "cred": 1}
]

# Baseline Targets (Reference P1 Output)
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

# Initial Environment
INIT_ENV = {
    'avg_ing_cost': 11.23, 'interest_rate': 10.5, 'ss_wc_rate': 11.0, 'periods_per_year': 6, 'inflation': 1.1
}

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
    st.session_state.market_env = INIT_ENV.copy()
    st.session_state.players = {} 

def init_game(n_stores):
    st.session_state.players = {}
    st.session_state.current_period = 1
    st.session_state.market_env = INIT_ENV.copy()
    
    for i in range(n_stores):
        ref_idx = i if i < 7 else 0 
        base = BASELINE_INPUTS[ref_idx]
        default_inputs = [
            base['markup'], base['promo'], base['hours'], 
            2.0, 20.0, 4.0, 5.0,
            base['del'], base['rec'], base['cred'],
            40000, 16000, INIT_FINANCIALS['ap'][ref_idx]
        ]
        
        # Calculate Initial Net Worth (Approx) for Display
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
def calculate_score(w, markup, promo, hours, delivery, records, credit, base_cost):
    est_price = base_cost * (1 + markup/100) 
    score_price = (1.0 / est_price) * w["rx_price"] * 1000 
    score_adv = (np.log1p(promo) / np.log1p(1000)) * w["adv"]
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
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env['avg_ing_cost'])
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], 11.23)
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
        misc_ops = total_sales * 0.015 + 2000
        
        # Interest & Loan
        purchases = inp[10] + inp[11]
        ap_payment = inp[12]
        
        cash_in = total_sales * 0.95
        total_opex_pre_interest = base_wages + benefits + rent + curr_promo + misc_ops
        
        # Temporary cash check for loan
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
        
        assets = fin['cash'] + fin['inventory'] + (total_sales * 0.05)
        liabilities = fin['ap'] + fin['loan']
        net_worth = assets - liabilities
        
        fin['net_worth'] = net_worth # Store for leaderboard
        
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
        data.append({
            "Store Name": p['name'],
            "Net Worth": nw,
            "Last Profit": np_val
        })
    df = pd.DataFrame(data).sort_values("Net Worth", ascending=False)
    
    # Add Rank Emoji
    ranks = []
    for i in range(len(df)):
        if i == 0: ranks.append("🥇 1st")
        elif i == 1: ranks.append("🥈 2nd")
        elif i == 2: ranks.append("🥉 3rd")
        else: ranks.append(f"{i+1}th")
    df.insert(0, "Rank", ranks)
    return df

# ==========================================
# 5. UI LAYOUT
# ==========================================

# --- INSTRUCTOR ---
def render_instructor():
    st.header("👨‍🏫 Instructor Dashboard")
    
    if st.session_state.game_state == "SETUP":
        st.info("Step 1: Game Initialization")
        with st.form("setup_form"):
            n = st.number_input("Number of Stores (Max 7)", 1, 7, 7)
            if st.form_submit_button("✅ Start New Game"):
                init_game(n)
                st.rerun()
    else:
        # Leaderboard
        st.subheader("🏆 Live Leaderboard")
        df_rank = get_leaderboard()
        st.dataframe(df_rank.style.format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)
        
        st.divider()
        
        # Simulation Control
        st.subheader(f"⚙️ Control Panel: Period {st.session_state.current_period}")
        with st.expander("🌍 Environment Settings", expanded=False):
            c1, c2, c3 = st.columns(3)
            env = st.session_state.market_env
            new_int = c1.number_input("Interest %", value=env['interest_rate'])
            new_tax = c2.number_input("SS&WC %", value=env['ss_wc_rate'])
            new_cost = c3.number_input("Ing Cost $", value=env['avg_ing_cost'])
            if st.button("Update Env"):
                env.update({'interest_rate': new_int, 'ss_wc_rate': new_tax, 'avg_ing_cost': new_cost})
                st.success("Saved!")

        # Status & Run
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
                
        # --- RESET BUTTON ---
        st.divider()
        st.warning("⛔ Danger Zone")
        if st.button("🔴 END GAME & RESET", type="secondary"):
            reset_game()

# --- STUDENT ---
def render_student():
    if st.session_state.game_state == "SETUP":
        st.warning("⏳ Waiting for Instructor to start the game...")
        return

    st.header(f"🛒 Student Interface (Period {st.session_state.current_period})")
    
    store_ids = list(st.session_state.players.keys())
    labels = {i: f"{st.session_state.players[i]['name']} ({st.session_state.players[i]['status']})" for i in store_ids}
    sel_id = st.selectbox("Select Store:", store_ids, format_func=lambda x: labels[x])
    player = st.session_state.players[sel_id]
    
    new_name = st.text_input("Store Name:", value=player['name'])
    if new_name != player['name']:
        player['name'] = new_name
        st.rerun()
        
    tab1, tab2, tab3 = st.tabs(["📝 Decisions", "📊 My Results", "🏆 Rankings"])
    
    with tab1:
        with st.form("input_form"):
            df_input = pd.DataFrame({"Parameter": INPUT_LABELS, "Value": player['inputs']})
            edited = st.data_editor(df_input, height=450, use_container_width=True, hide_index=True, column_config={"Value": st.column_config.NumberColumn(format="%.2f")})
            if st.form_submit_button("✅ Submit"):
                player['inputs'] = edited['Value'].tolist()
                player['status'] = "Submitted"
                st.success("Submitted!")
                st.rerun()
                
    with tab2:
        if player['history']:
            hist = pd.DataFrame(player['history']).set_index("Period")
            st.dataframe(hist.style.format("{:,.2f}"), use_container_width=True)
            last = player['history'][-1]
            st.metric("Current Net Worth", f"${last['Net Worth']:,.0f}", delta=f"Profit: ${last['NET PROFIT']:,.0f}")
        else:
            st.info("Results will appear here after Period 1.")
            
    with tab3:
        st.subheader("Current Market Standings")
        df_rank = get_leaderboard()
        # Highlight user row
        st.dataframe(df_rank.style.apply(lambda x: ['background: #e6ffe6' if x['Store Name'] == player['name'] else '' for i in x], axis=1).format({"Net Worth": "${:,.0f}", "Last Profit": "${:,.0f}"}), use_container_width=True)

# ==========================================
# 6. MAIN APP
# ==========================================
st.sidebar.title("💊 PharmaSim V43")
role = st.sidebar.radio("Role:", ["Student", "Instructor"])

if role == "Instructor":
    pwd = st.sidebar.text_input("🔑 Password", type="password")
    if pwd == "admin": render_instructor()
    else: st.info("Login required.")
else:
    render_student()
