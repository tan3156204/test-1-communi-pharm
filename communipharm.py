import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 0. FORCE RESET UTILITY
# ==========================================
# ฟังก์ชันนี้จะช่วยล้างค่าขยะที่ค้างอยู่ใน Memory ของ Streamlit
def force_reset():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.set_page_config(page_title="PharmaSim V55 (Debug Mode)", layout="wide")

# ==========================================
# 1. CONSTANTS & CALIBRATION
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

# Values from Input C1P1 (Corrected)
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
    
    # Financial Initialization 
    # Store 1 Target: Cash ~8k, Inv ~120k, AR ~20k, AP ~60k -> NW ~90-100k
    init_cash = [8746, 2500, 2500, 2200, 2500, 2200, 5000]
    
    for i in range(n_stores):
        ref_idx = i if i < 7 else 0 
        base = BASELINE_INPUTS[ref_idx]
        
        # --- Defaults Setup ---
        d = [0.0] * 36
        d[0] = float(base['markup'])
        d[3] = float(base['del']); d[4] = float(base['rec']); d[5] = float(base['cred'])
        d[6] = float(base['hours']); d[7] = float(base['promo'])
        
        # Purchases (CRITICAL for AP Calc)
        d[14] = float(base['rx_pur'])
        d[15] = float(base['otc_pur'])
        
        # Labor
        d[16] = float(base['pharm']) 
        d[17] = 20.0 # Pharm Rate
        d[18] = 4.0 
        d[19] = 5.0 
        d[20] = 8000.0 # Mgr Salary
        
        # Financials
        d[28] = float(base['ap_paid']) # This is what you PAY this period
        
        # Beginning Balance Logic
        # We assume Beginning AP was roughly equal to what they decided to pay
        # This ensures they don't start with massive debt
        init_ap_val = base['ap_paid'] 
        init_ar_val = 22000 
        init_inv = 130000 # Approx
        
        nw_start = init_cash[ref_idx] + init_inv + init_ar_val - init_ap_val
        
        st.session_state.players[i] = {
            "name": f"Store {i+1}",
            "type": STORE_CATEGORY.get(ref_idx, "Neighbor"),
            "inputs": d,
            "financials": {
                "cash": init_cash[ref_idx],
                "inventory": init_inv,
                "ar": init_ar_val, 
                "ap": init_ap_val, # Beginning AP
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
    total_baseline_rx = sum(BASELINE_TARGETS['rx_demand'])
    
    for pid, p in st.session_state.players.items():
        ref_idx = pid if pid < 7 else 0
        inp = p['inputs']
        fin = p['financials']
        
        # --- 1. EXTRACT INPUTS ---
        curr_markup = inp[0]; copay_disc = inp[2]
        curr_del = inp[3]; curr_rec = inp[4]; curr_cred = inp[5]
        curr_hours = inp[6]; curr_promo = inp[7]
        otc_markup = inp[13] if inp[13] > 0 else 30.0
        rx_purch = inp[14]; otc_purch = inp[15]
        pharmacists = inp[16]; wage_pharm = inp[17]
        clerks = inp[18]; wage_clerk = inp[19]
        mgr_sal = inp[20]; mgr_hours = inp[22]
        mortgage = inp[23]; ap_paid = inp[28] # Value from input (approx 60k-100k)
        
        # --- 2. SALES ---
        cat = STORE_CATEGORY.get(ref_idx, "Neighbor")
        w = WEIGHTS[cat]
        base_in = BASELINE_INPUTS[ref_idx]
        
        curr_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, env)
        base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], base_in['del'], base_in['rec'], base_in['cred'], env)
        ratio = curr_score / base_score
        
        actual_rx_vol = BASELINE_TARGETS['rx_demand'][ref_idx] * ratio
        actual_other_sales = BASELINE_TARGETS['other_sales'][ref_idx] * ratio
        
        actual_rx_price = env['avg_ing_cost'] * (1 + curr_markup/100)
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        # --- 3. COGS & EXPENSES ---
        cogs_rx = sales_rx / (1 + curr_markup/100)
        cogs_other = actual_other_sales / (1 + otc_markup/100)
        total_cogs = cogs_rx + cogs_other
        
        weeks = 52.0 / env['periods_per_year']
        labor_cost = (pharmacists * curr_hours * wage_pharm * weeks) + (clerks * curr_hours * wage_clerk * weeks)
        if pharmacists == 0: labor_cost = (clerks * curr_hours * wage_clerk * weeks) # Owner works
        
        opex_cash = labor_cost + mgr_sal + rent = (total_sales * 0.03) + curr_promo + 2000
        
        # --- 4. CASH FLOW DEBUGGING ---
        # Beginning Cash
        start_cash = fin['cash']
        
        # Cash In
        # Assume 80% of Sales collected immediately + 20% of OLD AR
        # Simplified: Cash In = Total Sales (assuming steady state for simplicity)
        cash_in = total_sales * 0.90 # 90% collection rate
        
        # Cash Out
        # THIS IS THE KEY: Cash Out = Expenses + AP Payment
        # ap_paid comes from Input. If Input says 60,000, we pay 60,000.
        total_cash_out = opex_cash + ap_paid
        
        net_cash_flow = cash_in - total_cash_out
        
        end_cash = start_cash + net_cash_flow
        
        # --- 5. FINANCIAL POSITION UPDATE ---
        # Update AP
        # New AP = Old AP + New Purchases - Paid
        old_ap = fin['ap']
        new_ap = old_ap + rx_purch + otc_purch - ap_paid
        if new_ap < 0: new_ap = 0 # Cannot have negative debt
        
        fin['ap'] = new_ap
        fin['cash'] = end_cash
        fin['ar'] = (fin['ar'] + total_sales) - cash_in
        fin['inventory'] = fin['inventory'] + rx_purch + otc_purch - total_cogs
        
        # --- 6. OUTPUTS ---
        res = {}
        res["TOT SALES"] = total_sales
        res["Rx SALES"] = sales_rx
        res["OTH SALES"] = actual_other_sales
        res["A/P Paid"] = ap_paid
        res["Net Worth"] = (fin['cash'] + fin['inventory'] + fin['ar']) - (fin['ap'] + fin['loan'])
        res["Cash Flow"] = net_cash_flow
        
        # DIAGNOSTIC FIELDS (To find the -900k culprit)
        res["[DEBUG] Start AP"] = old_ap
        res["[DEBUG] Purchases"] = rx_purch + otc_purch
        res["[DEBUG] AP Paid"] = ap_paid
        res["[DEBUG] End AP"] = new_ap
        res["[DEBUG] Cash In"] = cash_in
        res["[DEBUG] Cash Out"] = total_cash_out
        
        # Standard Ratios
        res["Current"] = (fin['cash'] + fin['ar'] + fin['inventory']) / fin['ap'] if fin['ap'] > 0 else 99
        res["Profit"] = total_sales - total_cogs - opex_cash
        
        # Fill rest with 0 for compatibility
        for k in OUTPUT_LABELS:
            if k not in res: res[k] = 0
            
        p['history'].append(res)
        p['status'] = "Processed"
        
    st.session_state.current_period += 1

