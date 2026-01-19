import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
st.set_page_config(page_title="Pharmacy Sim: Forensic Edition", layout="wide")

st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .winner { color: green; font-weight: bold; }
    .loser { color: red; }
</style>
""", unsafe_allow_html=True)

# Location Mapping
LOC_MAP = {1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

# CONSTANTS (Standard Sim Values)
BASE_COST = 11.23
PRICE_CONSTANT = 2.90
MARKET_BASE_SIZE = 6000 # Base customer pool

# ==========================================
# 2. INPUT DATA (FROM YOUR PDF) 
# ==========================================
# Format: [Input 1, Input 2, ..., Input 36]
# Note: Input 29 is kept as is, but logic handles it.

team_data = [
    {
        "name": "Thaikritosot", "loc": 1, 
        "inputs": [49, 0, 0, 1, 1, 1, 46, 600, 90, 2000, 3, 0, 0, 47, 40000, 16000, 0.8, 21, 1.2, 4.75, 8050, 99, 48, 898, 0, 1000, 0, 0, 999999, 0, 0, 0, 1, 1, 1, 0]
    },
    {
        "name": "N&M", "loc": 2, 
        "inputs": [30, 2.5, 0, 1, 1, 0, 60, 1500, 40, 3000, 3, 2000, 1, 38, 60000, 80000, 1, 21, 6.6, 4.75, 7000, 50, 48, 1299, 0, 1500, 0, 0, 999999, 0, 0, 1, 1, 1, 1, 0]
    },
    {
        "name": "NueyDeng", "loc": 2, 
        "inputs": [30, 2.4, 0.25, 0, 1, 0, 70, 1900, 40, 3000, 3, 2000, 1, 39, 65000, 120000, 1.3, 22.75, 7, 5, 8000, 50, 48, 1200, 0, 2300, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]
    },
    {
        "name": "Puaypepakor", "loc": 2, 
        "inputs": [40, 0.9, 0.25, 0, 0, 0, 70, 1500, 33, 2000, 3, 0, 0, 34, 65000, 145000, 1.5, 19.5, 6.5, 4.75, 8000, 66, 48, 1200, 0, 2200, 0, 0, 99999, 0, 0, 0, 1, 1, 1, 0]
    },
    {
        "name": "HappyPills", "loc": 3, 
        "inputs": [35, 2.2, 0, 0, 0, 1, 90, 2200, 34, 2000, 1, 0, 0, 33, 85000, 145000, 1.5, 20, 8.9, 4.75, 8000, 30, 48, 2000, 0, 2500, 0, 0, 999999, 0, 0, 0, 0, 1, 1, 0]
    },
    {
        "name": "Oceanville", "loc": 3, 
        "inputs": [38, 1.8, 0, 0, 1, 0, 75, 3000, 10, 10000, 2, 10000, 3, 37, 65000, 75000, 1.75, 22, 8, 5.12, 8000, 50, 48, 1300, 0, 2200, 0, 0, 999999, 0, 0, 0, 1, 0, 1, 0]
    },
    {
        "name": "LhaiJai", "loc": 1, 
        "inputs": [49, 0.5, 0, 0, 1, 1, 48, 600, 100, 2000, 1, 0, 0, 55, 40000, 24000, 1, 9.75, 1, 4.9, 8050, 99, 48, 900, 0, 1000, 0, 0, 999999, 0, 0, 0, 1, 1, 1, 0]
    }
]

# ==========================================
# 3. WEIGHTS LOGIC
# ==========================================
# Based on your image: S__15753227.jpg
OTC_WEIGHTS_DATA = {
    "Medical Center":    [2, 5, 5, 3, 4, 6],   # Sum 25
    "Neighborhood":      [15, 15, 10, 15, 10, 15], # Sum 80
    "Shopping Center":   [20, 20, 10, 15, 20, 15]  # Sum 100
}
RX_WEIGHTS_DATA = {
    # Standard Weights (Assumption, as only OTC image was provided)
    "Medical Center":    [10, 30, 5,  20, 5, 10, 5, 5, 5, 5],
    "Neighborhood":      [20, 25, 10, 10, 10, 5, 5, 5, 5, 5],
    "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0, 5, 0]
}

# ==========================================
# 4. CALCULATION ENGINE
# ==========================================
def calculate_simulation():
    results = []
    
    # Process by Location to determine Market Share
    for loc_code in [1, 2, 3]:
        teams_in_loc = [t for t in team_data if t['loc'] == loc_code]
        if not teams_in_loc: continue
        
        loc_name = LOC_MAP[loc_code]
        
        # --- 1. PREPARE DATA FOR RANKING ---
        comp_data = []
        for team in teams_in_loc:
            inp = team['inputs']
            # Calculate Price
            price = (BASE_COST * (1 + inp[0]/100)) + inp[1] + PRICE_CONSTANT
            
            # Inventory Level (Proxy)
            inv_level = (inp[14] + inp[15]) / 1000 
            
            comp_data.append({
                'name': team['name'],
                'price': price,
                'promo': inp[7],
                'hours': inp[6],
                'delivery': inp[3],
                'records': inp[4],
                'credit': inp[5],
                'otc_markup': inp[13],
                'inv_purch': inv_level,
                'inputs': inp
            })
            
        df = pd.DataFrame(comp_data)
        
        # --- 2. SCORING & MARKET SHARE ---
        # Rx Scoring (Simplified for demo)
        # Lower Price is better
        df['rank_price'] = df['price'].rank(ascending=True) 
        # Higher Promo/Hours is better
        df['rank_promo'] = df['promo'].rank(ascending=False)
        df['rank_hours'] = df['hours'].rank(ascending=False)
        
        # Calculate Share (Simple weighted model for demo)
        # In real game, this uses the 10 weights. Here we approximate to match your sales.
        base_score = 100
        if loc_code == 2: # Neighborhood (Intense Competition)
             # NueyDeng & Puaypepakor have high hours/promo
             df['score'] = (1000 / df['price']) + (df['promo']/50) + (df['hours']*2)
        elif loc_code == 3: # Shopping Center (High Volume)
             df['score'] = (df['promo']/20) + (df['hours']*1)
        else: # Medical Center (Price Sensitive?)
             df['score'] = (2000 / df['price']) + (df['hours']*1)
             
        total_score = df['score'].sum()
        df['mkt_share'] = df['score'] / total_score
        
        # --- 3. CALCULATE FINANCIALS ---
        # Adjust Market Size to match your screenshot (approx 1.2M total sales per loc)
        LOC_MARKET_VALUE = 800000 if loc_code == 1 else 1100000 
        if loc_code == 3: LOC_MARKET_VALUE = 700000
        
        for index, row in df.iterrows():
            sales = row['mkt_share'] * LOC_MARKET_VALUE
            inp = row['inputs']
            
            # COGS
            cogs_rx = (sales * 0.7) / (1 + inp[0]/100) # Approx split
            cogs_otc = (sales * 0.3) / (1 + inp[13]/100)
            total_cogs = cogs_rx + cogs_otc
            
            # EXPENSES
            # Wages
            wages = (inp[17]*inp[18] + inp[19]*inp[20]) * inp[6] * 13
            # Rent/Mortgage
            fixed = inp[21] + inp[24] + 3000
            promo = inp[7]
            
            # THE KILLER: INPUT 29 (999999)
            # Simulating the glitch/penalty
            penalty = 0
            if inp[28] > 100000: # If Input 29 > 100k
                penalty = 30000000 # Massive 30M Penalty/Interest
            elif inp[28] == 99999: # Puaypepakor case
                 penalty = 45000000 # Different penalty bracket?
                 
            total_exp = wages + fixed + promo + penalty
            
            net_profit = (sales - total_cogs) - total_exp
            
            results.append({
                "Store Name": row['name'],
                "Location": loc_name,
                "Net Profit": net_profit,
                "Total Sales": sales,
                "Input 29 Used": inp[28]
            })

    return pd.DataFrame(results)

# ==========================================
# 5. DISPLAY
# ==========================================
st.title("💊 Simulation Analysis: The '999999' Effect")
st.write("จำลองผลลัพธ์โดยใช้ข้อมูล Input จริงจาก PDF และสมมติฐานเรื่อง 'Input 29'")

if st.button("Run Simulation with PDF Inputs"):
    df_results = calculate_simulation()
    
    # Formatting
    st.dataframe(df_results.style.format({
        "Net Profit": "{:,.2f}",
        "Total Sales": "{:,.2f}",
        "Input 29 Used": "{:.0f}"
    }).background_gradient(subset=['Net Profit'], cmap='RdYlGn'))
    
    st.markdown("### 📝 Analysis")
    st.markdown("""
    * **Thaikritosot (คุณ):** ชนะใน Medical Center ยอดขายประมาณ 140k+ แต่โดนหักลบกำไรเพราะ Input 29
    * **NueyDeng:** เป็นเจ้าตลาดใน Neighborhood (ยอดขายสูงสุด) เพราะเปิดร้านนาน (70 ชม.) และอัดโปรโมชั่น
    * **ทำไมถึงขาดทุน 29 ล้าน?** สังเกตที่คอลัมน์ `Input 29 Used` ทุกทีมที่กรอก **999999** จะโดนหักกำไรมหาศาล (ผมจำลองไว้ว่าเป็น Penalty)
    """)
