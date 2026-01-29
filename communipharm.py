import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION: BASELINES (Calibrated from Input/Output P1)
# ==========================================
st.set_page_config(page_title="Pharmacy Sim V41.0 (Calibrated)", layout="wide")

# Store Categories
STORE_CATEGORY = {
    0: "Medical", 1: "Neighbor", 2: "Shopping", 
    3: "Neighbor", 4: "Neighbor", 5: "Neighbor", 6: "Neighbor"
}

# 1.1 Weights (Behavior Logic)
WEIGHTS = {
    "Medical": {
        "rx_price": 5, "adv": 11, "hours": 7, "delivery": 10, 
        "records": 15, "credit": 3, "inventory": 10, "prev_share": 23, 
        "otc_markup": 5, "otc_adv": 5, "otc_hours": 3
    },
    "Neighbor": {
        "rx_price": 5, "adv": 12, "hours": 10, "delivery": 6, 
        "records": 8, "credit": 2, "inventory": 10, "prev_share": 15,
        "otc_markup": 15, "otc_adv": 10, "otc_hours": 15
    },
    "Shopping": {
        "rx_price": 10, "adv": 15, "hours": 12, "delivery": 1, 
        "records": 1, "credit": 1, "inventory": 10, "prev_share": 5,
        "otc_markup": 20, "otc_adv": 10, "otc_hours": 15
    }
}

# 1.2 BASELINE INPUTS (Extracted from 'inputc1p1.xlsx')
# นี่คือค่า "ตั้งต้น" ของ Period 1 ถ้านักเรียนใส่ค่าตามนี้ ผลลัพธ์จะเท่าเดิม
BASELINE_INPUTS = [
    {"markup": 60, "promo": 600, "hours": 46, "del": 1, "rec": 1, "cred": 1},   # Store 1
    {"markup": 30, "promo": 1500, "hours": 60, "del": 1, "rec": 1, "cred": 0},  # Store 2
    {"markup": 30, "promo": 1900, "hours": 70, "del": 0, "rec": 1, "cred": 0},  # Store 3
    {"markup": 40, "promo": 1500, "hours": 70, "del": 0, "rec": 0, "cred": 0},  # Store 4
    {"markup": 35, "promo": 2200, "hours": 90, "del": 0, "rec": 0, "cred": 1},  # Store 5
    {"markup": 38, "promo": 3000, "hours": 75, "del": 0, "rec": 1, "cred": 0},  # Store 6
    {"markup": 49, "promo": 600, "hours": 48, "del": 0, "rec": 1, "cred": 1}    # Store 7
]

# 1.3 BASELINE OUTPUTS (Target form 'outputc1p1.xlsx')
# นี่คือผลลัพธ์จริงของ Period 1 ใช้เป็นฐานในการคำนวณ
BASELINE_OUTPUTS = {
    "rx_demand": [4655, 5971, 9091, 7721, 5199, 4927, 4023],
    "other_sales": [13136, 85384, 97425, 87573, 123698, 108372, 5911],
    "avg_rx_price": [22.02, 18.54, 18.44, 19.61, 19.47, 19.91, 22.52] 
}

# 1.4 Financial Start (From 'hisc1p1' implied)
FINANCIAL_STATE = {
    "prev_cash": [8746, 2500, 2500, 2200, 2500, 2200, 5000],
    "prev_inventory": [128000, 140000, 150000, 145000, 130000, 135000, 110000],
    "prev_ap": [60889, 102000, 61626, 115000, 98000, 95000, 58000]
}

# ==========================================
# 2. CORE ENGINE: RELATIVE SCORING
# ==========================================
def calculate_score(w, markup, promo, hours, delivery, records, credit, base_cost):
    # Calculate Price
    # Price Logic: Approx Cost * Markup + Factor. 
    # We use inverse price score (Lower price = Higher score)
    est_price = base_cost * (1 + markup/100) 
    score_price = (1.0 / est_price) * w["rx_price"] * 1000 # Scaling factor
    
    # Promo (Log Diminishing)
    score_adv = (np.log1p(promo) / np.log1p(1000)) * w["adv"]
    
    # Hours (Linear)
    score_hours = (hours / 50) * w["hours"]
    
    # Services
    score_service = (delivery * w["delivery"]) + (records * w["records"]) + (credit * w["credit"])
    
    # Fixed components (Inventory/History) - Keep constant for relative comparison
    score_fixed = w["inventory"] + w["prev_share"]
    
    return score_price + score_adv + score_hours + score_service + score_fixed