# ==========================================
# 4. UI
# ==========================================
st.sidebar.title("💊 PharmaSim V55 (Reset Tool)")

if st.sidebar.button("🔴 FORCE RESET & CLEAR DATA", type="primary"):
    force_reset()

role = st.sidebar.radio("Role:", ["Student", "Instructor"])

def safe_fmt(x):
    return "{:,.2f}".format(x) if isinstance(x, (int, float)) else x

if role == "Instructor":
    st.header("👨‍🏫 Instructor (Diagnostics)")
    
    if st.session_state.game_state == "SETUP":
        if st.button("Start Game"):
            init_game(7)
            st.rerun()
    else:
        if st.button("▶️ Run Period"):
            run_period_simulation()
            st.rerun()
            
        st.divider()
        st.subheader("🕵️ CASH FLOW INVESTIGATION")
        if st.session_state.current_period > 1:
            debug_data = []
            for name, p in st.session_state.players.items():
                if p['history']:
                    last = p['history'][-1]
                    debug_data.append({
                        "Store": p['name'],
                        "1. Cash In (Sales)": safe_fmt(last.get("[DEBUG] Cash In", 0)),
                        "2. OpEx (Labor/Rent)": safe_fmt(last.get("Cash Out", 0) - last.get("A/P Paid", 0)), # Approx
                        "3. AP Paid (The Culprit?)": safe_fmt(last.get("[DEBUG] AP Paid", 0)),
                        "4. Total Cash Out": safe_fmt(last.get("[DEBUG] Cash Out", 0)),
                        "5. Net Cash Flow": safe_fmt(last.get("Cash Flow", 0)),
                        "6. Ending AP Debt": safe_fmt(last.get("[DEBUG] End AP", 0))
                    })
            st.dataframe(pd.DataFrame(debug_data))
            
            st.subheader("📊 Full Report")
            full_data = {p['name']: [p['history'][-1][k] for k in OUTPUT_LABELS] for p in st.session_state.players.values()}
            st.dataframe(pd.DataFrame(full_data, index=OUTPUT_LABELS).style.format(safe_fmt))

else:
    st.header("Student View")
    if st.session_state.game_state == "ACTIVE":
        sel = st.selectbox("Store", list(st.session_state.players.keys()))
        p = st.session_state.players[sel]
        
        with st.expander("Edit Inputs", expanded=True):
            df_in = pd.DataFrame({"Param": INPUT_LABELS, "Value": p['inputs']})
            edited = st.data_editor(df_in, use_container_width=True, height=600)
            if st.button("Save"):
                p['inputs'] = edited['Value'].tolist()
                st.success("Saved")
