import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. TIMEZONE SETUP ---
IST = pytz.timezone('Asia/Kolkata')

def get_ist_time():
    return datetime.now(IST).strftime("%I:%M:%S %p")

# --- 2. SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'last_sync' not in st.session_state:
    st.session_state['last_sync'] = "Never"

# --- 3. CONFIG & CONNECTION ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. CACHED DATA LOADING ---
@st.cache_data(ttl=60)
def load_data(tab):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=tab, ttl=0)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        if "429" in str(e):
            st.error("Google Sheets is busy. Wait 15 seconds and Refresh.")
        return pd.DataFrame()

def save_data(df, tab):
    df.columns = df.columns.str.strip().str.lower()
    conn.update(spreadsheet=SHEET_URL, worksheet=tab, data=df)
    st.cache_data.clear()
    st.session_state['last_sync'] = get_ist_time()

# --- 5. LOGIN LOGIC ---
if not st.session_state['logged_in']:
    st.title("BeyondWalls Management System")
    users_df = load_data("users")
    with st.form("login"):
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            if not users_df.empty and 'username' in users_df.columns:
                user_match = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
                if not user_match.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = u
                    st.session_state['role'] = user_match.iloc[0]['role']
                    st.session_state['last_sync'] = get_ist_time()
                    st.rerun()
                else: st.error("Wrong credentials")
            else: st.error("User database error.")
