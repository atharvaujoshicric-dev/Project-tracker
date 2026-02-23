import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

# Establish Connection using the Secrets you added in Step 2
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(tab):
    return conn.read(spreadsheet=SHEET_URL, worksheet=tab, ttl=0)

def save_data(df, tab):
    conn.update(spreadsheet=SHEET_URL, worksheet=tab, data=df)
    st.cache_data.clear()

# --- CONSTANTS ---
CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA"]

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("BeyondWalls Management System")
    users_df = load_data("users")
    with st.form("login"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user_match = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
            if not user_match.empty:
                st.session_state.update({'logged_in': True, 'user': u, 'role': user_match.iloc[0]['role']})
                st.rerun()
            else: st.error("Wrong credentials")
else:
    st.sidebar.title(f"User: {st.session_state.user}")
    menu = ["My Tasks"]
    if st.session_state.role == 'Admin': menu.append("Admin Control")
    choice = st.sidebar.selectbox("Menu", menu)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- USER: MY TASKS ---
    if choice == "My Tasks":
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        my_projs = projects_df[projects_df['owner'] == st.session_state.user]
        
        if not my_projs.empty:
            sel_p_name = st.selectbox("Project", my_projs['name'].tolist())
            sel_p_id = my_projs[my_projs['name'] == sel_p_name]['id'].iloc[0]
            
            f_stat = st.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

            # ADD TASK (Pending Only)
            if f_stat == "Pending":
                with st.expander("➕ Add Task"):
                    with st.form("new_t"):
                        cat = st.selectbox("Category", CATEGORIES)
                        sub = st.selectbox("Type", REPORT_SUBS) if cat == "Report" else ""
                        desc = st.text_area("Description")
                        if st.form_submit_button("Save Task"):
                            new_t = pd.DataFrame([{"task_id": f"{cat[:3]}-{len(tasks_df)+101}", "project_id": sel_p_id, "category": cat, "sub_category": sub, "description": desc, "status": "Pending"}])
                            save_data(pd.concat([tasks_df, new_t], ignore_index=True), "tasks")
                            st.rerun()

            view_df = tasks_df[(tasks_df['project_id'] == sel_p_id) & (tasks_df['status'] == f_stat)]
            st.dataframe(view_df)
            
            if not view_df.empty:
                sel_tid = st.selectbox("Select Task ID", view_df['task_id'].tolist())
                if f_stat == "Pending" and st.button("✅ Mark Done"):
                    tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'Completed'
                    save_data(tasks_df, "tasks")
                    st.rerun()
                elif f_stat == "Completed" and st.button("📁 Move to Closed"):
                    tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'Closed'
                    save_data(tasks_df, "tasks")
                    st.rerun()

    # --- ADMIN CONTROL (RETORED) ---
    elif choice == "Admin Control":
        st.header("Admin Dashboard")
        t1, t2, t3 = st.tabs(["Manage Users", "Manage Projects", "Transfer"])
        
        users_df = load_data("users")
        projs_df = load_data("projects")

        with t1: # Users
            with st.form("add_u"):
                nu, np, nr = st.text_input("New User"), st.text_input("Pass"), st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create"):
                    save_data(pd.concat([users_df, pd.DataFrame([{"username": nu, "password": np, "role": nr}])]), "users")
                    st.rerun()
        
        with t2: # Projects
            with st.form("add_p"):
                pn, po = st.text_input("Project Name"), st.selectbox("Owner", users_df['username'].tolist())
                if st.form_submit_button("Create Project"):
                    save_data(pd.concat([projs_df, pd.DataFrame([{"id": len(projs_df)+1, "name": pn, "owner": po}])]), "projects")
                    st.rerun()
            st.table(projs_df)

        with t3: # Transfer
            p_move = st.selectbox("Project", projs_df['name'].tolist())
            new_o = st.selectbox("New Owner", users_df['username'].tolist())
            if st.button("Transfer"):
                projs_df.loc[projs_df['name'] == p_move, 'owner'] = new_o
                save_data(projs_df, "projects")
                st.rerun()
