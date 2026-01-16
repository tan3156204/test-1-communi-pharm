import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config & Full Screen Setup
# ==========================================
st.set_page_config(
    page_title="Communi-Pharm V10.5 (Full Screen)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS Hack to Force Full Screen & Remove Margins ---
st.markdown("""
<style>
    /* ขยายพื้นที่แสดงผลให้เต็มจอจริงๆ */
    .reportview-container .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    /* ลด Padding ด้านบนเพื่อไม่ให้เสียพื้นที่ */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 95% !important; /* ปรับให้กว้างเกือบสุดขอบ */
    }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"

# List of all 36 Inputs
INPUT_LABELS = [
    "1. Prescription Markup (%)", "2. Prescription Professional Fee ($)", "3. Copayment Discount ($)",
    "4. Delivery Service (0=No, 1=Yes)", "5. Patient Records (0=No, 1=Yes)", "6. Store Offers Credit (0=No, 1=Yes)",
    "7. Hours Pharmacy Open Per Week", "8. Promotional Expenditures ($)", "9. % Promotion on Rx Dept (%)",
    "10. Current Period’s Investment ($)", "11. Investment Project Number", "12. Investment Withdrawal ($)",
    "13. Investment Withdrawal Project Number", "14. Markup on Other Items (%)", "15. Prescription Inv Purchases ($)",
    "16. Other Inv Purchases ($)", "17. Number Pharmacists", "18. Pharmacist’s Hourly Pay ($)",
    "19. Number Sales Clerks", "20. Sales Clerk’s Hourly Pay ($)", "21. Manager’s Salary ($)",
    "22. Manager’s % Time Rx", "23. Manager Hours/Week", "24. Mortgage Payment ($)",
    "25. Collection Agency ($)", "26. Minimum Cash Balance ($)", "27. Rx Inv Returned ($)",
    "28. Other Inv Returned ($)", "29. Payment on A/P ($)", "30. Long Term Debt Written ($)",
    "31. Long Term Debt Payment ($)", "32. Interest Rate A/R (%)", "33. Benefits: Life Ins (0/1)",
    "34. Benefits: Health Ins (0/1)", "35. Third-Party Rx (0/1)", "36. Bid for HMO Contract ($)"
]

REPORT_COLUMNS = [
    "Rank", "Store Name", "LOCATION", "Net Profit", "ROI", 
    "TOT SALES", "Rx SALES", "OTH SALES", "Rx Mkt Sh",
    "Avg Rx Pr", "Rx Ing $", "Rx GM%", 
    "Store Hrs", "A/P Paid", "M’age Pay", "E. Loan",
    "Net Worth", "Cash Flow", "Cash", "Investments",
    "Current", "Acid Test", "Turnover", "ROA", "G Margin", "Debt/NW"
]

LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

DEFAULT_WEIGHTS = {
    "Factor": [
        "Store's Past Rx Price", "Store's Present Rx Price", "Store's Promotion Index",
        "Store's Hours", "Offers Delivery Service", "Offers Patient Records",
        "Offers Credit", "Store's Inventory Level", "Store's Previous Market Share",
        "Store's RX Per Hour"
    ],
    "Medical Center":    [10, 30, 5,  20, 5, 10, 5, 5, 5, 5],
    "Neighborhood":      [20, 25, 10, 10, 10, 5, 5, 5, 5, 5],
    "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0, 5, 0]
}

# ==========================================
# 2. Initialization & Pre-loading Inputs
# ==========================================
def initialize_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 2 
    st.session_state.weights_df = pd.DataFrame(DEFAULT_WEIGHTS).set_index("Factor")
    
    for i in range(1, num_teams + 1):
        team_id = f"team_{i}"
        
        inputs = [0.0] * 36
        # Defaults for other teams
        inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
        inputs[17]=1; inputs[18]=25.0; inputs[19]=1; inputs[20]=10.0; 
        inputs[21]=1500.0; inputs[23]=40.0
        
        store_name = f"Store {i}"
        history = []
        
        # --- Store 1: ThaikritOsot Configuration ---
        if i == 1:
            store_name = "ThaikritOsot"
            
            # === CORRECTED INPUTS FOR PERIOD 2 ===
            inputs[0] = 49.0; inputs[1] = 1.0; inputs[2] = 0.0
            inputs[3] = 1.0; inputs[4] = 1.0; inputs[5] = 1.0
            inputs[6] = 60.0; inputs[7] = 1000.0; inputs[8] = 60.0
            inputs[9] = 0.0; inputs[10] = 0.0
            inputs[13] = 47.0; inputs[14] = 40000.0; inputs[15] = 25000.0
            inputs[17] = 1.0; inputs[18] = 21.0
            inputs[19] = 1.5; inputs[20] = 4.75
            inputs[21] = 8100.0; inputs[22] = 33.33; inputs[23] = 60.0
            inputs[24] = 8200.0; inputs[26] = 1000.0
            inputs[28] = 999999.0; inputs[29] = 10000.0 # Debt Written
            inputs[31] = 2.0 # Interest Rate
            inputs[32] = 1.0; inputs[33] = 1.0; inputs[34] = 1.0

            # --- Period 1 History ---
            p1_stats = {
                "Store Name": "ThaikritOsot", "LOCATION": "Medical Center",
                "Net Profit": 9848.0, "ROI": 7.0, 
                "TOT SALES": 142312.0, "Rx SALES": 115752.0, "OTH SALES": 26560.0,
                "Rx Mkt Sh": 12.5, "Avg Rx Pr": 19.61, "Rx Ing $": 11.23, "Rx GM%": 42.7,
                "Store Hrs": 46.0, "A/P Paid": 20000.0, "E. Loan": 0.0,
                "Net Worth": 138000.0, "Cash Flow": 5000.0, "Cash": 15000.0,
                "Investments": 2000.0,
                "Current": 2.40, "Acid Test": 1.16, "Turnover": 0.67,
                "ROA": 3.0, "G Margin": 45.0, "Debt/NW": 1.17
            }
            history.append(p1_stats)

        st.session_state.players[team_id] = {
            'shop_name': store_name,
            'location_code': 1 if i == 1 else (i % 3) + 1,
            'status': 'Thinking',
            'period': 2,
            'inputs': inputs,
            'financials': {
                'cash': 15000.0 if i==1 else 10000.0,
                'investments': 2000.0 if i==1 else 0.0,
                'acct_receivable': 45000.0,
                'inventory_rx': 55000.0, 
                'inventory_otc': 25000.0,
                'fixed_assets': 50000.0,
                'acct_payable': 30000.0,
                'notes_payable': 0.0,
                'long_term_debt': 100000.0,
                'retained_earnings': 138000.0 if i==1 else 100000.0
            },
            'prev_stats': { 
                'avg_price': 19.61 if i==1 else 20.0, 
                'mkt_share': 12.5 if i==1 else 20.0, 
                'rx_per_hr': 5.0
            },
            'history': history
        }

if 'players' not in st.session_state:
    initialize_game(5)

# ==========================================
# 3. Logic Engine
# ==========================================
def calculate_rank_scores(store_list, w_df):
    data = []
    base_cost = 11.23 
    price_constant = 2.90 

    for p in store_list:
        tid = p['id']
        inp = p['p']['inputs']
        prev = p['p']['prev_stats']
        fin = p['p']['financials']
        
        curr_price = (base_cost * (1 + inp[0]/100)) + inp[1] + price_constant
        inv_level = (fin['inventory_rx'] + fin['inventory_otc']) / 1000
        
        data.append({
            'id': tid,
            'price_past': prev['avg_price'],
            'price_pres': curr_price,
            'promo': inp[7], 'hours': inp[6], 'delivery': inp[3],
            'records': inp[4], 'credit': inp[5], 'inventory': inv_level,
            'mkt_share': prev['mkt_share'], 'efficiency': prev['rx_per_hr']
        })
    
    df_comp = pd.DataFrame(data)
    loc_code = store_list[0]['p']['location_code']
    weights = w_df[LOC_MAP[loc_code]].values
    
    df_ranks = pd.DataFrame({'id': df_comp['id']})
    def get_rank(series, ascending): return series.rank(method='min', ascending=ascending)

    df_ranks['r1'] = get_rank(df_comp['price_past'], False)
    df_ranks['r2'] = get_rank(df_comp['price_pres'], False)
    for i, col in enumerate(['promo','hours','delivery','records','credit','inventory','mkt_share','efficiency']):
        df_ranks[f'r{i+3}'] = get_rank(df_comp[col], True)
    
    final_scores = {}
    for index, row in df_ranks.iterrows():
        total_score = sum(row[f'r{i+1}'] * weights[i] for i in range(10))
        final_scores[row['id']] = total_score
        
    return final_scores, base_cost, price_constant

def process_period():
    w_df = st.session_state.weights_df
    
    stores_by_loc = {1: [], 2: [], 3: []}
    for tid, p in st.session_state.players.items():
        if p['status'] == 'Submitted' and p['location_code'] != 0:
            stores_by_loc[p['location_code']].append({'id': tid, 'p': p})
            
    for loc_code, stores in stores_by_loc.items():
        if not stores: continue
        
        rank_scores, base_cost, pr_const = calculate_rank_scores(stores, w_df)
        total_loc_score = sum(rank_scores.values())
        base_market_size = len(stores) * 6000 
        
        for s_data in stores:
            tid = s_data['id']
            p = s_data['p']
            inp = p['inputs']
            fin = p['financials']
            
            # --- Sales ---
            my_score = rank_scores[tid]
            mkt_share = (my_score / total_loc_score) if total_loc_score else 0
            rx_count = base_market_size * mkt_share
            avg_rx_price = (base_cost * (1 + inp[0]/100)) + inp[1] + pr_const
            rx_sales = rx_count * avg_rx_price
            
            otc_ratio = 0.25 if loc_code == 1 else 0.45
            otc_sales = rx_sales * otc_ratio * (1 + (inp[7]/5000)) * (1 + inp[13]/100)
            tot_sales = rx_sales + otc_sales
            
            # --- COGS ---
            cost_rx = rx_sales / (1 + (inp[0]/100))
            cost_otc = otc_sales / (1 + (inp[13]/100))
            
            req_ret_rx = min(inp[26], fin['inventory_rx'] * 0.25)
            req_ret_otc = min(inp[27], fin['inventory_otc'] * 0.25)
            
            fin['inventory_rx'] = max(0, (fin['inventory_rx'] + inp[14] - req_ret_rx) - cost_rx)
            fin['inventory_otc'] = max(0, (fin['inventory_otc'] + inp[15] - req_ret_otc) - cost_otc)
            tot_cogs = cost_rx + cost_otc
            gross_margin = tot_sales - tot_cogs
            
            # --- Expenses ---
            hrs_open = inp[6]
            wages = (inp[17]*inp[18] + inp[19]*inp[20]) * hrs_open * 13
            if hrs_open > 40: wages *= 1.1
            
            ben_rate = 0
            if inp[32]==1: ben_rate += 0.05
            if inp[33]==1: ben_rate += 0.15
            ben_cost = wages * ben_rate
            
            fixed_ops = inp[21] + inp[24] + 3000
            depr = fin['fixed_assets']*0.02
            interest_exp = (fin['long_term_debt'] + fin['notes_payable']) * 0.025
            ar_interest_income = (fin['acct_receivable'] * 0.5) * (inp[31] / 100)
            
            tot_exp = wages + ben_cost + fixed_ops + inp[7] + depr + interest_exp
            net_profit = gross_margin - tot_exp + ar_interest_income
            
            # --- Cash Flow ---
            pay_ap = min(inp[28], fin['acct_payable'])
            debt_written = inp[29]
            
            cash_in = (tot_sales * 0.9) + debt_written
            cash_out = (tot_exp - depr) + inp[14] + inp[15] + inp[30] + pay_ap
            
            fin['cash'] += (cash_in - cash_out)
            fin['retained_earnings'] += net_profit
            fin['long_term_debt'] += (debt_written - inp[30]) 
            fin['acct_payable'] = max(0, fin['acct_payable'] - pay_ap + (inp[14]+inp[15])*0.5)
            
            e_loan = 0
            if fin['cash'] < 0:
                e_loan = abs(fin['cash']) + 2000
                fin['notes_payable'] += e_loan
                fin['cash'] += e_loan

            # --- History ---
            nw = fin['retained_earnings']
            curr_assets = fin['cash'] + fin['investments'] + fin['inventory_rx'] + fin['inventory_otc'] + fin['acct_receivable']
            curr_liab = fin['acct_payable'] + fin['notes_payable']

            p['history'].append({
                "Store Name": p['shop_name'], "LOCATION": LOC_MAP[p['location_code']],
                "Net Profit": net_profit, "ROI": (net_profit/nw*100) if nw else 0,
                "TOT SALES": tot_sales, "Rx SALES": rx_sales, "OTH SALES": otc_sales,
                "Rx Mkt Sh": mkt_share * 100, "Avg Rx Pr": avg_rx_price,
                "Rx Ing $": base_cost, "Rx GM%": (rx_sales - cost_rx)/rx_sales*100 if rx_sales else 0,
                "Store Hrs": hrs_open, "E. Loan": e_loan, "Investments": fin['investments'],
                "Net Worth": nw, "Cash Flow": cash_in - cash_out, "Cash": fin['cash'],
                "Current": curr_assets/curr_liab if curr_liab else 0,
                "Acid Test": (fin['cash'] + fin['acct_receivable']) / (curr_liab + 1),
                "Turnover": tot_cogs / ((fin['inventory_rx']+fin['inventory_otc'])/2 + 1),
                "ROA": (net_profit / (fin['fixed_assets'] + curr_assets)*100),
                "G Margin": (gross_margin / tot_sales*100) if tot_sales else 0,
                "Debt/NW": ((fin['long_term_debt'] + curr_liab) / nw) if nw else 0
            })
            
            p['prev_stats'] = {'avg_price': avg_rx_price, 'mkt_share': mkt_share*100, 'rx_per_hr': rx_count/(hrs_open*13)}
            p['status'] = 'Thinking'
            p['period'] = p.get('period', 1) + 1

    st.session_state.global_period += 1

# ==========================================
# 4. UI Display
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Instructor":
        pwd = st.text_input("Admin Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.markdown("---")
            if st.button("⚠️ Reset Game", type="primary"):
                initialize_game(5); st.rerun()
    
    elif role == "Student":
        if st.session_state.players:
            t_ids = list(st.session_state.players.keys())
            sel_id = st.selectbox("Your Store", t_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
            p = st.session_state.players[sel_id]
            st.info(f"Store: {p['shop_name']} | Location: {LOC_MAP[p['location_code']]}")
            
            if p['status'] == 'Thinking':
                st.write(f"### 📝 Decisions for Period {st.session_state.global_period}")
                st.caption("Inputs pre-loaded.")
                with st.form("inputs"):
                    cols = st.columns(3) # Grid Layout for Inputs
                    for i in range(36):
                        with cols[i%3]:
                            if i in [3,4,5,32,33,34]: p['inputs'][i] = st.selectbox(INPUT_LABELS[i], [0,1], index=int(p['inputs'][i]))
                            else: p['inputs'][i] = st.number_input(INPUT_LABELS[i], value=float(p['inputs'][i]))
                    if st.form_submit_button("✅ Submit"): p['status']='Submitted'; st.rerun()
            else:
                st.success("Submitted. Waiting for Instructor.")
                if st.button("Edit"): p['status']='Thinking'; st.rerun()

            if p['history']:
                st.markdown("---")
                st.write(f"### 📊 History (Last: Period {p['period']-1})")
                last = p['history'][-1]
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Total Sales", f"${last['TOT SALES']:,.0f}")
                m2.metric("Net Profit", f"${last['Net Profit']:,.0f}")
                m3.metric("Cash", f"${last['Cash']:,.0f}")
                m4.metric("Debt/NW", f"{last['Debt/NW']:.2f}")
                
                df_res = pd.DataFrame(list(last.items()), columns=["Metric", "Value"])
                df_res = df_res[df_res['Metric'].isin(REPORT_COLUMNS)]
                # Use container width to fill the screen
                st.dataframe(df_res, use_container_width=True, height=600)

if role == "Instructor" and pwd == ADMIN_PASSWORD:
    st.title(f"👨‍🏫 Instructor Control (Period {st.session_state.global_period})")
    if st.button("🚀 Run Simulation"):
        process_period(); st.rerun()
    
    rows = [p['history'][-1] for p in st.session_state.players.values() if p['history']]
    if rows:
        st.write("### 🏆 Leaderboard")
        df = pd.DataFrame(rows).sort_values("Net Profit", ascending=False)
        st.dataframe(df[REPORT_COLUMNS].style.format(precision=2), use_container_width=True)