else:
    # --- 6. SIDEBAR ---
    st.sidebar.title(f"User: {st.session_state['user']}")
    st.sidebar.info(f"Last Data Sync: {st.session_state['last_sync']} (IST)")
    
    if st.sidebar.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.session_state['last_sync'] = get_ist_time()
        st.rerun()

    menu = ["My Tasks"]
    if st.session_state['role'] == 'Admin': menu.append("Admin Control")
    choice = st.sidebar.selectbox("Menu", menu)
    
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- 7. USER: MY TASKS ---
    if choice == "My Tasks":
        st.header("Project Tasks")
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        
        if not projects_df.empty and 'owner' in projects_df.columns:
            my_projs = projects_df[projects_df['owner'] == st.session_state['user']]
            
            if not my_projs.empty:
                sel_p_name = st.selectbox("Select Project", my_projs['name'].tolist())
                sel_p_id = my_projs[my_projs['name'] == sel_p_name]['id'].iloc[0]
                
                search_query = st.text_input("🔍 Search tasks", "").lower()
                f_stat = st.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

                if f_stat == "Pending":
                    # --- ADD TASK FORM ---
                    with st.expander("➕ Add New Task", expanded=False):
                        with st.form("new_t", clear_on_submit=True):
                            CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report", "Others"]
                            SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA", "Others"]
                            cat = st.selectbox("Category", CATEGORIES)
                            sub = st.selectbox("Report Type", SUBS) if cat == "Report" else ""
                            desc = st.text_area("Description")
                            d_date = st.date_input("Deadline Date", datetime.now(IST))
                            d_priority = st.selectbox("Priority", ["FH", "SH"])
                            
                            if st.form_submit_button("Save Task"):
                                tasks_latest = load_data("tasks")
                                new_id = f"{cat[:3].upper()}-{len(tasks_latest)+101}"
                                new_row = pd.DataFrame([{
                                    "task_id": new_id, "project_id": sel_p_id, "category": cat,
                                    "sub_category": sub, "description": desc, "status": "pending",
                                    "deadline_date": d_date.strftime("%d/%m/%Y"), "deadline_half": d_priority
                                }])
                                save_data(pd.concat([tasks_latest, new_row], ignore_index=True), "tasks")
                                # st.rerun() resets everything and closes the expander
                                st.rerun()

                if not tasks_df.empty and 'status' in tasks_df.columns:
                    view_df = tasks_df[(tasks_df['project_id'].astype(str) == str(sel_p_id)) & (tasks_df['status'].str.lower() == f_stat.lower())].copy()
                    if search_query:
                        view_df = view_df[view_df['description'].astype(str).str.lower().str.contains(search_query)]
                    
                    st.dataframe(view_df, use_container_width=True)
                    
                    if not view_df.empty:
                        sel_tid = st.selectbox("Select Task ID to Action", ["Select ID"] + view_df['task_id'].tolist())
                        
                        if sel_tid != "Select ID":
                            c1, c2 = st.columns(2)
                            with c1:
                                if f_stat == "Pending":
                                    if st.button("✅ Mark Completed"):
                                        tasks_latest = load_data("tasks")
                                        tasks_latest.loc[tasks_latest['task_id'] == sel_tid, 'status'] = 'completed'
                                        save_data(tasks_latest, "tasks")
                                        st.rerun()
                                    
                                    # --- EDIT TASK FORM ---
                                    with st.expander("📝 Edit Task Details"):
                                        curr = view_df[view_df['task_id'] == sel_tid].iloc[0]
                                        try: v_date = datetime.strptime(str(curr['deadline_date']), "%d/%m/%Y")
                                        except: v_date = datetime.now(IST)
                                        
                                        with st.form(f"edit_{sel_tid}", clear_on_submit=True):
                                            e_desc = st.text_area("Description", value=str(curr['description']))
                                            e_date = st.date_input("Date", value=v_date)
                                            e_half = st.selectbox("Priority", ["FH", "SH"], index=0 if str(curr['deadline_half']) == "FH" else 1)
                                            if st.form_submit_button("Update & Close"):
                                                tasks_latest = load_data("tasks")
                                                tasks_latest.loc[tasks_latest['task_id'] == sel_tid, ['description', 'deadline_date', 'deadline_half']] = [e_desc, e_date.strftime("%d/%m/%Y"), e_half]
                                                save_data(tasks_latest, "tasks")
                                                st.rerun()
                                                
                                elif f_stat == "Completed" and st.button("↩️ Re-open"):
                                    tasks_latest = load_data("tasks")
                                    tasks_latest.loc[tasks_latest['task_id'] == sel_tid, 'status'] = 'pending'
                                    save_data(tasks_latest, "tasks")
                                    st.rerun()
                            with c2:
                                if f_stat != "Closed" and st.button("📁 Move to Closed"):
                                    tasks_latest = load_data("tasks")
                                    tasks_latest.loc[tasks_latest['task_id'] == sel_tid, 'status'] = 'closed'
                                    save_data(tasks_latest, "tasks")
                                    st.rerun()
                else: st.info("No tasks found.")

    # --- 8. ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Management")
        t1, t2, t3 = st.tabs(["Users", "Projects", "Transfer"])
        users_df, projs_df = load_data("users"), load_data("projects")

        with t1:
            with st.form("add_u", clear_on_submit=True):
                nu, np, nr = st.text_input("New User"), st.text_input("Pass"), st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create User"):
                    save_data(pd.concat([users_df, pd.DataFrame([{"username": nu, "password": np, "role": nr}])]), "users")
                    st.rerun()
        with t2:
            with st.form("add_p", clear_on_submit=True):
                pn, po = st.text_input("Project Name"), st.selectbox("Owner", users_df['username'].tolist() if not users_df.empty else [])
                if st.form_submit_button("Create Project"):
                    new_id = int(projs_df['id'].max() + 1) if not projs_df.empty else 1
                    save_data(pd.concat([projs_df, pd.DataFrame([{"id": new_id, "name": pn, "owner": po}])]), "projects")
                    st.rerun()
            st.table(projs_df)
        with t3:
            p_move = st.selectbox("Project", projs_df['name'].tolist() if not projs_df.empty else [])
            new_o = st.selectbox("New Owner", users_df['username'].tolist() if not users_df.empty else [])
            if st.button("Transfer"):
                projs_df.loc[projs_df['name'] == p_move, 'owner'] = new_o
                save_data(projs_df, "projects")
                st.rerun()
