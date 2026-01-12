import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Configuration & Constants
# ==========================================
def main():
    st.set_page_config(page_title="Communi-Pharm V10.0", layout="wide")
    
    # --- Helper Function for Rerun ---
    def safe_rerun():
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()

    ADMIN_PASSWORD = "admin"

    # 36 Inputs Labels
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

    LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

    DEFAULT_WEIGHTS = {
        "Factor": [
            "Store's Past Rx Price", "Store's Present Rx Price", "Store's Promotion Index",
            "Store's Hours", "Offers Delivery Service", "Offers Patient Records",
            "Offers Credit", "Store's Inventory Level", "Store's Previous Market Share",
            "Store's RX Per Hour"
        ],
        "Medical Center":    [10, 30, 5,  10, 5, 10, 5, 10, 10, 5],
        "Neighborhood":      [20, 25, 10, 5,  10, 5, 5, 5,  10, 5],
        "Shopping Center":   [40, 30, 15, 5,  0,  0, 5, 0,  5,  0]
    }

    # ==========================================
    # 2. Initialization
    # ==========================================
    if 'players' not in st.session_state:
        st.session_state.players = {}
        st.session_state.global_period = 1
        st.session_state.weights_df = pd.DataFrame(DEFAULT_WEIGHTS).set_index("Factor")
        
        # Init 5 Teams
        for i in range(1, 6):
            team_id = f"team_{i}"
            inputs = [0.0] * 36
            # Set Default Inputs
            inputs[0]=50.0; inputs[1]=3.0; inputs[6]=50.0; inputs[13]=45.0
            inputs[17]=1; inputs[18]=25.0; inputs[19]=1; inputs[20]=10.0; 
            inputs[21]=1500.0; inputs[23]=40.0
            
            st.session_state.players[team_id] = {
                'shop_name': f"Store {i}", 
                'location_code': 0,
                'status': 'Thinking',
                'inputs': inputs,
                'financials': {
                    'cash': 50000.0, 'acct_receivable': 2000.0,
                    'inventory_rx': 30000.0, 'inventory_otc': 15000.0,
                    'fixed_assets': 60000.0, 'acct_payable': 5000.0,
                    'notes_payable': 0.0, 'long_term_debt': 40000.0,
                    'retained_earnings': 112000.0 
                },
                'prev_stats': { 'avg_price': 20.0, 'mkt_share': 20.0, 'rx_per_hr': 5.0 },
                'history': []
            }

    # ==========================================
    # 3. Calculation Logic
    # ==========================================
    def calculate_score(p, w_df):
        if p['location_code'] == 0: return 0, 0
        w = w_df[LOC_MAP[p['location_code']]]
        inp = p['inputs']
        prev = p['prev_stats']
        
        curr_price = 10.0 * (1 + inp[0]/100) + inp[1]
        
        # Score Components
        s_parts = [
            w[0] * (20/prev['avg_price']),      # Past Price
            w[1] * (20/curr_price),             # Present Price
            w[2] * (inp[7]/1000),               # Promo
            w[3] * (inp[6]/40),                 # Hours
            w[4] * inp[3],                      # Delivery
            w[5] * inp[4],                      # Records
            w[6] * inp[5],                      # Credit
            w[7] * ((p['financials']['inventory_rx']+p['financials']['inventory_otc'])/10000), # Inv
            w[8] * prev['mkt_share'],           # Market Share
            w[9] * prev['rx_per_hr']            # Efficiency
        ]
        return max(sum(s_parts), 1), curr_price

    def run_period():
        w_df = st.session_state.weights_df
        loc_data = {1: [], 2: [], 3: []}
        
        # 1. Gather Scores
        for tid, p in st.session_state.players.items():
            if p['status'] == 'Submitted' and p['location_code'] != 0:
                sc, pr = calculate_score(p, w_df)
                loc_data[p['location_code']].append({'id': tid, 'score': sc, 'price': pr})
        
        # 2. Process Sales
        for loc, stores in loc_data.items():
            if not stores: continue
            tot_sc = sum(s['score'] for s in stores)
            base_demand = 6000
            
            for s in stores:
                p = st.session_state.players[s['id']]
                inp = p['inputs']; fin = p['financials']
                
                # Sales
                mkt_share = s['score'] / tot_sc if tot_sc else 0
                rx_count = base_demand * mkt_share
                rx_sales = rx_count * s['price']
                otc_sales = rx_sales * 0.45 * (1 + inp[13]/100)
                tot_sales = rx_sales + otc_sales
                
                # COGS
                c_rx = rx_sales / (1 + inp[0]/100)
                c_otc = otc_sales / (1 + inp[13]/100)
                
                # Stock Check & Emergency
                e_rx = max(0, (c_rx - fin['inventory_rx']) * 1.15)
                if e_rx > 0: fin['inventory_rx'] = c_rx
                
                e_otc = max(0, (c_otc - fin['inventory_otc']) * 1.15)
                if e_otc > 0: fin['inventory_otc'] = c_otc
                
                fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - c_rx
                fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - c_otc
                
                # Expenses
                open_hrs = inp[6]
                wages = (inp[18]*inp[17] + inp[20]*inp[19]) * open_hrs * 13
                # (Simplified Overtime logic for brevity)
                if open_hrs > 40: wages *= 1.1 
                
                exp = wages + inp[21] + (inp[23] or 2500) + inp[7] + (fin['fixed_assets']*0.02) + (fin['long_term_debt']*0.025) + 2000
                
                # Profit & Cash
                gross = tot_sales - (c_rx + c_otc + e_rx + e_otc)
                net = gross - exp
                
                cash_flow = (tot_sales*0.9 + inp[29]) - (exp - (fin['fixed_assets']*0.02) + inp[14] + inp[15] + inp[31] + e_rx + e_otc)
                fin['cash'] += cash_flow
                fin['retained_earnings'] += net
                fin['long_term_debt'] -= inp[31]
                
                # Emergency Loan
                if fin['cash'] < 0:
                    loan = abs(fin['cash']) + 2000
                    fin['notes_payable'] += loan
                    fin['cash'] += loan
                
                # Update State
                p['prev_stats'] = {'avg_price': s['price'], 'mkt_share': mkt_share*100, 'rx_per_hr': rx_count/(open_hrs*13) if open_hrs else 0}
                p['history'].append({
                    "Store Name": p['shop_name'], "LOCATION": LOC_MAP[p['location_code']],
                    "Net Profit": net, "TOT SALES": tot_sales, "Rx Mkt Sh": mkt_share*100,
                    "Cash": fin['cash'], "Loan": fin['notes_payable']
                })
                p['status'] = 'Thinking'
                p['period'] = st.session_state.global_period + 1

        st.session_state.global_period += 1

    # ==========================================
    # 4. UI Layout
    # ==========================================
    with st.sidebar:
        st.title("💊 Communi-Pharm V10")
        role = st.selectbox("Role", ["Student", "Instructor"])
        
        if role == "Instructor":
            if st.text_input("Password", type="password") == ADMIN_PASSWORD:
                st.markdown("---")
                if st.button("⚠️ Reset Game", type="primary"):
                    st.session_state.clear()
                    safe_rerun()
        
        elif role == "Student":
            if 'players' in st.session_state and st.session_state.players:
                me = st.selectbox("Select Store", list(st.session_state.players.keys()), 
                                 format_func=lambda x: st.session_state.players[x]['shop_name'])
                st.session_state['current_user'] = me

    # --- MAIN PAGE ---
    if role == "Instructor" and st.session_state.get('players'):
        st.header(f"Instructor Control (Period {st.session_state.global_period})")
        ready = sum(1 for p in st.session_state.players.values() if p['status']=='Submitted')
        st.info(f"Ready: {ready} / {len(st.session_state.players)} Teams")
        
        if st.button("🚀 Run Simulation"):
            run_period()
            st.success("Simulation Complete!")
            safe_rerun()
            
        # Report
        data = [p['history'][-1] for p in st.session_state.players.values() if p['history']]
        if data:
            st.dataframe(pd.DataFrame(data).style.format(precision=2))

    elif role == "Student" and st.session_state.get('current_user'):
        p = st.session_state.players[st.session_state['current_user']]
        st.title(f"🏥 {p['shop_name']}")
        
        # Location Selector
        if p['location_code'] == 0:
            st.warning("Please Select Location")
            c1,c2,c3 = st.columns(3)
            if c1.button("Medical Center"): p['location_code']=1; safe_rerun()
            if c2.button("Neighborhood"): p['location_code']=2; safe_rerun()
            if c3.button("Shopping Center"): p['location_code']=3; safe_rerun()
        else:
            st.caption(f"📍 Location: {LOC_MAP[p['location_code']]}")
            
            if p['status'] == 'Thinking':
                with st.form("decision_form"):
                    st.write("Input Decisions:")
                    cols = st.columns(3)
                    for i in range(36):
                        with cols[i%3]:
                            val = p['inputs'][i]
                            if i in [3,4,5,32,33,34]: # Boolean inputs
                                p['inputs'][i] = st.selectbox(INPUT_LABELS[i], [0,1], index=int(val))
                            else:
                                p['inputs'][i] = st.number_input(INPUT_LABELS[i], value=float(val))
                    
                    if st.form_submit_button("✅ Submit"):
                        p['status'] = 'Submitted'
                        safe_rerun()
            else:
                st.success("Decisions Submitted. Waiting for Instructor.")
                if st.button("Edit"):
                    p['status'] = 'Thinking'
                    safe_rerun()
                
                if p['history']:
                    st.write("### Latest Results")
                    last = p['history'][-1]
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Profit", f"${last['Net Profit']:,.2f}")
                    c2.metric("Sales", f"${last['TOT SALES']:,.2f}")
                    c3.metric("Mkt Share", f"{last['Rx Mkt Sh']:.2f}%")

if __name__ == "__main__":
    main()
