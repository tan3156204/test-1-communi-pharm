import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config (Matching Manual Weights)
# ==========================================
st.set_page_config(page_title="Communi-Pharm V3.4 (Legacy Comparison)", layout="wide")
ADMIN_PASSWORD = "admin1234"

# Configuration for Ranking Weights (Source: Instructor's Guide)
LOCATION_CONFIG = {
    3: { # Location 3: Medical Center
        "name": "Medical Center",
        "rent_rate": 0.045,
        "base_traffic": 5000, 
        "weights": {"price": 2, "promo": 2, "hours": 6, "service": 10, "inventory": 8, "staff": 8}
    },
    2: { # Location 2: Neighborhood
        "name": "Neighborhood",
        "rent_rate": 0.025,
        "base_traffic": 3500,
        "weights": {"price": 10, "promo": 7, "hours": 5, "service": 5, "inventory": 6, "staff": 5}
    },
    1: { # Location 1: Shopping Center
        "name": "Shopping Center",
        "rent_rate": 0.030,
        "base_traffic": 6000,
        "weights": {"price": 7, "promo": 10, "hours": 4, "service": 3, "inventory": 5, "staff": 7}
    }
}

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_id = f"Team {i}"
        
        # Array 37 slots (Index 1-36 matches the Form)
        inputs = [0.0] * 37 
        
        # Default Values to prevent ZeroDivisionError
        inputs[1] = float(i)    # Store ID
        inputs[2] = 1.0         # Period
        inputs[3] = 2.0         # Location Code (Default = Neighborhood)
        inputs[4] = 3.0         # Prof Fee
        inputs[5] = 50.0        # Rx Markup
        inputs[6] = 45.0        # OTC Markup
        inputs[12] = 1.0        # Pharm
        inputs[13] = 20.0       # Wage
        inputs[14] = 1.0        # Clerk
        inputs[15] = 6.0        # Wage
        inputs[16] = 8000.0     # Mgr Salary
        inputs[17] = 50.0       # Hours
        inputs[23] = 20000.0    # Buy Rx
        inputs[24] = 10000.0    # Buy OTC
        
        # Fixed Costs Defaults
        inputs[29] = 2000.0     # Rent (Placeholder)
        inputs[30] = 1500.0     # Utilities
        inputs[31] = 400.0      # Insurance
        inputs[32] = 200.0      # Licenses

        st.session_state.players[team_id] = {
            'shop_name': team_id,
            'status': 'Thinking',
            'inputs': inputs,
            'financials': {
                'cash': 40000.0, 'inventory_rx': 20000.0, 'inventory_otc': 15000.0,
                'long_term_debt': 0.0, 'emergency_loan': 0.0, 'last_market_share': 14.28
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Engine (Weighted Ranking Logic)
# ==========================================
def get_rank_points(series, ascending=True):
    # Rank 1 gets N points, Rank N gets 1 point
    ranks = series.rank(ascending=ascending, method='min')
    return (len(series) + 1) - ranks

def process_period():
    # 1. Group players by Location
    loc_groups = {1: [], 2: [], 3: []}
    for t, p in st.session_state.players.items():
        if p['status'] == 'Submitted':
            loc_code = int(p['inputs'][3])
            if loc_code in loc_groups:
                loc_groups[loc_code].append(t)

    # 2. Process each location independently
    for loc_code, teams in loc_groups.items():
        if not teams: continue
        
        config = LOCATION_CONFIG[loc_code]
        w = config['weights']
        
        # Extract comparison data
        data = []
        for t in teams:
            inp = st.session_state.players[t]['inputs']
            
            # Derived Variables for Ranking
            price_est = 10 * (1 + inp[5]/100) + inp[4] # Rx Price
            promo_tot = inp[19] + inp[20] + inp[21] + inp[22]
            hours_tot = inp[17] + inp[18]
            service_tot = inp[8] + inp[9] + inp[10] + inp[11]
            inventory_tot = st.session_state.players[t]['financials']['inventory_rx'] # Opening Inv
            staff_tot = inp[12] + (inp[14] * 0.5) # Pharm + 0.5 Clerk
            wage_avg = (inp[13] + inp[15]) / 2
            
            data.append({
                'team': t, 'price': price_est, 'promo': promo_tot,
                'hours': hours_tot, 'service': service_tot,
                'inventory': inventory_tot, 'staff': staff_tot,
                'wage_avg': wage_avg
            })
            
        df = pd.DataFrame(data).set_index('team')
        
        # Wage Penalty Logic (Manual: < 90% of avg market wage => poor staff performance)
        market_wage = df['wage_avg'].mean()
        df['staff_effective'] = df.apply(lambda x: x['staff'] * 0.6 if x['wage_avg'] < (market_wage * 0.9) else x['staff'], axis=1)

        # 3. Calculate Weighted Scores (The "Black Box" of Original Game)
        scores = pd.Series(0.0, index=df.index)
        scores += get_rank_points(df['price'], ascending=True) * w['price']      # Lower price is better
        scores += get_rank_points(df['promo'], ascending=False) * w['promo']     # More promo is better
        scores += get_rank_points(df['hours'], ascending=False) * w['hours']
        scores += get_rank_points(df['service'], ascending=False) * w['service']
        scores += get_rank_points(df['inventory'], ascending=False) * w['inventory']
        scores += get_rank_points(df['staff_effective'], ascending=False) * w['staff']
        
        # Calculate Market Share
        total_points = scores.sum()
        market_shares = scores / total_points if total_points > 0 else 0
        
        # 4. Financial Calculations per Player
        for t in teams:
            p = st.session_state.players[t]
            inp = p['inputs']
            fin = p['financials']
            
            share = market_shares[t]
            
            # Demand Calculation
            # In original game, total market grows slightly with total promo
            market_size = config['base_traffic'] * len(teams) * (1 + (df['promo'].sum() / 100000))
            my_traffic = market_size * share
            
            rx_units = int(my_traffic * 0.35)
            otc_units = int(my_traffic * 0.65)
            
            # Revenue
            rx_cost = 10.0
            rx_price = rx_cost * (1 + inp[5]/100) + inp[4]
            rx_rev = rx_units * rx_price
            rx_cogs = rx_units * rx_cost
            
            otc_cost = 5.0
            otc_price = otc_cost * (1 + inp[6]/100)
            otc_rev = otc_units * otc_price
            otc_cogs = otc_units * otc_cost
            
            total_rev = rx_rev + otc_rev
            
            # Expenses
            # Wage (13 weeks)
            wages = ((inp[12]*inp[13]) + (inp[14]*inp[15])) * inp[17] * 13
            
            # Fixed Costs (User Inputs 29-36 are ESTIMATES, but actuals might differ in real game)
            # Here we use logic: Rent is % of sales, others are fixed
            rent_actual = total_rev * config['rent_rate'] # Overwrite user input for calculation
            
            promo_cost = inp[19] + inp[20] + inp[21] + inp[22]
            mgr_salary = inp[16]
            
            # Sum other operating expenses (30-36)
            other_ops = sum(inp[30:37])
            
            total_exp = wages + rent_actual + promo_cost + mgr_salary + other_ops
            
            # Net Profit
            gross_margin = total_rev - (rx_cogs + otc_cogs)
            net_profit = gross_margin - total_exp
            
            # Cash Flow
            cash_in = total_rev
            cash_out = total_exp + inp[23] + inp[24] + inp[25] + inp[26]
            
            fin['cash'] += (cash_in - cash_out)
            
            # Inventory Update
            fin['inventory_rx'] += (inp[23] - rx_cogs)
            fin['inventory_otc'] += (inp[24] - otc_cogs)
            fin['last_market_share'] = share * 100
            
            # Emergency Loan Trigger
            if fin['cash'] < 0:
                needed = abs(fin['cash']) + 1000
                fin['emergency_loan'] += needed
                fin['cash'] += needed

            # Record History
            p['history'].append({
                "Period": st.session_state.global_period,
                "Market Share": share * 100,
                "Total Sales": total_rev,
                "Net Profit": net_profit,
                "Cash": fin['cash'],
                "Location": config['name']
            })
            p['status'] = 'Thinking'
            p['period'] += 1

    st.session_state.global_period += 1

# ==========================================
# 4. User Interface
# ==========================================
def format_team_name(team_id):
    shop_name = st.session_state.players[team_id].get('shop_name', team_id)
    return f"{shop_name} ({team_id})"

with st.sidebar:
    st.title("Communi-Pharm V3.4")
    st.caption("Legacy Inputs (English) + Rank Logic")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Select Team", options=list(st.session_state.players.keys()), format_func=format_team_name)
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Student":
    p = st.session_state.players[team]
    
    # Shop Name
    with st.sidebar:
        st.markdown("---")
        new_name = st.text_input("Shop Name", value=p['shop_name'])
        if st.button("Save Name"):
            p['shop_name'] = new_name; st.rerun()

    st.title(f"🏥 {p['shop_name']}")
    st.caption(f"Team: {team} | Period: {st.session_state.global_period}")
    
    # Results Display
    if p['history']:
        last = p['history'][-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Market Share", f"{last['Market Share']:.2f}%")
        c2.metric("Total Sales", f"${last['Total Sales']:,.0f}")
        c3.metric("Net Profit", f"${last['Net Profit']:,.0f}")
        c4.metric("Cash", f"${last['Cash']:,.0f}")

    if p['status'] == 'Submitted':
        st.info("✅ Input Submitted.")
        if st.button("Edit Inputs"):
            p['status'] = 'Thinking'; st.rerun()
    else:
        # ==========================================
        # FORM 36 ITEMS (ENGLISH EXACT MATCH)
        # ==========================================
        with st.form("form_36"):
            st.subheader("Decision Input Form (Items 1-36)")
            inputs = p['inputs']
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("#### Section 1")
                i01 = st.number_input("Item 01: Store ID", value=int(inputs[1]), disabled=True)
                i02 = st.number_input("Item 02: Period", value=st.session_state.global_period, disabled=True)
                i03 = st.number_input("Item 03: Location Code (1-3)", min_value=1, max_value=3, value=int(inputs[3]))
                st.caption("1=Shopping, 2=Neighbor, 3=Medical")
                i04 = st.number_input("Item 04: Prof Fee ($)", value=inputs[4])
                i05 = st.number_input("Item 05: Rx Markup (%)", value=inputs[5])
                i06 = st.number_input("Item 06: OTC Markup (%)", value=inputs[6])
                i07 = st.number_input("Item 07: Special Disc (%)", value=inputs[7])
                st.markdown("---")
                st.caption("Service (0/1)")
                i08 = st.number_input("Item 08: Delivery", 0, 1, int(inputs[8]))
                i09 = st.number_input("Item 09: Patient Rec", 0, 1, int(inputs[9]))
                i10 = st.number_input("Item 10: Charge Acct", 0, 1, int(inputs[10]))
                i11 = st.number_input("Item 11: Consulting", 0, 1, int(inputs[11]))
                i12 = st.number_input("Item 12: Pharmacists", value=inputs[12])

            with c2:
                st.markdown("#### Section 2")
                i13 = st.number_input("Item 13: Pharm Wage", value=inputs[13])
                i14 = st.number_input("Item 14: Clerks", value=inputs[14])
                i15 = st.number_input("Item 15: Clerk Wage", value=inputs[15])
                i16 = st.number_input("Item 16: Mgr Salary", value=inputs[16])
                i17 = st.number_input("Item 17: Hours (Wk)", value=inputs[17])
                i18 = st.number_input("Item 18: Hours (Sun)", value=inputs[18])
                st.markdown("---")
                st.caption("Advertising")
                i19 = st.number_input("Item 19: Newspaper", value=inputs[19])
                i20 = st.number_input("Item 20: Radio", value=inputs[20])
                i21 = st.number_input("Item 21: TV", value=inputs[21])
                i22 = st.number_input("Item 22: Direct Mail", value=inputs[22])
                st.markdown("---")
                i23 = st.number_input("Item 23: Buy Rx ($)", value=inputs[23])
                i24 = st.number_input("Item 24: Buy OTC ($)", value=inputs[24])

            with c3:
                st.markdown("#### Section 3")
                i25 = st.number_input("Item 25: Pay A/P", value=inputs[25])
                i26 = st.number_input("Item 26: Pay Note", value=inputs[26])
                i27 = st.number_input("Item 27: New Note", value=inputs[27])
                i28 = st.number_input("Item 28: Dividend", value=inputs[28])
                st.markdown("---")
                st.caption("Operating Expenses")
                i29 = st.number_input("Item 29: Rent", value=inputs[29])
                i30 = st.number_input("Item 30: Utilities", value=inputs[30])
                i31 = st.number_input("Item 31: Insurance", value=inputs[31])
                i32 = st.number_input("Item 32: Taxes/Lic", value=inputs[32])
                i33 = st.number_input("Item 33: Repairs", value=inputs[33])
                i34 = st.number_input("Item 34: Supplies", value=inputs[34])
                i35 = st.number_input("Item 35: Acct/Legal", value=inputs[35])
                i36 = st.number_input("Item 36: Other", value=inputs[36])

            if st.form_submit_button("Submit Decisions"):
                ni = [0.0]*37
                ni[1]=i01; ni[2]=i02; ni[3]=i03; ni[4]=i04; ni[5]=i05; ni[6]=i06
                ni[7]=i07; ni[8]=i08; ni[9]=i09; ni[10]=i10; ni[11]=i11; ni[12]=i12
                ni[13]=i13; ni[14]=i14; ni[15]=i15; ni[16]=i16; ni[17]=i17; ni[18]=i18
                ni[19]=i19; ni[20]=i20; ni[21]=i21; ni[22]=i22; ni[23]=i23; ni[24]=i24
                ni[25]=i25; ni[26]=i26; ni[27]=i27; ni[28]=i28; ni[29]=i29; ni[30]=i30
                ni[31]=i31; ni[32]=i32; ni[33]=i33; ni[34]=i34; ni[35]=i35; ni[36]=i36
                
                p['inputs'] = ni
                p['status'] = 'Submitted'
                st.rerun()

elif role == "Instructor" and is_admin:
    st.title("Instructor Panel")
    if st.button("Run Simulation"):
        process_period()
        st.success("Processed!")
        st.rerun()
    
    st.dataframe(pd.DataFrame([
        {"Team": k, "Status": v['status'], "Cash": v['financials']['cash']} 
        for k,v in st.session_state.players.items()
    ]))
