import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config (ปรับตาม Manual)
# ==========================================
st.set_page_config(page_title="Communi-Pharm (V2.3 Dashboard)", layout="wide")
ADMIN_PASSWORD = "admin1234"
LOCATIONS = ["Med Center", "Neighborhood", "Shopping"]

# Configuration ของแต่ละทำเล (อ้างอิง Manual หน้า Store Specs)
# Rent Rate: Med=4.5%, Neighborhood=2.5%, Shopping=3.0%
LOCATION_CONFIG = {
    "Med Center": {
        "rent_rate": 0.045, 
        "weights": {"rx_price": 3, "promotion": 2, "hours": 6, "service": 10, "inventory": 8, "staffing": 8, "prev_share": 5},
        "base_traffic": 5000 
    },
    "Neighborhood": {
        "rent_rate": 0.025,
        "weights": {"rx_price": 9, "promotion": 7, "hours": 5, "service": 5, "inventory": 6, "staffing": 5, "prev_share": 6},
        "base_traffic": 3500
    },
    "Shopping": {
        "rent_rate": 0.030,
        "weights": {"rx_price": 7, "promotion": 9, "hours": 4, "service": 3, "inventory": 5, "staffing": 7, "prev_share": 4},
        "base_traffic": 6000
    }
}

# ==========================================
# 2. State & Data
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_name = f"Team {i}"
        st.session_state.players[team_name] = {
            'location': None,
            'period': 1,
            'status': 'Thinking',
            'last_decision': {},
            'financials': {
                'cash': 40000.0,
                'inventory_rx': 20000.0,
                'inventory_otc': 15000.0,
                'accounts_payable': 0.0,
                'long_term_debt': 0.0,
                'emergency_loan': 0.0,  # เพิ่มหนี้ฉุกเฉิน
                'last_market_share': 14.28
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Logic Engine (Weighted Rank + Manual Financials)
# ==========================================
def get_rank_score(series, ascending=True):
    ranks = series.rank(ascending=ascending, method='min') 
    n_teams = len(series)
    # คะแนนเต็มเท่ากับจำนวนทีมในทำเลนั้น
    points = (n_teams + 1) - ranks
    return points

def process_period():
    loc_pools = {loc: [] for loc in LOCATIONS}
    for t, data in st.session_state.players.items():
        if data['location'] and data['status'] == 'Submitted':
            loc_pools[data['location']].append(t)

    for loc, teams in loc_pools.items():
        if not teams: continue
        
        # ดึง Config ของทำเลนั้น
        config = LOCATION_CONFIG[loc]
        weights = config['weights']
        base_traffic = config['base_traffic']
        rent_rate = config['rent_rate']
        
        data_rows = []
        for t in teams:
            d = st.session_state.players[t]['last_decision']
            f = st.session_state.players[t]['financials']
            
            # Service Level Calculation
            service_lvl = (1 if d['delivery'] else 0) + (1 if d['records'] else 0) + (1 if d['credit'] else 0)
            
            # Price Estimation (Rx)
            estimated_price = 10 * (1 + d['rx_markup']/100) + d['rx_fee']
            
            row = {
                'team': t,
                'price': estimated_price,
                'promo': d['promo_exp'],
                'hours': d['hours_open'],
                'service': service_lvl,
                'inventory': f['inventory_rx'],
                'staff': d['n_pharm'],
                'prev_share': f['last_market_share'],
                'wage_rate': d['wage_pharm']
            }
            data_rows.append(row)
            
        df = pd.DataFrame(data_rows).set_index('team')
        
        # Logic: Wage Penalty (ถ้าจ่ายต่ำกว่าตลาด 10% ประสิทธิภาพพนักงานลดลง)
        avg_wage = df['wage_rate'].mean()
        df['staff_effective'] = df.apply(lambda x: x['staff'] * 0.6 if x['wage_rate'] < (avg_wage * 0.9) else x['staff'], axis=1)

        # Ranking Calculation (Comparative Logic)
        scores = pd.Series(0.0, index=df.index)
        scores += get_rank_score(df['price'], ascending=True) * weights['rx_price']
        scores += get_rank_score(df['promo'], ascending=False) * weights['promotion']
        scores += get_rank_score(df['hours'], ascending=False) * weights['hours']
        scores += get_rank_score(df['service'], ascending=False) * weights['service']
        scores += get_rank_score(df['inventory'], ascending=False) * weights['inventory']
        scores += get_rank_score(df['staff_effective'], ascending=False) * weights['staffing']
        scores += get_rank_score(df['prev_share'], ascending=False) * weights['prev_share']

        total_mkt_score = scores.sum()
        market_shares = scores / total_mkt_score if total_mkt_score > 0 else 0
        
        # Financial Calculation Loop
        for t in teams:
            player = st.session_state.players[t]
            d = player['last_decision']
            fin = player['financials']
            
            share = market_shares[t]
            # Traffic Adjustment based on total market performance could be added here
            my_traffic = base_traffic * share * len(teams) # Scale traffic to number of teams playing
            
            rx_units = int(my_traffic * 0.35)
            otc_units = int(my_traffic * 0.65)
            
            # --- Revenue ---
            rx_cost = 10.0
            rx_price = rx_cost * (1 + d['rx_markup']/100) + d['rx_fee']
            rx_rev = rx_units * rx_price
            rx_cogs = rx_units * rx_cost
            
            otc_cost = 5.0
            otc_price = otc_cost * (1 + d['otc_markup']/100)
            otc_rev = otc_units * otc_price
            otc_cogs = otc_units * otc_cost
            
            total_rev = rx_rev + otc_rev
            total_cogs = rx_cogs + otc_cogs
            gross_margin = total_rev - total_cogs
            
            # --- Expenses ---
            wages = (d['n_pharm'] * d['wage_pharm'] + d['n_clerk'] * d['wage_clerk']) * d['hours_open'] * 4 * 3 # 3 months/period approx? Manual says period = Quarter? Let's assume input is per month, so * 3. Or just keep logic simple per period.
            # *Assumption*: User inputs are "Per Period" values to keep it simple.
            
            wages = (d['n_pharm'] * d['wage_pharm'] + d['n_clerk'] * d['wage_clerk']) * d['hours_open'] * 13 # 13 weeks in a quarter
            mgr_salary = d['manager_salary'] # Fixed per period
            
            # [LOGIC FIX] Rent is % of Sales based on Location
            rent_exp = total_rev * rent_rate
            
            utilities = 1200 # Fixed estimate
            ads = d['promo_exp']
            depreciation = 500 # Fixed straight line estimate
            
            interest_exp = (fin['long_term_debt'] * 0.02) + (fin['emergency_loan'] * 0.05) # Higher rate for emergency
            
            # [LOGIC FIX] Other Taxes (Business Tax ~1.5%)
            other_taxes = total_rev * 0.015
            
            total_exp = wages + mgr_salary + rent_exp + utilities + ads + interest_exp + depreciation + other_taxes
            
            net_profit_before_tax = gross_margin - total_exp
            income_tax = net_profit_before_tax * 0.20 if net_profit_before_tax > 0 else 0
            net_profit = net_profit_before_tax - income_tax
            
            # --- Cash Flow & Balance Sheet Updates ---
            cash_in = total_rev 
            purchases = d['buy_rx'] + d['buy_otc']
            debt_pay = d['payment_ap'] + d['debt_payment_long']
            
            # Update Cash
            current_cash = fin['cash'] + (cash_in - (total_exp - depreciation) - purchases - debt_pay)
            
            # [LOGIC FIX] Emergency Loan Check
            if current_cash < 0:
                loan_needed = abs(current_cash) + 1000 # Borrow enough to be positive
                fin['emergency_loan'] += loan_needed
                current_cash += loan_needed
                player['alert'] = f"⚠️ Emergency Loan Triggered: ${loan_needed:,.0f}"
            else:
                player['alert'] = None

            fin['cash'] = current_cash
            fin['inventory_rx'] += (d['buy_rx'] - rx_cogs)
            fin['inventory_otc'] += (d['buy_otc'] - otc_cogs)
            fin['long_term_debt'] -= d['debt_payment_long']
            fin['last_market_share'] = share * 100
            
            # Record History
            player['history'].append({
                "Period": st.session_state.global_period,
                "Market Share": share * 100,
                "Total Sales": total_rev,
                "Net Profit": net_profit,
                "Cash": fin['cash'],
                "Rent": rent_exp,
                "Emergency Loan": fin['emergency_loan'],
                "Decision": d
            })
            
            player['status'] = 'Thinking'
            player['period'] += 1

    st.session_state.global_period += 1

def make_input(label, key, default):
    return st.number_input(label, value=float(default), step=1.0, key=key)

# ==========================================
# 4. User Interface
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V2.3")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Team", list(st.session_state.players.keys()))
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Dashboard")
    
    tab1, tab2 = st.tabs(["⚡ Control Center", "📊 Reports"])
    
    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader("Player Status")
            status_data = []
            ready_cnt = 0
            for t, p in st.session_state.players.items():
                loc = p['location'] if p['location'] else "-"
                sts = "✅ Submitted" if p['status'] == 'Submitted' else "⏳ Thinking"
                if p['status'] == 'Submitted': ready_cnt += 1
                
                # Check for Alert
                alert = "🚨" if p.get('alert') else ""
                
                status_data.append({
                    "Team": t, 
                    "Location": loc, 
                    "Status": sts + " " + alert, 
                    "Cash": f"${p['financials']['cash']:,.0f}",
                    "E-Loan": f"${p['financials']['emergency_loan']:,.0f}"
                })
            st.dataframe(pd.DataFrame(status_data), hide_index=True)
            
        with c2:
            st.metric("Ready", f"{ready_cnt}/7")
            if st.button("🚀 Run Period", type="primary"):
                process_period()
                st.success("Simulation Processed!")
                st.rerun()

    with tab2:
        st.subheader("Comparative Report")
        # (Report rendering logic remains similar but can include Rent/Tax details if needed)
        st.write("Use the Student View to see detailed Income Statements.")

elif role == "Student":
    p_data = st.session_state.players[team]
    
    if not p_data['location']:
        st.warning("Please Select Location to Start")
        # แสดง Info ของแต่ละทำเลให้ผู้เล่นตัดสินใจ
        st.info("**Medical Center**: High Rent (4.5%), Service Critical, Price Inelastic")
        st.info("**Neighborhood**: Low Rent (2.5%), Price Sensitive")
        st.info("**Shopping Center**: Moderate Rent (3.0%), High Traffic")
        loc = st.radio("Location", LOCATIONS)
        if st.button("Confirm Location"):
            p_data['location'] = loc
            st.rerun()
    else:
        st.title(f"🏥 {team} ({p_data['location']})")
        
        # Alert Display
        if p_data.get('alert'):
            st.error(p_data['alert'])
        
        # History Table
        if p_data['history']:
            last = p_data['history'][-1]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Market Share", f"{last['Market Share']:.2f}%")
            c2.metric("Net Profit", f"${last['Net Profit']:,.0f}", delta_color="normal")
            c3.metric("Cash Balance", f"${last['Cash']:,.0f}")
            c4.metric("Rent Paid", f"${last['Rent']:,.0f}")
            
            with st.expander("📜 Income Statement (Last Period)"):
                st.json(last) # Simplified view for debugging/checking

        if p_data['status'] == 'Submitted':
            st.info("Submitted. Waiting for Instructor...")
            if st.button("Cancel"):
                p_data['status'] = 'Thinking'
                st.rerun()
        else:
            with st.form("decision_form"):
                st.subheader(f"Decisions for Period {st.session_state.global_period}")
                
                with st.expander("1. Pricing & Marketing", expanded=True):
                    c1, c2 = st.columns(2)
                    v1 = c1.number_input("Rx Markup (%)", value=49.0, help="Standard is ~50%")
                    v2 = c2.number_input("Rx Fee ($)", value=0.0)
                    v3 = c1.number_input("Promo Budget ($)", value=600.0)
                    v_otc_mark = c2.number_input("OTC Markup (%)", value=45.0)
                    
                    st.caption("Service Options (Affects Service Score)")
                    col_s1, col_s2, col_s3 = st.columns(3)
                    v4 = col_s1.checkbox("Delivery Service", True)
                    v5 = col_s2.checkbox("Patient Records", True)
                    v6 = col_s3.checkbox("Credit Service", True)

                with st.expander("2. Operations & Staff", expanded=True):
                    c1, c2 = st.columns(2)
                    v7 = c1.number_input("Hours Open/Week", value=46.0)
                    v17 = c2.number_input("Pharmacists (FTE)", value=1.0)
                    v18 = c1.number_input("Pharm Wage ($/hr)", value=20.0)
                    v19 = c2.number_input("Clerks (FTE)", value=1.0)
                    v20 = c1.number_input("Clerk Wage ($/hr)", value=5.0)
                    v21 = c2.number_input("Manager Salary ($/Period)", value=8000.0)

                with st.expander("3. Purchasing & Finance"):
                    c1, c2 = st.columns(2)
                    v15 = c1.number_input("Buy Rx Inventory ($)", value=20000.0)
                    v16 = c2.number_input("Buy OTC Inventory ($)", value=10000.0)
                    v_ap = c1.number_input("Pay Accounts Payable ($)", value=0.0)
                    v_debt = c2.number_input("Pay Long Term Debt ($)", value=0.0)
                    # ตัด Mortgage ออก เพราะคำนวณอัตโนมัติแล้ว

                if st.form_submit_button("✅ Submit Decisions"):
                    decisions = {
                        'rx_markup': v1, 'rx_fee': v2, 'promo_exp': v3,
                        'delivery': v4, 'records': v5, 'credit': v6,
                        'hours_open': v7, 'n_pharm': v17, 'wage_pharm': v18,
                        'n_clerk': v19, 'wage_clerk': v20, 'manager_salary': v21,
                        'buy_rx': v15, 'buy_otc': v16, 'otc_markup': v_otc_mark,
                        'payment_ap': v_ap, 'debt_payment_long': v_debt
                    }
                    p_data['last_decision'] = decisions
                    p_data['status'] = 'Submitted'
                    st.rerun()

elif role == "Instructor" and not is_admin:
    st.error("Wrong Password")
