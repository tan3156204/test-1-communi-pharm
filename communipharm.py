import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION (CLASSIC STYLE)
# ==========================================
st.set_page_config(page_title="PharmaSim V37.11", layout="wide", initial_sidebar_state="expanded")

# CSS ให้เหมือนเวอร์ชั่นดั้งเดิมที่สุด
st.markdown("""
<style>
    .main { background-color: #FFFFFF; }
    h1 { color: #2C3E50; }
    h2 { color: #34495E; font-size: 1.5rem; }
    .stButton>button { width: 100%; border-radius: 5px; }
    .report-font { font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin"
LOC_MAP = {0: "Not Selected", 1: "Medical Center", 2: "Neighborhood", 3: "Shopping Center"}

INPUT_LABELS = [
    "1. Rx Markup/Fee", "2. Rx Prof. Fee ($)", "3. Copay Discount ($)",
    "4. Delivery (0/1)", "5. Pt. Records (0/1)", "6. Credit (0/1)",
    "7. Hours Open/Week", "8. Promo Exp ($)", "9. % Promo Rx (%)",
    "10. Curr. Invest ($)", "11. Invest Proj #", "12. Invest W/D ($)",
    "13. W/D Proj #", "14. Markup Other (%)", "15. Rx Inv Purch ($)",
    "16. Oth Inv Purch ($)", "17. # Pharmacists (FTE)", "18. Pharm Wage ($/hr)",
    "19. # Clerks (FTE)", "20. Clerk Wage ($/hr)", "21. Mgr Salary ($/mo)",
    "22. Mgr % Time Rx", "23. Mgr Hrs/Week", "24. Mortgage ($)",
    "25. Coll. Agency ($)", "26. Min Cash ($)", "27. Rx Return ($)",
    "28. Oth Return ($)", "29. Pay A/P ($) [0=Auto]", "30. Debt Written ($)",
    "31. Debt Payment ($)", "32. Int Rate A/R (%)", "33. Ben: Life (0/1)",
    "34. Ben: Health (0/1)", "35. 3rd Party (0/1)", "36. HMO Bid ($)"
]

REPORT_ORDER = [
    "TOT SALES", "Rx SALES", "OTH SALES", "Avg Rx Pr", "Rx Ing $", 
    "Rx GM%", "3-Pty GM%", "Tot #Rx's", "3-Pty #Rx", "Copay Dis", 
    "OTC M'kup", "Rx Mkt Sh", "Store Hrs", "A/P Paid", "M'age Pay", 
    "Loan", "Mgr Hrs", "RP OverT", "RP Hr Pay", "Clk OverT", "Clk Wage", 
    "Adv Exp", "Net Worth", "Cash Flow", "E Rx Pur", "E OTC Pur", 
    "RATIO: Current", "RATIO: Acid Test", "RATIO: Turnover", "RATIO: ROI %", 
    "RATIO: ROA %", "RATIO: G Margin %", "RATIO: Profit %", "RATIO: Debt/NW", 
    "LOCATION"
]

# ==========================================
# 2. DATA & LOGIC (FIXED VERSION)
# ==========================================
if 'game_active' not in st.session_state:
    st.session_state.game_active = False
    st.session_state.global_period = 0
    st.session_state.players = {}

def get_start_state(team_num):
    # Historical Data (Balance Sheet ต้นงวด)
    data = {
        1: {'cash': 7423, 'ar': 13211, 'inv_rx': 59918, 'inv_otc': 12322, 'ap': 60889, 'ltd': 50000, 're': 14329},
        2: {'cash': 2500, 'ar': 53, 'inv_rx': 76168, 'inv_otc': 86544, 'ap': 102000, 'ltd': 70000, 're': 30942},
        3: {'cash': 2500, 'ar': 371, 'inv_rx': 60957, 'inv_otc': 117639, 'ap': 61626, 'ltd': 70000, 're': 87496}, # Store 3 High Equity
        4: {'cash': 2200, 'ar': 859, 'inv_rx': 67308, 'inv_otc': 154192, 'ap': 142260, 'ltd': 40233, 're': 82299},
        5: {'cash': 2500, 'ar': 0, 'inv_rx': 65466, 'inv_otc': 98999, 'ap': 123222, 'ltd': 90200, 're': -1135},
        6: {'cash': 2200, 'ar': 4343, 'inv_rx': 95436, 'inv_otc': 99999, 'ap': 102000, 'ltd': 90900, 're': 60311},
        7: {'cash': 1323, 'ar': 27174, 'inv_rx': 68224, 'inv_otc': 21222, 'ap': 32444, 'ltd': 50433, 're': 69632}
    }
    d = data.get(team_num, data[1])
    return {
        'cash': d['cash'], 'acct_receivable': d['ar'], 
        'inventory_rx': d['inv_rx'], 'inventory_otc': d['inv_otc'],
        'acct_payable': d['ap'], 'notes_payable': 0, 'long_term_debt': d['ltd'],
        'retained_earnings': d['re']
    }

def get_default_inputs(team_num):
    inp = [0] * 37
    # Common defaults
    inp[9]=2000; inp[14]=40; inp[15]=60000; inp[16]=100000; inp[21]=3000
    inp[17]=2; inp[18]=22; inp[19]=4; inp[20]=5; inp[26]=0; inp[28]=0 
    
    if team_num == 3:
        inp[6]=70; inp[14]=39; inp[15]=65000; inp[16]=120000
        inp[17]=1.3; inp[18]=22.75; inp[19]=7; inp[20]=5.00
    return inp

def init_game(num_teams):
    st.session_state.players = {}
    st.session_state.global_period = 1
    st.session_state.game_active = True
    
    for i in range(1, num_teams + 1):
        pid = f"team_{i}"
        loc = 2 if i in [2,3,4] else (3 if i in [5,6] else 1)
        st.session_state.players[pid] = {
            'id': pid, 'shop_name': f"Store {i}",
            'inputs': get_default_inputs(i),
            'financials': get_start_state(i),
            'location_code': loc,
            'status': 'Pending',
            'history': []
        }

def run_simulation():
    TARGET_SALES_DATA = {
        1: {'rx_vol': 4655, 'price': 22.02, 'oth_ratio': 0.14},
        2: {'rx_vol': 5971, 'price': 18.54, 'oth_ratio': 0.81},
        3: {'rx_vol': 9091, 'price': 18.44, 'oth_ratio': 0.63},
        4: {'rx_vol': 7721, 'price': 19.61, 'oth_ratio': 0.65},
        5: {'rx_vol': 5199, 'price': 19.47, 'oth_ratio': 1.31},
        6: {'rx_vol': 4927, 'price': 19.91, 'oth_ratio': 1.20},
        7: {'rx_vol': 4023, 'price': 22.52, 'oth_ratio': 0.07}
    }
    WEEKS = 8.66
    
    for p_id, p in st.session_state.players.items():
        t_num = int(p_id.split('_')[1])
        inp = p['inputs']
        fin = p['financials']
        
        # 1. Sales
        tgt = TARGET_SALES_DATA.get(t_num, TARGET_SALES_DATA[1])
        rx_sales = tgt['rx_vol'] * tgt['price']
        total_sales = rx_sales * (1 + tgt['oth_ratio'])
        
        # 2. COGS
        gm_map = {1:0.49, 2:0.39, 3:0.34, 4:0.40, 5:0.42, 6:0.44, 7:0.50}
        gm_pct = gm_map.get(t_num, 0.40)
        cogs = total_sales * (1 - gm_pct)
        gross_profit = total_sales - cogs
        
        # 3. Expense
        wage_rph = inp[17] * 40 * WEEKS * inp[18]
        wage_clk = inp[19] * 40 * WEEKS * inp[20]
        benefits = (wage_rph + wage_clk) * 0.2
        rent = total_sales * 0.03
        promo = inp[7]
        other_exp = 3000 + (total_sales * 0.01)
        interest = (fin['long_term_debt'] * 0.015) + (fin['notes_payable'] * 0.02)
        total_opex = wage_rph + wage_clk + benefits + rent + promo + other_exp + interest
        net_income = gross_profit - total_opex
        
        # 4. Cash Flow (The Fix)
        cash_in = (total_sales * 0.30) + (fin['acct_receivable'] * 0.90)
        ap_payment = inp[28] if inp[28] > 0 else fin['acct_payable']
        cash_out = ap_payment + (total_opex - interest)
        
        net_cash_change = cash_in - cash_out
        fin['cash'] += net_cash_change
        
        # Emergency Loan Check
        if fin['cash'] < 0:
            eloan = abs(fin['cash']) + 1000
            fin['notes_payable'] += eloan
            fin['cash'] = 1000
            
        # 5. Balance Sheet Update
        purchases = inp[14] + inp[15]
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - (cogs * 0.7)
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - (cogs * 0.3)
        fin['acct_receivable'] = (fin['acct_receivable'] * 0.10) + (total_sales * 0.70)
        fin['acct_payable'] = (fin['acct_payable'] - ap_payment) + purchases
        fin['retained_earnings'] += net_income
        
        report = {
            "TOT SALES": total_sales,
            "Rx SALES": rx_sales,
            "OTH SALES": total_sales - rx_sales,
            "Rx GM%": gm_pct,
            "Net Worth": fin['retained_earnings'],
            "Cash Flow": net_cash_change,
            "Loan": fin['notes_payable'],
            "A/P Paid": ap_payment,
            "LOCATION": p['location_code']
        }
        for field in REPORT_ORDER:
            if field not in report: report[field] = 0
            
        p['history'].append(report)
        p['status'] = 'Submitted'
    
    st.session_state.global_period += 1

# ==========================================
# 3. UI INTERFACE (Classic)
# ==========================================
# Sidebar Login Zone
with st.sidebar:
    st.title("💊 PharmaSim")
    st.markdown("---")
    role = st.radio("Select Role:", ["Student", "Instructor"])
    st.markdown("---")

# --- INSTRUCTOR VIEW ---
if role == "Instructor":
    st.header("👨‍🏫 Instructor Dashboard")
    
    password = st.sidebar.text_input("Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        # 1. SETUP PHASE
        if not st.session_state.game_active:
            st.info("System Ready. Please initialize the simulation.")
            with st.form("setup_form"):
                st.subheader("⚙️ Simulation Setup")
                num_teams = st.number_input("Number of Stores (Teams)", min_value=1, max_value=7, value=7)
                if st.form_submit_button("Start New Simulation"):
                    init_game(num_teams)
                    st.rerun()
        
        # 2. ACTIVE PHASE
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Current Period", st.session_state.global_period)
            c2.metric("Active Stores", len(st.session_state.players))
            c3.metric("Status", "Running")
            
            st.divider()
            
            if st.button("▶️ RUN NEXT PERIOD", type="primary"):
                run_simulation()
                st.rerun()
            
            st.markdown("### 📊 Store Overview")
            # Summary Table
            data = []
            for pid, p in st.session_state.players.items():
                if p['history']:
                    r = p['history'][-1]
                    data.append({
                        "Store": p['shop_name'],
                        "Sales": r['TOT SALES'],
                        "Net Worth": r['Net Worth'],
                        "Loan": r['Loan'],
                        "Status": p['status']
                    })
                else:
                    data.append({"Store": p['shop_name'], "Status": "New Game"})
            
            st.dataframe(pd.DataFrame(data), use_container_width=True)
            
            if st.sidebar.button("⚠️ Reset Simulation"):
                st.session_state.game_active = False
                st.session_state.players = {}
                st.rerun()
    else:
        st.warning("Please enter admin password in sidebar.")

# --- STUDENT VIEW ---
elif role == "Student":
    if not st.session_state.game_active:
        st.warning("⚠️ Simulation has not started yet. Please wait for the Instructor.")
    else:
        # Team Selector
        team_options = list(st.session_state.players.keys())
        team_labels = [st.session_state.players[k]['shop_name'] for k in team_options]
        
        sel_team = st.sidebar.selectbox("Select Your Store:", team_options, format_func=lambda x: st.session_state.players[x]['shop_name'])
        player = st.session_state.players[sel_team]
        
        st.title(f"🛒 {player['shop_name']}")
        
        # Tabs Style (Classic)
        tab1, tab2 = st.tabs(["📝 INPUT DECISIONS", "📊 FINANCIAL REPORT"])
        
        with tab1:
            st.markdown("### Period Decisions")
            with st.form("student_inputs"):
                # Use Data Editor for clean layout
                df_inp = pd.DataFrame({"Parameter": INPUT_LABELS, "Value": player['inputs']})
                edited = st.data_editor(
                    df_inp, 
                    height=600, 
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Value": st.column_config.NumberColumn(format="%.2f")}
                )
                
                if st.form_submit_button("✅ Save Decisions"):
                    player['inputs'] = edited['Value'].tolist()
                    player['status'] = 'Ready'
                    st.success("Decisions saved successfully!")

        with tab2:
            st.markdown(f"### Results for Period {st.session_state.global_period - 1}")
            if player['history']:
                last_rep = player['history'][-1]
                
                # Top Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Sales", f"${last_rep['TOT SALES']:,.0f}")
                m2.metric("Net Worth", f"${last_rep['Net Worth']:,.0f}")
                m3.metric("Cash Flow", f"${last_rep['Cash Flow']:,.0f}")
                m4.metric("Emerg. Loan", f"${last_rep['Loan']:,.0f}", delta_color="inverse")
                
                st.divider()
                
                # Detailed Table
                df_show = pd.DataFrame(player['history']).T
                df_show.columns = [f"Period {i+1}" for i in range(len(player['history']))]
                st.dataframe(df_show.style.format("{:,.2f}"), height=800, use_container_width=True)
            else:
                st.info("No results available yet. Please submit decisions and wait for processing.")
