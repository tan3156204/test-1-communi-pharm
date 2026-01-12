import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config
# ==========================================
st.set_page_config(page_title="Communi-Pharm V2.4 (Named)", layout="wide")
ADMIN_PASSWORD = "admin1234"
LOCATIONS = ["Med Center", "Neighborhood", "Shopping"]

LOCATION_CONFIG = {
    "Med Center": {
        "rent_rate": 0.045, 
        "weights": {"rx_price": 2, "promotion": 2, "hours": 6, "service": 10, "inventory": 8, "staffing": 8, "prev_share": 5},
        "base_traffic": 5000,
        "desc": "เน้นบริการ ไม่เกี่ยงราคา (ค่าเช่าแพง)"
    },
    "Neighborhood": {
        "rent_rate": 0.025,
        "weights": {"rx_price": 10, "promotion": 7, "hours": 5, "service": 5, "inventory": 6, "staffing": 5, "prev_share": 6},
        "base_traffic": 3500,
        "desc": "ลูกค้าประหยัด อ่อนไหวต่อราคา"
    },
    "Shopping": {
        "rent_rate": 0.030,
        "weights": {"rx_price": 7, "promotion": 10, "hours": 4, "service": 3, "inventory": 5, "staffing": 7, "prev_share": 4},
        "base_traffic": 6000,
        "desc": "คนพลุกพล่าน เน้นโปรโมชั่น"
    }
}

