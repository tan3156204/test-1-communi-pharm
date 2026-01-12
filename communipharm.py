import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. System Config (ค่าคงที่ระบบ)
# ==========================================
st.set_page_config(page_title="Communi-Pharm (Manual Exact)", layout="wide")
ADMIN_PASSWORD = "admin1234"
LOCATIONS = ["Med Center", "Neighborhood", "Shopping"]

# ค่าความสำคัญ (Weights) 10 ตัวแปร (อ้างอิงหน้า 3 และ 11 ของคู่มือ)
DEFAULT_WEIGHTS = {
    "Med Center": {
        "rx_price": 5,       # ราคายา (Past+Present)
        "promotion": 3,      # การโฆษณา
        "hours": 7,          # เวลาเปิดร้าน
        "service": 9,        # บริการ (Delivery + Records + Credit)
        "inventory": 8,      # ความพร้อมของสินค้า
        "staffing": 8,       # ความรวดเร็ว (เภสัชกร)
        "prev_share": 5,     # โมเมนตัมตลาดเก่า
        "base_traffic": 5000 # ฐานลูกค้าในทำเล
    },
    "Neighborhood": {
        "rx_price": 6, "promotion": 5, "hours": 5,
        "service": 6, "inventory": 6, "staffing": 5,
        "prev_share": 6, "base_traffic": 3500
    },
    "Shopping": {
        "rx_price": 10, "promotion": 9, "hours": 4,
        "service": 2, "inventory": 5, "staffing": 7,
        "prev_share": 4, "base_traffic": 6000
    }
}

# ==========================================
# 2. State & Data
# ==========================================
if 'location_weights' not in st.session_state:
    st.session_state.location_weights = DEFAULT_WEIGHTS.copy()

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
                'short_term_loans': 0.0,
                'last_market_share': 14.28
            },
            'history': []
        }

if 'global_period' not in st.session_state:
    st.session_state.global_period = 1

# ==========================================
# 3. Logic Engine (Formula from Manual Page 10)
# ==========================================

def get_rank_score(series, ascending=True):
    """
    แปลงค่าเป็นคะแนนตามลำดับ (Rank Score)
    - สูตร: อันดับที่ 1 (ดีสุด) ได้ N คะแนน, อันดับสุดท้ายได้ 1 คะแนน
    - ascending=True: ค่าน้อยดี (เช่น ราคา) -> ค่าน้อยได้ Rank 1 (คะแนน N)
    - ascending=False: ค่ามากดี (เช่น โฆษณา) -> ค่ามากได้ Rank 1 (คะแนน N)
    """
    # rank(method='min') ให้เลข 1, 2, 3...
    ranks = series.rank(ascending=ascending, method='min') 
    
    # แปลง Rank เป็น Points (ที่ 1 ได้คะแนนเยอะสุด)
    # Points = (N_Teams + 1) - Rank
    n_teams = len(series)
    points = (n_teams + 1) - ranks
    return points

