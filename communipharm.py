import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 0. FORCE RESET UTILITY (ONLY NEW THING ADDED)
# ==========================================
def force_reset():
    st.session_state.clear()
    st.rerun()

st.set_page_config(page_title="PharmaSim V54 (Fixed)", layout="wide")

# ==========================================
# 1. CONSTANTS
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

# Original V54 Inputs
BASELINE_INPUTS = [
    {"markup": 60, "promo": 600, "hours": 46, "del": 1, "rec": 1, "cred": 1, "pharm": 0, "ap_paid": 60889, "rx_pur": 40000, "otc_pur": 16000},
    {"markup": 30, "promo": 1500, "hours": 60, "del": 1, "rec": 1, "cred": 0, "pharm": 1, "ap_paid": 102000, "rx_pur": 60000, "otc_pur": 80000},
    {"markup": 30, "promo": 1900, "hours": 70, "del": 0, "rec": 1, "cred": 0, "pharm": 1.3, "ap_paid": 61626, "rx_pur": 65000, "otc_pur": 120000},
    {"markup": 40, "promo": 1500, "hours": 70, "del": 0, "rec": 0, "cred": 0, "pharm": 1.5, "ap_paid": 115000, "rx_pur": 65000, "otc_pur": 145000},
    {"markup": 35, "promo": 2200, "hours": 90, "del": 0, "rec": 0, "cred": 1, "pharm": 1.5, "ap_paid": 98000, "rx_pur": 85000, "otc_pur": 145000},
    {"markup": 38, "promo": 3000, "hours": 75, "del": 0, "rec": 1, "cred": 0, "pharm": 1.75, "ap_paid": 95000, "rx_pur": 65000, "otc_pur": 175000},
    {"markup": 49, "promo": 600, "hours": 48, "del": 0, "rec": 1, "cred": 1, "pharm": 1, "ap_paid": 58000, "rx_pur": 40000, "otc_pur": 24000}
]

BASELINE_TARGETS = {
    "rx_demand": [4655, 5971, 9091, 7721, 5199, 4927, 4023],
    "other_sales": [13136, 85384, 97425, 87573, 123698, 108372, 5911],
}