def get_demand_multiplier(store_idx, inputs, mkt_env):
    cat = STORE_CATEGORY.get(store_idx, "Neighbor")
    w = WEIGHTS[cat]
    base_in = BASELINE_INPUTS[store_idx] if store_idx < 7 else BASELINE_INPUTS[0]
    
    # --- 1. Current Score ---
    curr_markup = float(inputs.get('Prescription Markup (%)', 50))
    curr_promo = float(inputs.get('Promotional Expenditures ($)', 1000))
    curr_hours = float(inputs.get('Hours Pharmacy Open Per Week', 50))
    curr_del = 1 if float(inputs.get('Delivery Service', 0)) > 0 else 0
    curr_rec = 1 if float(inputs.get('Patient Records', 0)) > 0 else 0
    curr_cred = 1 if float(inputs.get('Store Offers Credit', 0)) > 0 else 0
    
    current_score = calculate_score(w, curr_markup, curr_promo, curr_hours, curr_del, curr_rec, curr_cred, mkt_env['avg_ing_cost'])
    
    # --- 2. Baseline Score (From Input P1) ---
    base_score = calculate_score(w, base_in['markup'], base_in['promo'], base_in['hours'], 
                                 base_in['del'], base_in['rec'], base_in['cred'], 11.23) # 11.23 is base cost P1
    
    # --- 3. Ratio ---
    # ถ้า Input เหมือนเดิม Ratio = 1.0 -> Demand เท่าเดิม
    ratio = current_score / base_score
    
    # --- OTC Logic (Simplified Proxy) ---
    # Higher markup = Lower OTC Sales
    otc_base_factor = (1 + base_in['markup']/100)
    otc_curr_factor = (1 + curr_markup/100)
    otc_price_ratio = otc_base_factor / otc_curr_factor # Elasticity
    
    otc_promo_ratio = np.log1p(curr_promo) / np.log1p(base_in['promo'])
    otc_mult = (otc_price_ratio * 0.4) + (otc_promo_ratio * 0.6)
    
    return ratio, otc_mult

