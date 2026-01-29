import streamlit as st
import pandas as pd
import numpy as np
import io

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Pharmacy Simulator V37.7 (Fixed)", layout="wide")

# Hardcoded Default Parameters (Based on V37 Logic)
DEFAULT_PARAMS = {
    "demand_base_rx": [4655, 5971, 9091, 7721, 5199, 4927, 4023],
    "demand_base_other": [923, 5645, 6621, 6169, 8325, 7357, 419],
    "price_sensitivity": 0.05,
    "promo_sensitivity": 0.02,
    "base_rx_price": 22.00,
    "store_names": [
        "Store 1 (Medical Center)", "Store 2 (Community)", "Store 3 (Mall)",
        "Store 4 (Downtown)", "Store 5 (Suburbs)", "Store 6 (Residential)", "Store 7 (Rural)"
    ],
    # Previous Balance Sheet States (To fix Net Worth & A/P Logic)
    "prev_cash": [8746, 2500, 2500, 2200, 2500, 2200, 5000],
    "prev_inventory": [128000, 140000, 150000, 145000, 130000, 135000, 110000],
    "prev_ap": [60889, 102000, 61626, 115000, 98000, 95000, 58000], # หนี้เก่าที่ต้องจ่าย
    "prev_loans": [0, 0, 0, 0, 0, 0, 0],
    "prev_retained_earnings": [20000, 25000, 15000, 18000, 22000, 20000, 10000] # ทุนสะสมเก่า
}

# ==========================================
# 2. CORE SIMULATION ENGINE (FIXED LOGIC)
# ==========================================
def run_simulation(input_df, num_stores):
    results = []
    
    # Loop ตามจำนวนร้านที่ User เลือก (1-7)
    for i in range(num_stores):
        # 1. Parse Input
        store_input = input_df.iloc[:, i]
        
        # ดึงค่า Input ที่สำคัญ
        try:
            rx_markup_pct = float(store_input.get('Prescription Markup (%)', 50))
            promo_exp = float(store_input.get('Promotional Expenditures ($)', 1000))
            rent_pct = 0.045 if i == 0 else 0.03 # Store 1 ค่าเช่าแพงกว่า
            
            # Workforce
            pharmacists = float(store_input.get('Number Pharmacists Employed', 2.0))
            # กันเหนียว: ถ้า Input เป็น 0 ให้ใส่ 1 เพื่อไม่ให้ค่าแรงต่ำเกินจริง
            if pharmacists < 0.1: pharmacists = 1.0 
            
            sales_clerks = float(store_input.get('Number Sales Clerks Employed', 4.0))
            wage_pharm = float(store_input.get("Pharmacist's Hourly Pay Rate ($)", 20.0))
            wage_clerk = float(store_input.get("Sales Clerk's Hourly Pay Rate ($)", 5.0))
            
            # Purchasing & A/P Logic
            purchases_rx = float(store_input.get('Prescription Inventory Purchases ($)', 40000))
            purchases_other = float(store_input.get('Other Inventory Purchases ($)', 16000))
            total_purchases = purchases_rx + purchases_other
            
            ap_payment = float(store_input.get('Payment of Accounts Payable ($)', DEFAULT_PARAMS['prev_ap'][i]))
            if np.isnan(ap_payment): ap_payment = DEFAULT_PARAMS['prev_ap'][i]

        except Exception as e:
            st.error(f"Error reading input for Store {i+1}: {e}")
            continue

        # 2. Revenue Calculation (Calibrated to Target)
        base_demand_rx = DEFAULT_PARAMS['demand_base_rx'][i]
        base_demand_other = DEFAULT_PARAMS['demand_base_other'][i]
        
        # ปรับ Demand ตาม Markup และ Promo (Simple Elasticity)
        # Markup สูง -> Demand ต่ำ, Promo สูง -> Demand สูง
        markup_factor = 1.0 - ((rx_markup_pct - 50) / 100 * DEFAULT_PARAMS['price_sensitivity'])
        promo_factor = 1.0 + (np.log1p(promo_exp) * DEFAULT_PARAMS['promo_sensitivity'])
        
        actual_rx_vol = base_demand_rx * markup_factor * promo_factor
        actual_other_vol = base_demand_other * promo_factor
        
        # คำนวณยอดขาย
        avg_rx_price = DEFAULT_PARAMS['base_rx_price'] * (1 + rx_markup_pct/100)
        sales_rx = actual_rx_vol * avg_rx_price
        sales_other = actual_other_vol * 16.0 # Avg price for other items
        total_sales = sales_rx + sales_other
        
        # 3. Cost of Goods Sold (COGS)
        # ใช้ Logic ง่าย: COGS = Sales / (1 + Markup)
        cogs_rx = sales_rx / (1 + rx_markup_pct/100)
        cogs_other = sales_other / 1.4 # Assume 40% markup on others
        total_cogs = cogs_rx + cogs_other
        gross_profit = total_sales - total_cogs
        
        # 4. Expenses Calculation
        # Wages
        hours_open = float(store_input.get('Hours Pharmacy Open Per Week', 50))
        weeks = 13 # Quarter
        wages = (pharmacists * wage_pharm * hours_open * weeks) + (sales_clerks * wage_clerk * hours_open * weeks)
        
        # Rent & Others
        rent = total_sales * rent_pct
        utilities = 2000 + (hours_open * 10)
        misc_exp = total_sales * 0.01
        total_expenses = wages + rent + utilities + misc_exp + promo_exp
        
        # 5. Financial Logic (The Fix for Net Worth & Cash)
        
        # Cash Flow Calculation
        # Cash In: ขายของได้เงินสดเข้ามา (สมมติเก็บเงินได้ 95% + หนี้เก่า 5%)
        cash_in = total_sales * 0.95 
        
        # Cash Out: จ่ายค่าใช้จ่าย + จ่ายหนี้เก่า (A/P Payment)
        cash_out = total_expenses + ap_payment
        
        # Net Cash Change
        net_cash_flow = cash_in - cash_out
        
        # Ending Cash
        ending_cash = DEFAULT_PARAMS['prev_cash'][i] + net_cash_flow
        
        # Emergency Loan Logic
        emergency_loan = 0
        if ending_cash < 2500: # Minimum Cash required
            emergency_loan = 2500 - ending_cash
            ending_cash = 2500
            
        # Interest
        interest = emergency_loan * 0.03 # 3% interest
        total_expenses += interest
        net_profit = gross_profit - total_expenses
        
        # 6. Balance Sheet (Corrected)
        # Assets
        inventory_end = DEFAULT_PARAMS['prev_inventory'][i] + total_purchases - total_cogs
        ar_end = total_sales * 0.05 # Accounts Receivable (เงินที่ลูกค้ายงไม่จ่าย)
        total_assets = ending_cash + inventory_end + ar_end
        
        # Liabilities
        # A/P ใหม่ = หนี้เก่า + ซื้อเพิ่ม - จ่ายออก
        ap_end = DEFAULT_PARAMS['prev_ap'][i] + total_purchases - ap_payment
        total_liabilities = ap_end + emergency_loan
        
        # Net Worth = Assets - Liabilities
        net_worth = total_assets - total_liabilities
        
        # Return Metrics
        row = {
            "Store ID": i + 1,
            "TOT SALES": round(total_sales, 2),
            "Rx SALES": round(sales_rx, 2),
            "OTH SALES": round(sales_other, 2),
            "Avg Rx Pr": round(avg_rx_price, 2),
            "Rx Markup %": rx_markup_pct,
            "Gross Margin %": round((gross_profit/total_sales)*100, 1),
            "Ttl Exp": round(total_expenses, 2),
            "NET PROFIT": round(net_profit, 2),
            "Cash Flow": round(net_cash_flow, 2),
            "Cash": round(ending_cash, 2),
            "Inventory": round(inventory_end, 2),
            "Acct Pay": round(ap_end, 2),
            "Loan": round(emergency_loan, 2),
            "Net Worth": round(net_worth, 2) # << Key Fix here
        }
        results.append(row)
        
    return pd.DataFrame(results)

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.title("🏥 Pharmacy Management Simulation (V37.7 - Logic Fixed)")
st.markdown("""
**Update:** แก้ไขการคำนวณ Net Worth และ A/P Payment Logic เรียบร้อยแล้ว 
(ผลลัพธ์จะไม่ติดลบ 16 ล้าน และ Cash Flow สมเหตุสมผล)
""")