ENV_MAPPING = [
    {"key": "avg_ing_cost", "value": 11.23},
    {"key": "avg_copay", "value": 2.0},
    {"key": "avg_3rd_party_fee", "value": 2.75},
    {"key": "pct_3rd_party", "value": 46.43},
    {"key": "interest_rate", "value": 10.5},
    {"key": "inflation", "value": 1.1},
    {"key": "ss_wc_rate", "value": 11.0},
    {"key": "periods_per_year", "value": 6},
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
    
    init_cash = [8746, 2500, 2500, 2200, 2500, 2200, 5000]
    
    for i in range(n_stores):
        ref_idx = i if i < 7 else 0 
        base = BASELINE_INPUTS[ref_idx]
        
        d = [0.0] * 36
        d[0] = float(base['markup'])
        d[3] = float(base['del']); d[4] = float(base['rec']); d[5] = float(base['cred'])
        d[6] = float(base['hours']); d[7] = float(base['promo'])
        
        d[14] = float(base['rx_pur'])
        d[15] = float(base['otc_pur'])
        
        d[16] = float(base['pharm']) 
        d[17] = 20.0 
        d[18] = 4.0 
        d[19] = 5.0 
        d[20] = 8000.0 
        d[28] = float(base['ap_paid']) 
        
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

# ==========================================
# 3. CORE LOGIC
# ==========================================
def calculate_score(w, markup, promo, hours, delivery, records, credit, env):
    est_price = env['avg_ing_cost'] * (1 + markup/100) 
    score_price = (1.0 / est_price) * w["rx_price"] * 1000 
    score_adv = (np.log1p(promo) / np.log1p(1200)) * w["adv"]
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
        curr_markup = inp[0]; copay_disc = inp[2]
        curr_del = inp[3]; curr_rec = inp[4]; curr_cred = inp[5]
        curr_hours = inp[6]; curr_promo = inp[7]
        otc_markup = inp[13] if inp[13] > 0 else 30.0
        rx_purch = inp[14]; otc_purch = inp[15]
        pharmacists = inp[16]; wage_pharm = inp[17]
        clerks = inp[18]; wage_clerk = inp[19]
        mgr_sal = inp[20]; mgr_hours = inp[22]
        mortgage = inp[23]; ap_paid = inp[28]
        
        # Sales
        cat = STORE_CATEGORY.get(ref_idx, "Neighbor")
        w = WEIGHTS[cat]
        base_in = BASELINE_INPUTS[ref_idx]
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env)
        base_env = {item['key']: item['value'] for item in ENV_MAPPING}
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], base_env)
        ratio = curr_score / base_score
        
        otc_mult = ratio * ((1 + 30/100) / (1 + otc_markup/100))
        
        actual_rx_vol = BASELINE_TARGETS['rx_demand'][ref_idx] * ratio
        actual_other_sales = BASELINE_TARGETS['other_sales'][ref_idx] * otc_mult
        
        actual_rx_price = env['avg_ing_cost'] * (1 + curr_markup/100)
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        # COGS & Expenses
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
            
        weeks = 52.0 / env['periods_per_year']
        labor_cost = (pharmacists * curr_hours * wage_pharm * weeks) + (clerks * curr_hours * wage_clerk * weeks)
        if pharmacists == 0: labor_cost = (clerks * curr_hours * wage_clerk * weeks) 
        
        # FIX SYNTAX ERROR HERE (Separated properly)
        rent = total_sales * 0.03
        misc_ops = 2000
        opex_cash = labor_cost + mgr_sal + rent + curr_promo + misc_ops + mortgage
        
        # Cash Flow
        cash_in = total_sales * 0.90
        total_cash_out = opex_cash + ap_paid
        net_cash_flow = cash_in - total_cash_out
        end_cash = fin['cash'] + net_cash_flow
        
        # Emergency Loan
        e_loan = 0; interest = 0
        if end_cash < 2500:
            e_loan = 2500 - end_cash
            end_cash = 2500
            interest = e_loan * (env['interest_rate']/100.0) / env['periods_per_year']
        
        total_expenses_profit = opex_cash + interest
        gross_profit = total_sales - total_cogs
        net_profit = gross_profit - total_expenses_profit
        
        # Financial Update
        fin['cash'] = end_cash
        fin['loan'] += e_loan
        fin['ap'] = fin['ap'] + rx_purch + otc_purch + e_rx_pur + e_otc_pur - ap_paid
        if fin['ap'] < 0: fin['ap'] = 0
        
        fin['inventory'] = fin['inventory'] + rx_purch + otc_purch + e_rx_pur + e_otc_pur - total_cogs
        fin['ar'] = (fin['ar'] + total_sales) - cash_in
        
        total_assets = fin['cash'] + fin['inventory'] + fin['ar']
        total_liab = fin['ap'] + fin['loan']
        net_worth = total_assets - total_liab
        fin['net_worth'] = net_worth
        
        # Outputs
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
        
        for k in OUTPUT_LABELS:
            if k not in res: res[k] = 0
            
        p['history'].append(res)
        p['status'] = "Processed"
        
    st.session_state.current_period += 1

# ==========================================
# 4. UI
# ==========================================
st.sidebar.title("💊 PharmaSim V54 (Fixed)")

# RESET BUTTON ADDED HERE
if st.sidebar.button("🔴 FORCE RESET & CLEAR DATA", type="primary"):
    force_reset()

role = st.sidebar.radio("Role:", ["Student", "Instructor"])

def safe_fmt(x):
    return "{:,.2f}".format(x) if isinstance(x, (int, float)) else x

if role == "Instructor":
    st.header("👨‍🏫 Instructor")
    
    if st.session_state.game_state == "SETUP":
        if st.button("Start Game"):
            init_game(7)
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
                st.dataframe(df_combined.style.format(safe_fmt), use_container_width=True, height=1000)
            else:
                st.info("Run Period 1 First")

        with tab2:
            st.subheader("⚙️ Env")
            df_env = pd.DataFrame([{"Variable": k, "Value": v} for k, v in st.session_state.market_env.items()])
            st.dataframe(df_env, use_container_width=True)

        with tab3:
            c1, c2 = st.columns([3, 1])
            with c1:
                status_data = [{"Store": p['name'], "Status": p['status']} for p in st.session_state.players.values()]
                st.dataframe(pd.DataFrame(status_data).T, use_container_width=True)
            with c2:
                if st.button("▶️ RUN PERIOD", type="primary"):
                    run_period_simulation()
                    st.rerun()

else:
    st.header("Student View")
    if st.session_state.game_state == "ACTIVE":
        sel = st.selectbox("Store", list(st.session_state.players.keys()))
        p = st.session_state.players[sel]
        
        tab1, tab2 = st.tabs(["📝 Inputs", "📊 Results"])
        with tab1:
            df_in = pd.DataFrame({"Param": INPUT_LABELS, "Value": p['inputs']})
            edited = st.data_editor(df_in, use_container_width=True, height=600)
            if st.button("Save"):
                p['inputs'] = edited['Value'].tolist()
                st.success("Saved")
        with tab2:
            if p['history']:
                st.dataframe(pd.DataFrame(p['history']).T, use_container_width=True)