def process_period():
    # 1. แยกกลุ่มทีมตามทำเล (Market Segments)
    loc_pools = {loc: [] for loc in LOCATIONS}
    for t, data in st.session_state.players.items():
        if data['location'] and data['status'] == 'Submitted':
            loc_pools[data['location']].append(t)

    # 2. คำนวณทีละตลาด
    for loc, teams in loc_pools.items():
        if not teams: continue
        
        # ดึง Config ของทำเลนั้น
        weights = st.session_state.location_weights[loc]
        base_traffic = weights['base_traffic']
        
        # เตรียม Dataframe สำหรับ Ranking
        data_rows = []
        for t in teams:
            d = st.session_state.players[t]['last_decision']
            f = st.session_state.players[t]['financials']
            
            # คำนวณ Service Level (รวม Delivery, Records, Credit)
            service_lvl = (1 if d['delivery'] else 0) + (1 if d['records'] else 0) + (1 if d['credit'] else 0)
            
            # คำนวณ Price Index (Rx Fee + Markup Effect)
            # (แปลง markup เป็นตัวเงินคร่าวๆ เพื่อเทียบ: cost $10 * markup%)
            estimated_price = 10 * (1 + d['rx_markup']/100) + d['rx_fee']
            
            row = {
                'team': t,
                'price': estimated_price,       # ยิ่งน้อยยิ่งดี
                'promo': d['promo_exp'],        # ยิ่งมากยิ่งดี
                'hours': d['hours_open'],       # ยิ่งมากยิ่งดี
                'service': service_lvl,         # ยิ่งมากยิ่งดี
                'inventory': f['inventory_rx'], # ยิ่งมากยิ่งดี
                'staff': d['n_pharm'],          # ยิ่งมากยิ่งดี
                'prev_share': f['last_market_share'], # ยิ่งมากยิ่งดี
                # Wage Check: เช็คว่าจ่ายค่าแรงต่ำกว่าตลาดไหม (สมมติมาตรฐาน $20)
                'wage_rate': d['wage_pharm']
            }
            data_rows.append(row)
            
        df = pd.DataFrame(data_rows).set_index('team')
        
        # --- กฏ Wage Penalty (จากคู่มือหน้า 17) ---
        avg_wage = df['wage_rate'].mean()
        # ถ้าจ่ายต่ำกว่า 90% ของค่าเฉลี่ยตลาด ให้ลดคะแนน Staff ลง 50%
        df['staff_effective'] = df.apply(lambda x: x['staff'] * 0.5 if x['wage_rate'] < (avg_wage * 0.9) else x['staff'], axis=1)

        # --- คำนวณคะแนนดิบ (Weighted Rank Points) ---
        # สูตร: Sum (Rank Score * Weight)
        
        scores = pd.Series(0.0, index=df.index)
        
        # 1. Price (ค่าน้อย = Rank ดี)
        scores += get_rank_score(df['price'], ascending=True) * weights['rx_price']
        
        # 2. Promotion (ค่ามาก = Rank ดี)
        scores += get_rank_score(df['promo'], ascending=False) * weights['promotion']
        
        # 3. Hours
        scores += get_rank_score(df['hours'], ascending=False) * weights['hours']
        
        # 4. Service
        scores += get_rank_score(df['service'], ascending=False) * weights['service']
        
        # 5. Inventory
        scores += get_rank_score(df['inventory'], ascending=False) * weights['inventory']
        
        # 6. Staffing (ใช้ effective staff ที่หัก penalty แล้ว)
        scores += get_rank_score(df['staff_effective'], ascending=False) * weights['staffing']
        
        # 7. Momentum (Prev Share)
        scores += get_rank_score(df['prev_share'], ascending=False) * weights['prev_share']

        # --- คำนวณ Market Share (%) ---
        total_mkt_score = scores.sum()
        market_shares = scores / total_mkt_score # สัดส่วนคะแนนเรา / คะแนนรวม
        
        # --- คำนวณงบการเงิน (Financial Statements) ---
        for t in teams:
            player = st.session_state.players[t]
            d = player['last_decision']
            fin = player['financials']
            
            share = market_shares[t]
            my_traffic = base_traffic * share
            
            # ยอดขาย (Rx & OTC)
            rx_units = int(my_traffic * 0.35)
            otc_units = int(my_traffic * 0.65)
            
            # Revenue
            rx_cost = 10.0 # สมมติทุนยาเฉลี่ย
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
            
            # Expenses
            # Wages = (N * Rate * Hours * 4 weeks)
            wages = (d['n_pharm'] * d['wage_pharm'] + d['n_clerk'] * d['wage_clerk']) * d['hours_open'] * 4
            mgr_salary = d['manager_salary']
            
            # Fixed & Variable
            rent = d['mortgage_payment']
            utilities = 1000
            ads = d['promo_exp']
            
            # Interest (ดอกเบี้ย) - คู่มือระบุให้คิด
            interest_exp = (fin['long_term_debt'] * 0.01) # สมมติ 1% ต่อเดือน
            
            total_exp = wages + mgr_salary + rent + utilities + ads + interest_exp
            
            net_profit = gross_margin - total_exp
            
            # Cash Flow
            # Cash In = Sales
            # Cash Out = Expenses + Purchases + Debt Payment
            cash_in = total_rev
            purchases = d['buy_rx'] + d['buy_otc']
            debt_pay = d['payment_ap'] + d['debt_payment_long']
            
            fin['cash'] += (cash_in - total_exp - purchases - debt_pay)
            
            # Update Balance Sheet
            fin['inventory_rx'] += (d['buy_rx'] - rx_cogs)
            fin['inventory_otc'] += (d['buy_otc'] - otc_cogs)
            fin['long_term_debt'] -= d['debt_payment_long']
            fin['last_market_share'] = share * 100
            
            # History Log
            player['history'].append({
                "Period": st.session_state.global_period,
                "Market Share": f"{share*100:.2f}%",
                "Customers": int(my_traffic),
                "Revenue": total_rev,
                "Expenses": total_exp,
                "Net Profit": net_profit,
                "Cash": fin['cash']
            })
            
            # Reset Status
            player['status'] = 'Thinking'
            player['period'] += 1

    st.session_state.global_period += 1

def make_input(label, key, default):
    return st.number_input(label, value=float(default), step=1.0, key=key)