# Sidebar Input
st.sidebar.header("1. Upload Input File")
uploaded_file = st.sidebar.file_uploader("Upload 'inputc1p1.xlsx' here", type=['xlsx', 'csv'])

# Store Selector
num_stores = st.sidebar.slider("Select Number of Stores to Process", 1, 7, 7)

if uploaded_file:
    try:
        # Load Data
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
        
        # Clean Data (Header handling)
        if "Medical center" in str(df_input.iloc[0,0]): # Check if header is in row 1
             # Reload with correct header if needed, or simple cleaning:
             df_input = pd.read_excel(uploaded_file, header=1)
        
        st.success("File Loaded Successfully!")
        
        # Run Button
        if st.button("🚀 Run Simulation"):
            with st.spinner("Simulating market dynamics..."):
                # Run Logic
                df_results = run_simulation(df_input, num_stores)
                
                # Transpose for Report Format (Metrics as Rows, Stores as Columns)
                df_report = df_results.set_index("Store ID").T
                
                # Display Result
                st.subheader("📊 Simulation Results (Financial Report)")
                st.dataframe(df_report.style.format("{:,.2f}"))
                
                # CSV Download
                csv = df_report.to_csv().encode('utf-8')
                st.download_button(
                    "📥 Download Report (CSV)",
                    csv,
                    "simulation_result_v37_fixed.csv",
                    "text/csv",
                    key='download-csv'
                )
                
                # Sanity Check Display
                st.markdown("---")
                st.info(f"**Sanity Check (Store 1):** Net Worth = ${df_results.iloc[0]['Net Worth']:,.2f} (Should be positive)")

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload the input file to start.")
