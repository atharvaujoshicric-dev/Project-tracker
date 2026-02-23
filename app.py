import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(tab):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=tab, ttl=0)
        # Fix: Strip spaces and lowercase headers to prevent KeyErrors
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Error loading tab '{tab}': {e}")
        return pd.DataFrame()

def save_data(df, tab):
    # Ensure headers are clean before saving back to Google Sheets
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
            else: st.error("User database not found or empty.")
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
        st.header("Project Tasks")
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        
        if not projects_df.empty and 'owner' in projects_df.columns:
            my_projs = projects_df[projects_df['owner'] == st.session_state.user]
            
            if not my_projs.empty:
                sel_p_name = st.selectbox("Select Project", my_projs['name'].tolist())
                sel_p_id = my_projs[my_projs['name'] == sel_p_name]['id'].iloc[0]
                
                f_stat = st.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

                # ADD TASK (Pending Only)
                if f_stat == "Pending":
                    with st.expander("➕ Add New Task"):
                        with st.form("new_t"):
                            cat = st.selectbox("Category", CATEGORIES)
                            sub = st.selectbox("Report Type", REPORT_SUBS) if cat == "Report" else ""
                            desc = st.text_area("Description")
                            if st.form_submit_button("Save Task"):
                                new_id = f"{cat[:3].upper()}-{len(tasks_df)+101}"
                                new_row = pd.DataFrame([{
                                    "task_id": new_id, "project_id": sel_p_id, "category": cat,
                                    "sub_category": sub, "description": desc, "status": "pending"
                                }])
                                save_data(pd.concat([tasks_df, new_row], ignore_index=True), "tasks")
                                st.success("Task Saved!")
                                st.rerun()

                # VIEW TASKS
                if not tasks_df.empty and 'status' in tasks_df.columns:
                    # Filter and match lowercase status
                    view_df = tasks_df[(tasks_df['project_id'].astype(str) == str(sel_p_id)) & (tasks_df['status'].str.lower() == f_stat.lower())]
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
                            elif f_stat == "Completed":
                                if st.button("↩️ Re-open"):
                                    tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'pending'
                                    save_data(tasks_df, "tasks")
                                    st.rerun()
                        with c2:
                            if f_stat != "Closed":
                                if st.button("📁 Move to Closed"):
                                    tasks_df.loc[tasks_df['task_id'] == sel_tid, 'status'] = 'closed'
                                    save_data(tasks_df, "tasks")
                                    st.rerun()
                else: st.info("No tasks found.")
            else: st.warning("No projects assigned to you.")
        else: st.error("Project database error. Check headers.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Management")
        t1, t2, t3 = st.tabs(["Manage Users", "Manage Projects", "Transfer"])
        
        users_df = load_data("users")
        projs_df = load_data("projects")

        with t1: # USERS
            with st.form("add_u"):
                nu = st.text_input("New User").strip()
                np = st.text_input("Pass").strip()
                nr = st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create User"):
                    if nu in users_df['username'].values:
                        st.error("User already exists!")
                    else:
                        new_u = pd.DataFrame([{"username": nu, "password": np, "role": nr}])
                        save_data(pd.concat([users_df, new_u], ignore_index=True), "users")
                        st.rerun()
            st.divider()
            du = st.selectbox("Delete User", users_df['username'].tolist() if not users_df.empty else [])
            if st.button("Confirm Delete User"):
                save_data(users_df[users_df['username'] != du], "users")
                st.rerun()

        with t2: # PROJECTS
            with st.form("add_p"):
                pn = st.text_input("Project Name").strip()
                po = st.selectbox("Owner", users_df['username'].tolist() if not users_df.empty else [])
                if st.form_submit_button("Create Project"):
                    new_id = int(projs_df['id'].max() + 1) if not projs_df.empty else 1
                    new_p = pd.DataFrame([{"id": new_id, "name": pn, "owner": po}])
                    save_data(pd.concat([projs_df, new_p], ignore_index=True), "projects")
                    st.rerun()
            st.table(projs_df)

        with t3: # TRANSFER
            st.subheader("Manual Transfer")
            p_to_move = st.selectbox("Project", projs_df['name'].tolist() if not projs_df.empty else [])
            new_owner = st.selectbox("New Recipient", users_df['username'].tolist() if not users_df.empty else [])
            if st.button("Execute Transfer"):
                projs_df.loc[projs_df['name'] == p_to_move, 'owner'] = new_owner
                save_data(projs_df, "projects")
                st.success("Transferred!")
                st.rerun()