# ==========================================
# 4. User Interface
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm")
    st.caption("Engine: V2.2 Exact Manual Formula")
    role = st.selectbox("Role", ["Student", "Instructor"])
    
    if role == "Student":
        team = st.selectbox("Team", list(st.session_state.players.keys()))
    else:
        pwd = st.text_input("Password", type="password")
        is_admin = (pwd == ADMIN_PASSWORD)

if role == "Instructor" and is_admin:
    st.title("👨‍🏫 Instructor Panel")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("Team Status")
        status_data = []
        ready_cnt = 0
        for t, p in st.session_state.players.items():
            loc = p['location'] if p['location'] else "-"
            sts = "✅ Submitted" if p['status'] == 'Submitted' else "⏳ Thinking"
            if p['status'] == 'Submitted': ready_cnt += 1
            status_data.append({"Team": t, "Location": loc, "Status": sts, "Cash": f"${p['financials']['cash']:,.0f}"})
        st.dataframe(pd.DataFrame(status_data), hide_index=True)
        
    with c2:
        st.metric("Ready", f"{ready_cnt}/7")
        if st.button("🚀 Run Period", type="primary"):
            process_period()
            st.success("Simulation Processed!")
            st.rerun()

elif role == "Student":
    p_data = st.session_state.players[team]
    
    if not p_data['location']:
        st.warning("Please Select Location")
        loc = st.radio("Location", LOCATIONS)
        if st.button("Confirm"):
            p_data['location'] = loc
            st.rerun()
    else:
        st.title(f"🏥 {team} ({p_data['location']})")
        
        # History
        if p_data['history']:
            last = p_data['history'][-1]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Market Share", last['Market Share'])
            c2.metric("Net Profit", f"${last['Net Profit']:,.0f}")
            c3.metric("Cash", f"${last['Cash']:,.0f}")
            c4.metric("Customers", last['Customers'])
            st.dataframe(pd.DataFrame(p_data['history']))

        if p_data['status'] == 'Submitted':
            st.info("Submitted. Waiting for Instructor...")
            if st.button("Cancel"):
                p_data['status'] = 'Thinking'
                st.rerun()
        else:
            with st.form("decision_form"):
                st.subheader(f"Decisions for Period {st.session_state.global_period}")
                
                # Group 1: Pricing
                with st.expander("1. Pricing & Marketing", expanded=True):
                    c1, c2 = st.columns(2)
                    v1 = c1.number_input("Rx Markup (%)", value=49.0)
                    v2 = c2.number_input("Rx Fee ($)", value=0.0)
                    v3 = c1.number_input("Promo Budget ($)", value=600.0)
                    v4 = c2.checkbox("Delivery Service", True)
                    v5 = c1.checkbox("Patient Records", True)
                    v6 = c2.checkbox("Credit Service", True)

                # Group 2: Operations
                with st.expander("2. Operations & Staff", expanded=True):
                    c1, c2 = st.columns(2)
                    v7 = c1.number_input("Hours Open/Week", value=46.0)
                    v17 = c2.number_input("Pharmacists (FTE)", value=1.0)
                    v18 = c1.number_input("Pharm Wage ($/hr)", value=20.0)
                    v19 = c2.number_input("Clerks (FTE)", value=1.0)
                    v20 = c1.number_input("Clerk Wage ($/hr)", value=5.0)
                    v21 = c2.number_input("Manager Salary ($)", value=8000.0)

                # Group 3: Purchasing
                with st.expander("3. Purchasing & Finance"):
                    c1, c2 = st.columns(2)
                    v15 = c1.number_input("Buy Rx Inventory ($)", value=20000.0)
                    v16 = c2.number_input("Buy OTC Inventory ($)", value=10000.0)
                    v_ap = c1.number_input("Pay Accounts Payable ($)", value=0.0)
                    v_debt = c2.number_input("Pay Long Term Debt ($)", value=0.0)
                    # Hidden inputs
                    v_otc_mark = 45.0
                    v_mort = 900.0

                if st.form_submit_button("✅ Submit Decisions"):
                    decisions = {
                        'rx_markup': v1, 'rx_fee': v2, 'promo_exp': v3,
                        'delivery': v4, 'records': v5, 'credit': v6,
                        'hours_open': v7, 'n_pharm': v17, 'wage_pharm': v18,
                        'n_clerk': v19, 'wage_clerk': v20, 'manager_salary': v21,
                        'buy_rx': v15, 'buy_otc': v16, 'otc_markup': v_otc_mark,
                        'payment_ap': v_ap, 'debt_payment_long': v_debt,
                        'mortgage_payment': v_mort
                    }
                    p_data['last_decision'] = decisions
                    p_data['status'] = 'Submitted'
                    st.rerun()

elif role == "Instructor" and not is_admin:
    st.error("Wrong Password")
