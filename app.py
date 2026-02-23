import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CACHED DATA LOADING ---
@st.cache_data(ttl=60)
def load_data(tab):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=tab, ttl=0)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        if "429" in str(e):
            st.error("Google Sheets Rate Limit reached. Please wait 30 seconds.")
        else:
            st.error(f"Error loading tab '{tab}': {e}")
        return pd.DataFrame()

def save_data(df, tab):
    df.columns = df.columns.str.strip().str.lower()
    conn.update(spreadsheet=SHEET_URL, worksheet=tab, data=df)
    st.cache_data.clear()

# --- CONSTANTS ---
CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report", "Others"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA", "Others"]

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("BeyondWalls Management System")
    users_df = load_data("users")
    with st.form("login"):
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            if not users_df.empty and 'username' in users_df.columns:
                user_match = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
                if not user_match.empty:
                    st.session_state.update({'logged_in': True, 'user': u, 'role': user_match.iloc[0]['role']})
                    st.rerun()
                else: st.error("Wrong credentials")
            else: st.error("User database error.")
else:
    st.sidebar.title(f"User: {st.session_state.user}")
    
    if st.sidebar.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    menu = ["My Tasks"]
    if st.session_state.role == 'Admin': menu.append("Admin Control")
    choice = st.sidebar.selectbox("Menu", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- USER: MY TASKS ---
    if choice == "My Tasks":
        st.header("Project Tasks")
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        
        if not projects_df.empty and 'owner' in projects_df.columns:
            my_projs = projects_df[projects_df['owner'] == st.session_state.user]
            
            if not my_projs.empty:
                sel_p_name = st.selectbox("Select Project", my_projs['name'].tolist())
                sel_p_id = my_projs[my_projs['name'] == sel_p_name]['id'].iloc[0]
                
                search_query = st.text_input("🔍 Search tasks", "").lower()
                f_stat = st.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

                # ADD TASK (Pending Only)
                if f_stat == "Pending":
                    with st.expander("➕ Add New Task"):
                        with st.form("new_t"):
                            cat = st.selectbox("Category", CATEGORIES)
                            # Sub-category only shows for Reports
                            sub = st.selectbox("Report Type", REPORT_SUBS) if cat == "Report" else ""
                            desc = st.text_area("Description")
                            d_date = st.date_input("Deadline Date", datetime.now())
                            d_priority = st.selectbox("Priority", ["FH", "SH"])
                            
                            if st.form_submit_button("Save Task"):
                                new_id = f"{cat[:3].upper()}-{len(tasks_df)+101}"
                                new_row = pd.DataFrame([{
                                    "task_id": new_id, "project_id": sel_p_id, "category": cat,
                                    "sub_category": sub, "description": desc, "status": "pending",
                                    "deadline_date": str(d_date), "deadline_half": d_priority
                                }])
                                save_data(pd.concat([tasks_df, new_row], ignore_index=True), "tasks")
                                st.rerun()

                # VIEW & SEARCH LOGIC
                if not tasks_df.empty and 'status' in tasks_df.columns:
                    view_df = tasks_df[(tasks_df['project_id'].astype(str) == str(sel_p_id)) & (tasks_df['status'].str.lower() == f_stat.lower())]
                    
                    if search_query:
                        view_df = view_df[view_df['description'].str.lower().str.contains(search_query) | view_df['task_id'].str.lower().str.contains(search_query)]
                    
                    st.dataframe(view_df, use_container_width=True)
                    
                    if not view_df.empty:
                        sel_tid = st.selectbox("Select Task ID", view_df['task_id'].tolist())
                        c1, c2 = st.columns(2)
                        with c1:
                            if f_stat == "Pending":
                                if st.button("✅ Mark Completed"):
                                    tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'completed'
                                    save_data(tasks_df, "tasks")
                                    st.rerun()
                                
                                with st.expander("📝 Edit Task"):
                                    curr = tasks_df[tasks_df['task_id'] == sel_tid].iloc[0]
                                    with st.form(f"edit_{sel_tid}"):
                                        e_desc = st.text_area("Edit Description", value=curr['description'])
                                        e_date = st.date_input("Edit Date", value=pd.to_datetime(curr['deadline_date']))
                                        e_half = st.selectbox("Edit Priority", ["FH", "SH"], index=0 if curr['deadline_half'] == "FH" else 1)
                                        if st.form_submit_button("Update"):
                                            tasks_df.loc[tasks_df['task_id'] == sel_tid, ['description', 'deadline_date', 'deadline_half']] = [e_desc, str(e_date), e_half]
                                            save_data(tasks_df, "tasks")
                                            st.rerun()
                            elif f_stat == "Completed" and st.button("↩️ Re-open"):
                                tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'pending'
                                save_data(tasks_df, "tasks")
                                st.rerun()
                            elif f_stat == "Closed" and st.session_state.role == "Admin" and st.button("🔓 Admin: Unlock"):
                                tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'pending'
                                save_data(tasks_df, "tasks")
                                st.rerun()
                        with c2:
                            if f_stat != "Closed" and st.button("📁 Move to Closed"):
                                tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'closed'
                                save_data(tasks_df, "tasks")
                                st.rerun()
                else: st.info("No tasks found.")
            else: st.warning("No projects assigned.")
        else: st.error("Database header error.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Management")
        t1, t2, t3 = st.tabs(["Manage Users", "Manage Projects", "Transfer"])
        users_df = load_data("users")
        projs_df = load_data("projects")

        with t1:
            with st.form("add_u"):
                nu, np, nr = st.text_input("New User"), st.text_input("Pass"), st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create User"):
                    if nu in users_df['username'].values: st.error("User exists!")
                    else:
                        save_data(pd.concat([users_df, pd.DataFrame([{"username": nu, "password": np, "role": nr}])]), "users")
                        st.rerun()
            du = st.selectbox("Delete User", users_df['username'].tolist() if not users_df.empty else [])
            if st.button("Confirm Delete"):
                save_data(users_df[users_df['username'] != du], "users")
                st.rerun()

        with t2:
            with st.form("add_p"):
                pn, po = st.text_input("Project Name"), st.selectbox("Owner", users_df['username'].tolist() if not users_df.empty else [])
                if st.form_submit_button("Create Project"):
                    new_id = int(projs_df['id'].max() + 1) if not projs_df.empty else 1
                    save_data(pd.concat([projs_df, pd.DataFrame([{"id": new_id, "name": pn, "owner": po}])]), "projects")
                    st.rerun()
            st.table(projs_df)

        with t3:
            p_move = st.selectbox("Project", projs_df['name'].tolist() if not projs_df.empty else [])
            new_o = st.selectbox("New Recipient", users_df['username'].tolist() if not users_df.empty else [])
            if st.button("Execute Transfer"):
                projs_df.loc[projs_df['name'] == p_move, 'owner'] = new_o
                save_data(projs_df, "projects")
                st.success("Transferred!")
                st.rerun()