# ==========================================
# 2. State Management
# ==========================================
if 'players' not in st.session_state:
    st.session_state.players = {}
    for i in range(1, 8):
        team_name = f"Team {i}"
        st.session_state.players[team_name] = {
            'shop_name': team_name, # <--- [NEW] ชื่อร้านเริ่มต้น
            'location': None,
            'period': 1,
            'status': 'Thinking',
            'last_decision': {},
            'financials': {
                'cash': 40000.0, 'inventory_rx': 20000.0, 'inventory_otc': 15000.0,
                'accounts_payable': 0.0, 'long_term_debt': 0.0, 'emergency_loan': 0.0,
                'last_market_share': 14.28
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Game Engine (Logic เดิม)
# ==========================================
def get_rank_score(series, ascending=True):
    ranks = series.rank(ascending=ascending, method='min')
    n_teams = len(series)
    return (n_teams + 1) - ranks

def process_period():
    loc_pools = {loc: [] for loc in LOCATIONS}
    for t, data in st.session_state.players.items():
        if data['location'] and data['status'] == 'Submitted':
            loc_pools[data['location']].append(t)

    for loc, teams in loc_pools.items():
        if not teams: continue
        config = LOCATION_CONFIG[loc]
        weights = config['weights']
        base_traffic = config['base_traffic']
        rent_rate = config['rent_rate']
        
        data_rows = []
        for t in teams:
            d = st.session_state.players[t]['last_decision']
            f = st.session_state.players[t]['financials']
            
            service_score = (1 if d['delivery'] else 0) + (1 if d['records'] else 0) + (1 if d['credit'] else 0)
            est_price = 10 * (1 + d['rx_markup']/100) + d['rx_fee']
            
            row = {
                'team': t, 'price': est_price, 'promo': d['promo_exp'], 'hours': d['hours_open'],
                'service': service_score, 'inventory': f['inventory_rx'], 'staff': d['n_pharm'],
                'wage_rate': d['wage_pharm'], 'prev_share': f['last_market_share']
            }
            data_rows.append(row)
            
        df = pd.DataFrame(data_rows).set_index('team')
        avg_wage = df['wage_rate'].mean()
        df['staff_effective'] = df.apply(lambda x: x['staff'] * 0.6 if x['wage_rate'] < (avg_wage * 0.9) else x['staff'], axis=1)

        scores = pd.Series(0.0, index=df.index)
        scores += get_rank_score(df['price'], ascending=True) * weights['rx_price']
        scores += get_rank_score(df['promo'], ascending=False) * weights['promotion']
        scores += get_rank_score(df['hours'], ascending=False) * weights['hours']
        scores += get_rank_score(df['service'], ascending=False) * weights['service']
        scores += get_rank_score(df['inventory'], ascending=False) * weights['inventory']
        scores += get_rank_score(df['staff_effective'], ascending=False) * weights['staffing']
        scores += get_rank_score(df['prev_share'], ascending=False) * weights['prev_share']

        total_score = scores.sum()
        market_shares = scores / total_score if total_score > 0 else 0
        
        for t in teams:
            player = st.session_state.players[t]
            d = player['last_decision']
            fin = player['financials']
            share = market_shares[t]
            market_size_factor = len(teams)
            my_traffic = base_traffic * share * market_size_factor
            
            rx_units = int(my_traffic * 0.35)
            otc_units = int(my_traffic * 0.65)
            
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
            
            weeks_per_period = 13
            wages = (d['n_pharm'] * d['wage_pharm'] + d['n_clerk'] * d['wage_clerk']) * d['hours_open'] * weeks_per_period
            mgr_salary = d['manager_salary']
            rent_exp = total_rev * rent_rate
            utilities = 1500; ads = d['promo_exp']; depreciation = 500
            interest_exp = (fin['long_term_debt'] * 0.02) + (fin['emergency_loan'] * 0.05)
            other_taxes = total_rev * 0.015
            
            total_exp = wages + mgr_salary + rent_exp + utilities + ads + interest_exp + depreciation + other_taxes
            net_profit_before_tax = gross_margin - total_exp
            income_tax = net_profit_before_tax * 0.20 if net_profit_before_tax > 0 else 0
            net_profit = net_profit_before_tax - income_tax
            
            cash_in = total_rev
            purchases = d['buy_rx'] + d['buy_otc']
            debt_pay = d['payment_ap'] + d['debt_payment_long']
            cash_out = (total_exp - depreciation) + purchases + debt_pay + income_tax
            
            fin['cash'] += (cash_in - cash_out)
            
            if fin['cash'] < 0:
                loan_needed = abs(fin['cash']) + 1000
                fin['emergency_loan'] += loan_needed
                fin['cash'] += loan_needed
                player['alert'] = f"🚨 Cash Shortage! Emergency Loan: ${loan_needed:,.0f}"
            else:
                player['alert'] = None

            fin['inventory_rx'] += (d['buy_rx'] - rx_cogs)
            fin['inventory_otc'] += (d['buy_otc'] - otc_cogs)
            fin['long_term_debt'] -= d['debt_payment_long']
            fin['last_market_share'] = share * 100
            
            player['history'].append({
                "Period": st.session_state.global_period, "Market Share": share * 100,
                "Total Sales": total_rev, "Net Profit": net_profit, "Cash": fin['cash'],
                "Rent": rent_exp, "Emerg Loan": fin['emergency_loan'], "Decision": d
            })
            player['status'] = 'Thinking'
            player['period'] += 1
    st.session_state.global_period += 1

# ==========================================
# 4. User Interface
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V2.4")
    role = st.selectbox("Login Role", ["Student", "Instructor"])
    if role == "Student":
        team = st.selectbox("Select Team", list(st.session_state.players.keys()))
    else:
        pwd = st.text_input("Admin Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Control Center")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Player Status")
        status_data = []
        ready_count = 0
        for t, p in st.session_state.players.items():
            s_name = p.get('shop_name', t) # <--- [NEW] แสดงชื่อร้าน
            loc = p['location'] if p['location'] else "❌ Not Selected"
            sts = "✅ Submitted" if p['status'] == 'Submitted' else "⏳ Thinking"
            if p['status'] == 'Submitted': ready_count += 1
            alert_icon = "⚠️" if p.get('alert') else ""
            
            status_data.append({
                "Team": t, "Shop Name": s_name, "Location": loc,
                "Status": sts, "Alert": alert_icon,
                "Cash": f"${p['financials']['cash']:,.0f}"
            })
        st.dataframe(pd.DataFrame(status_data), hide_index=True, use_container_width=True)
    with col2:
        st.metric("Ready to Run", f"{ready_count} / 7")
        if st.button("🚀 Process Period", type="primary"):
            process_period()
            st.success("Simulation Computed!"); st.rerun()

elif role == "Student":
    p_data = st.session_state.players[team]
    
    # --- [NEW] Sidebar for Shop Name ---
    with st.sidebar:
        st.markdown("---")
        st.subheader("🏷️ Shop Identity")
        new_name = st.text_input("Shop Name", value=p_data.get('shop_name', team))
        if st.button("Save Name"):
            p_data['shop_name'] = new_name
            st.rerun()

    if not p_data['location']:
        st.header("📍 Select Store Location")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🏥 Medical Center")
            st.write(LOCATION_CONFIG["Med Center"]["desc"]); st.write("**Rent:** 4.5%")
            if st.button("Select Med Center"): p_data['location'] = "Med Center"; st.rerun()
        with col2:
            st.subheader("🏡 Neighborhood")
            st.write(LOCATION_CONFIG["Neighborhood"]["desc"]); st.write("**Rent:** 2.5%")
            if st.button("Select Neighborhood"): p_data['location'] = "Neighborhood"; st.rerun()
        with col3:
            st.subheader("🛍️ Shopping Center")
            st.write(LOCATION_CONFIG["Shopping"]["desc"]); st.write("**Rent:** 3.0%")
            if st.button("Select Shopping"): p_data['location'] = "Shopping"; st.rerun()
    else:
        shop_display = p_data.get('shop_name', team) # <--- [NEW] ใช้ชื่อร้านที่ตั้ง
        st.title(f"🏥 {shop_display}")
        st.caption(f"Team: {team} | Location: {p_data['location']} | Period: {st.session_state.global_period}")
        
        if p_data.get('alert'): st.error(p_data['alert'])
        if p_data['history']:
            last = p_data['history'][-1]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Market Share", f"{last['Market Share']:.2f}%")
            m2.metric("Net Profit", f"${last['Net Profit']:,.0f}")
            m3.metric("Cash Balance", f"${last['Cash']:,.0f}")
            m4.metric("Emerg Loan", f"${last['Emerg Loan']:,.0f}")
        
        if p_data['status'] == 'Submitted':
            st.info("✅ Decisions Submitted. Waiting for Instructor.")
            if st.button("Cancel Submission"): p_data['status'] = 'Thinking'; st.rerun()
        else:
            with st.form("decision_form"):
                st.subheader("📝 Decisions Input")
                with st.expander("1. Pricing & Marketing", expanded=True):
                    c1, c2 = st.columns(2)
                    v_markup = c1.number_input("Rx Markup (%)", value=50.0)
                    v_fee = c2.number_input("Rx Fee ($)", value=0.0)
                    v_promo = c1.number_input("Promo Budget ($)", value=600.0)
                    v_otc_mark = c2.number_input("OTC Markup (%)", value=45.0)
                    sc1, sc2, sc3 = st.columns(3)
                    v_del = sc1.checkbox("Delivery", True); v_rec = sc2.checkbox("Patient Records", True); v_crd = sc3.checkbox("Credit", True)
                with st.expander("2. Operations & Staffing", expanded=True):
                    c1, c2 = st.columns(2)
                    v_hours = c1.number_input("Hours Open/Week", value=46.0)
                    v_n_pharm = c2.number_input("Pharmacists (FTE)", value=1.0)
                    v_w_pharm = c1.number_input("Pharm Wage ($/hr)", value=20.0)
                    v_n_clerk = c2.number_input("Clerks (FTE)", value=1.0)
                    v_w_clerk = c1.number_input("Clerk Wage ($/hr)", value=6.0)
                    v_mgr_sal = c2.number_input("Manager Salary", value=8000.0)
                with st.expander("3. Purchasing & Finance"):
                    c1, c2 = st.columns(2)
                    v_buy_rx = c1.number_input("Buy Rx Inventory", value=20000.0)
                    v_buy_otc = c2.number_input("Buy OTC Inventory", value=10000.0)
                    v_pay_ap = c1.number_input("Pay AP", value=0.0)
                    v_pay_debt = c2.number_input("Pay Long Term Debt", value=0.0)
                
                if st.form_submit_button("✅ Submit Decisions"):
                    p_data['last_decision'] = {
                        'rx_markup': v_markup, 'rx_fee': v_fee, 'promo_exp': v_promo,
                        'otc_markup': v_otc_mark, 'delivery': v_del, 'records': v_rec,
                        'credit': v_crd, 'hours_open': v_hours, 'n_pharm': v_n_pharm,
                        'wage_pharm': v_w_pharm, 'n_clerk': v_n_clerk, 'wage_clerk': v_w_clerk,
                        'manager_salary': v_mgr_sal, 'buy_rx': v_buy_rx, 'buy_otc': v_buy_otc,
                        'payment_ap': v_pay_ap, 'debt_payment_long': v_pay_debt
                    }
                    p_data['status'] = 'Submitted'; st.rerun()

elif role == "Instructor" and not is_admin:
    st.error("❌ Incorrect Password")