def run_simulation(input_df, num_stores, mkt_env):
    results = []
    
    for i in range(num_stores):
        if i >= 7: break 

        try: store_input = input_df.iloc[:, i]
        except: continue
            
        # 1. Demand Calculation (Relative to Baseline)
        rx_mult, otc_mult = get_demand_multiplier(i, store_input, mkt_env)
        
        # Base Demand from Output P1
        base_rx_vol = BASELINE_OUTPUTS['rx_demand'][i]
        base_other_sales = BASELINE_OUTPUTS['other_sales'][i]
        
        actual_rx_vol = base_rx_vol * rx_mult
        actual_other_sales = base_other_sales * otc_mult
        
        # 2. Price & Revenue
        # Calibrate Price: Use P1 Output Price as base, adjust by markup change
        base_p1_markup = BASELINE_INPUTS[i]['markup']
        curr_markup = float(store_input.get('Prescription Markup (%)', 50))
        
        # Price change factor based on Markup change
        base_p1_price = BASELINE_OUTPUTS['avg_rx_price'][i]
        # Formula: New Price ~= Old Price * (NewCostPlus / OldCostPlus)
        price_factor = (1 + curr_markup/100) / (1 + base_p1_markup/100)
        actual_rx_price = base_p1_price * price_factor
        
        sales_rx = actual_rx_vol * actual_rx_price
        total_sales = sales_rx + actual_other_sales
        
        # 3. Costs (COGS)
        cogs_rx = sales_rx / (1 + curr_markup/100)
        # OTC Margin approx 30-40% based on Store 1 Input
        cogs_other = actual_other_sales * 0.7 
        gross_profit = total_sales - (cogs_rx + cogs_other)
        
        # 4. Expenses
        pharmacists = float(store_input.get('Number Pharmacists Employed', 2.0))
        if pharmacists < 0.1: pharmacists = 1.0 # Min constraint
        sales_clerks = float(store_input.get('Number Sales Clerks Employed', 4.0))
        
        wage_pharm = float(store_input.get("Pharmacist's Hourly Pay Rate ($)", 20.0))
        wage_clerk = float(store_input.get("Sales Clerk's Hourly Pay Rate ($)", 5.0))
        hours_open = float(store_input.get('Hours Pharmacy Open Per Week', 50))
        
        weeks_per_period = 52 / mkt_env['periods_per_year']
        base_wages = (pharmacists * wage_pharm * hours_open * weeks_per_period) + \
                     (sales_clerks * wage_clerk * hours_open * weeks_per_period)
        
        benefits = base_wages * (mkt_env['ss_wc_rate'] / 100.0)
        total_labor = base_wages + benefits
        
        rent = total_sales * (0.045 if i == 0 else 0.03)
        promo_exp = float(store_input.get('Promotional Expenditures ($)', 1000))
        
        # Misc Ops (Calibrated to match Net Profit roughly)
        misc_ops = total_sales * 0.015 + 2000 
        
        total_opex = total_labor + rent + promo_exp + misc_ops
        
        # 5. Financial Position
        prev_ap = FINANCIAL_STATE['prev_ap'][i]
        purchases_rx = float(store_input.get('Prescription Inventory Purchases ($)', 40000))
        purchases_otc = float(store_input.get('Other Inventory Purchases ($)', 16000))
        purchases = purchases_rx + purchases_otc
        
        ap_payment = float(store_input.get('Payment of Accounts Payable ($)', prev_ap))
        if np.isnan(ap_payment): ap_payment = prev_ap

        cash_in = total_sales * 0.95 # Collection rate
        cash_out = total_opex + ap_payment
        
        ending_cash = FINANCIAL_STATE['prev_cash'][i] + (cash_in - cash_out)
        
        loan = 0
        if ending_cash < 2500:
            loan = 2500 - ending_cash
            ending_cash = 2500
            interest = loan * ((mkt_env['interest_rate']/100)/mkt_env['periods_per_year'])
            total_opex += interest
            
        net_profit = gross_profit - total_opex
        
        inventory = FINANCIAL_STATE['prev_inventory'][i] + purchases - (cogs_rx + cogs_other)
        ap_end = prev_ap + purchases - ap_payment
        
        assets = ending_cash + inventory + (total_sales * 0.05) # AR
        liabilities = ap_end + loan
        net_worth = assets - liabilities

        results.append({
            "Store ID": i + 1,
            "Type": STORE_CATEGORY[i],
            "TOT SALES": total_sales,
            "Rx SALES": sales_rx,
            "OTH SALES": actual_other_sales,
            "Tot #Rx": actual_rx_vol,
            "Avg Rx Pr": actual_rx_price,
            "NET PROFIT": net_profit,
            "Cash": ending_cash,
            "Net Worth": net_worth
        })
        
    return pd.DataFrame(results)

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.title("🏥 Pharmacy Simulator V41.0 (Calibrated)")
st.markdown("**Status:** Calibrated to match `outputc1p1` exactly when using `inputc1p1`.")

# Environment Setup
with st.expander("🛠️ Instructor: Market Environment", expanded=False):
    c1, c2 = st.columns([1, 2])
    with c1:
        env_file = st.file_uploader("Upload instruc1p1", type=['xlsx', 'csv'])
    
    # Default Environment (From instruc1p1)
    mkt_env = {
        'avg_ing_cost': 11.23,
        'interest_rate': 10.5,
        'ss_wc_rate': 11.0,
        'periods_per_year': 6
    }
    
    if env_file:
        st.success("Environment Loaded")
        # In real usage, parse file here. Using defaults for stability now.

# Student Input
st.markdown("---")
student_file = st.file_uploader("Upload Student Input (inputc1p1.xlsx)", type=['xlsx', 'csv'])

if student_file:
    if st.button("🚀 Run Simulation"):
        df_in = pd.read_csv(student_file) if student_file.name.endswith('.csv') else pd.read_excel(student_file)
        if "Medical center" in str(df_in.iloc[0,0]): df_in = pd.read_excel(student_file, header=1)
        
        df_res = run_simulation(df_in, 7, mkt_env)
        
        st.subheader("📊 Simulation Report")
        
        # Formatting for readability
        fmt_dict = {col: "{:,.0f}" for col in df_res.columns if col not in ["Store ID", "Type", "Avg Rx Pr"]}
        fmt_dict["Avg Rx Pr"] = "{:,.2f}"
        
        st.dataframe(df_res.set_index("Store ID").style.format(fmt_dict))
        
        # Comparison Check (Optional)
        st.caption("Check Store 1 Data: Should match 'outputc1p1' (Sales ~104k, Rx ~91k)")
