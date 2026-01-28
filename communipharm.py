import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(page_title="Communi-Pharm V37.9 (Full UI + Fixed Logic)", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .report-table { font-family: 'Courier New', monospace; font-size: 0.85em; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: 2px solid #4CAF50; }
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
# 2. DATA INITIALIZATION
# ==========================================
def get_start_state(team_num):
    # Historical Data from hisc1p1
    data = {
        1: {'cash': 7423, 'ar': 13211, 'inv_rx': 59918, 'inv_otc': 12322, 'ap': 60889, 'ltd': 50000, 're': 14329},
        2: {'cash': 2500, 'ar': 53, 'inv_rx': 76168, 'inv_otc': 86544, 'ap': 102000, 'ltd': 70000, 're': 30942},
        3: {'cash': 2500, 'ar': 371, 'inv_rx': 60957, 'inv_otc': 117639, 'ap': 61626, 'ltd': 70000, 're': 87496},
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
    
    # Specifics for Store 3 (Example)
    if team_num == 3:
        inp[6]=70; inp[14]=39; inp[15]=65000; inp[16]=120000
        inp[17]=1.3; inp[18]=22.75; inp[19]=7; inp[20]=5.00
    return inp

if 'game_state' not in st.session_state:
    st.session_state.game_state = "ACTIVE"
    st.session_state.global_period = 1
    st.session_state.players = {}
    # Init Players
    for i in range(1, 8):
        pid = f"team_{i}"
        loc = 2 if i in [2,3,4] else (3 if i in [5,6] else 1)
        st.session_state.players[pid] = {
            'id': pid, 'shop_name': f"Store {i} ({LOC_MAP[loc]})",
            'inputs': get_default_inputs(i),
            'financials': get_start_state(i),
            'location_code': loc,
            'status': 'Pending',
            'history': []
        }

# ==========================================
# 3. LOGIC ENGINE (THE FIX)
# ==========================================
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
        
        # 1. SALES
        tgt = TARGET_SALES_DATA.get(t_num, TARGET_SALES_DATA[1])
        total_sales = (tgt['rx_vol'] * tgt['price']) * (1 + tgt['oth_ratio'])
        rx_sales = tgt['rx_vol'] * tgt['price']
        
        # 2. COGS & GM
        gm_map = {1:0.49, 2:0.39, 3:0.34, 4:0.40, 5:0.42, 6:0.44, 7:0.50}
        gm_pct = gm_map.get(t_num, 0.40)
        cogs = total_sales * (1 - gm_pct)
        gross_profit = total_sales - cogs
        
        # 3. OPEX
        wage_rph = inp[17] * 40 * WEEKS * inp[18]
        wage_clk = inp[19] * 40 * WEEKS * inp[20]
        benefits = (wage_rph + wage_clk) * 0.2
        rent = total_sales * 0.03
        promo = inp[7]
        other_exp = 3000 + (total_sales * 0.01)
        interest = (fin['long_term_debt'] * 0.015) + (fin['notes_payable'] * 0.02)
        
        total_opex = wage_rph + wage_clk + benefits + rent + promo + other_exp + interest
        net_income = gross_profit - total_opex
        
        # 4. CASH FLOW (FIXED)
        cash_in = (total_sales * 0.30) + (fin['acct_receivable'] * 0.90)
        ap_payment = inp[28] if inp[28] > 0 else fin['acct_payable']
        cash_out = ap_payment + (total_opex - interest) # Interest handled/netted
        
        net_cash_change = cash_in - cash_out
        fin['cash'] += net_cash_change
        
        # Emergency Loan
        if fin['cash'] < 0:
            eloan = abs(fin['cash']) + 1000
            fin['notes_payable'] += eloan
            fin['cash'] = 1000
            
        # 5. UPDATE BS
        purchases = inp[14] + inp[15]
        fin['inventory_rx'] = (fin['inventory_rx'] + inp[14]) - (cogs * 0.7)
        fin['inventory_otc'] = (fin['inventory_otc'] + inp[15]) - (cogs * 0.3)
        fin['acct_receivable'] = (fin['acct_receivable'] * 0.10) + (total_sales * 0.70)
        fin['acct_payable'] = (fin['acct_payable'] - ap_payment) + purchases
        fin['retained_earnings'] += net_income
        
        # 6. REPORT
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
# 4. UI COMPONENTS (Full Version)
# ==========================================
with st.sidebar:
    st.title("💊 Communi-Pharm V37.9")
    st.caption("Full UI + Logic Fixed")
    role = st.selectbox("Select Role", ["Student", "Instructor"])
    
    if role == "Instructor":
        pwd = st.text_input("Admin Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("Admin Access Granted")
            if st.button("RUN SIMULATION PERIOD", type="primary"):
                run_simulation()
                st.rerun()
            if st.button("RESET GAME", type="secondary"):
                st.session_state.clear()
                st.rerun()
        else:
            st.warning("Enter password to access controls")

def render_student_view():
    st.header(f"🛒 Student Dashboard (Period {st.session_state.global_period})")
    
    # Store Selector
    team_ids = list(st.session_state.players.keys())
    selected_team = st.selectbox("Select Your Store", team_ids, format_func=lambda x: st.session_state.players[x]['shop_name'])
    player = st.session_state.players[selected_team]
    
    tab1, tab2 = st.tabs(["📝 Decisions (Inputs)", "📊 Financial Report"])
    
    with tab1:
        st.subheader(f"Input Decisions for {player['shop_name']}")
        
        # Form for Inputs
        with st.form("input_form"):
            # Using Data Editor for cleaner input list like before
            df_inp = pd.DataFrame({"Parameter": INPUT_LABELS, "Value": player['inputs']})
            edited_df = st.data_editor(df_inp, height=600, use_container_width=True, hide_index=True)
            
            submitted = st.form_submit_button("Save Decisions")
            if submitted:
                player['inputs'] = edited_df['Value'].tolist()
                player['status'] = 'Ready'
                st.success("Decisions Saved! Waiting for Instructor to Run.")

    with tab2:
        st.subheader("Performance Report")
        if player['history']:
            last_report = player['history'][-1]
            # Create metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Sales", f"${last_report['TOT SALES']:,.0f}")
            c2.metric("Net Worth", f"${last_report['Net Worth']:,.0f}")
            c3.metric("Cash Flow", f"${last_report['Cash Flow']:,.0f}")
            c4.metric("Loan (Debt)", f"${last_report['Loan']:,.0f}", delta_color="inverse")
            
            # Full Table
            df_hist = pd.DataFrame([last_report]).T
            st.dataframe(df_hist.style.format("{:,.2f}"), height=600)
        else:
            st.info("No reports available yet. Submit inputs and wait for simulation run.")

def render_instructor_view():
    st.header("👨‍🏫 Instructor Dashboard")
    st.write("Overview of all stores")
    
    # Consolidated Table
    data = []
    for pid, p in st.session_state.players.items():
        if p['history']:
            row = p['history'][-1]
            row['Store'] = p['shop_name']
            data.append(row)
            
    if data:
        df = pd.DataFrame(data).set_index('Store')
        # Select key columns for quick view
        cols = ["TOT SALES", "Net Worth", "Cash Flow", "Loan", "Rx GM%", "A/P Paid"]
        st.dataframe(df[cols].style.format("{:,.0f}"), use_container_width=True)
    else:
        st.info("No data simulated yet.")

# Main Router
if role == "Student":
    render_student_view()
elif role == "Instructor" and st.sidebar.text_input("Confirm Pwd", type="password", key="main_pwd") == ADMIN_PASSWORD:
    render_instructor_view()
