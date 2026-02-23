import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

# Establish Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet):
    return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl=0)

def save_data(df, worksheet):
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet, data=df)
    st.cache_data.clear()

# --- CONSTANTS ---
CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA"]

# --- APP STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None})

# --- LOGIN LOGIC ---
if not st.session_state.logged_in:
    st.title("BeyondWalls Management System")
    users_df = load_data("users")
    
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user_row = users_df[(users_df['username'] == u) & (users_df['password'] == str(p))]
            if not user_row.empty:
                st.session_state.update({'logged_in': True, 'user': u, 'role': user_row.iloc[0]['role']})
                st.rerun()
            else:
                st.error("Invalid Username or Password")
else:
    # Sidebar Navigation
    st.sidebar.title(f"User: {st.session_state.user}")
    st.sidebar.write(f"Role: {st.session_state.role}")
    menu = ["My Tasks"]
    if st.session_state.role == 'Admin': menu.append("Admin Control")
    choice = st.sidebar.selectbox("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- USER: MY TASKS ---
    if choice == "My Tasks":
        st.header("Project Management")
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        
        my_projects = projects_df[projects_df['owner'] == st.session_state.user]
        
        if not my_projects.empty:
            sel_proj_name = st.selectbox("Select Project", my_projects['name'].tolist())
            sel_proj_id = my_projects[my_projects['name'] == sel_proj_name]['id'].iloc[0]

            st.divider()
            f1, f2 = st.columns(2)
            f_cat = f1.multiselect("Filter Category", CATEGORIES)
            f_stat = f2.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

            # Add Task (Pending Only)
            if f_stat == "Pending":
                with st.expander("➕ Add New Task"):
                    with st.form("new_task"):
                        cat = st.selectbox("Category", CATEGORIES)
                        sub_cat = st.selectbox("Report Type", REPORT_SUBS) if cat == "Report" else ""
                        desc = st.text_area("Task Description")
                        d_date = st.date_input("Deadline")
                        d_half = st.selectbox("Half", ["FH", "SH"])
                        if st.form_submit_button("Add Task"):
                            new_id = f"{cat[:3].upper()}-{len(tasks_df)+101}"
                            new_row = pd.DataFrame([{
                                "task_id": new_id, "project_id": sel_proj_id, "category": cat,
                                "sub_category": sub_cat, "description": desc, "deadline_date": str(d_date),
                                "deadline_half": d_half, "status": "Pending"
                            }])
                            tasks_df = pd.concat([tasks_df, new_row], ignore_index=True)
                            save_data(tasks_df, "tasks")
                            st.success(f"Task {new_id} added to Google Sheets!")
                            st.rerun()

            # View & Action
            st.subheader(f"{f_stat} Tasks")
            view_df = tasks_df[(tasks_df['project_id'] == sel_proj_id) & (tasks_df['status'] == f_stat)]
            if f_cat:
                view_df = view_df[view_df['category'].isin(f_cat)]
            
            if not view_df.empty:
                st.dataframe(view_df, use_container_width=True)
                sel_task_id = st.selectbox("Select Task ID:", view_df['task_id'].tolist())
                
                c1, c2 = st.columns(2)
                with c1:
                    if f_stat == "Pending":
                        if st.button("✅ Mark Completed"):
                            tasks_df.loc[tasks_df['task_id'] == sel_task_id, 'status'] = 'Completed'
                            save_data(tasks_df, "tasks")
                            st.rerun()
                    elif f_stat == "Completed":
                        if st.button("↩️ Re-open"):
                            tasks_df.loc[tasks_df['task_id'] == sel_task_id, 'status'] = 'Pending'
                            save_data(tasks_df, "tasks")
                            st.rerun()
                    elif f_stat == "Closed" and st.session_state.role == "Admin":
                        if st.button("🔓 Admin: Unlock Task"):
                            tasks_df.loc[tasks_df['task_id'] == sel_task_id, 'status'] = 'Pending'
                            save_data(tasks_df, "tasks")
                            st.rerun()
                
                with c2:
                    if f_stat != "Closed":
                        if st.button("📁 Move to Closed"):
                            tasks_df.loc[tasks_df['task_id'] == sel_task_id, 'status'] = 'Closed'
                            save_data(tasks_df, "tasks")
                            st.rerun()
            else: st.info(f"No {f_stat.lower()} tasks found.")
        else: st.warning("No projects assigned to you.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Management")
        t1, t2, t3 = st.tabs(["Users", "Projects", "Transfer"])
        
        users_df = load_data("users")
        projects_df = load_data("projects")

        with t1: # User Management
            with st.form("add_u"):
                nu, np, nr = st.text_input("Username"), st.text_input("Password"), st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create User"):
                    new_u = pd.DataFrame([{"username": nu, "password": np, "role": nr}])
                    save_data(pd.concat([users_df, new_u], ignore_index=True), "users")
                    st.rerun()
            
            st.divider()
            du = st.selectbox("Delete User", users_df['username'].tolist())
            if st.button("Delete User"):
                # Simplified delete for GSheets
                save_data(users_df[users_df['username'] != du], "users")
                st.rerun()

        with t2: # Project Management
            with st.form("add_p"):
                p_name = st.text_input("Project Name")
                p_owner = st.selectbox("Owner", users_df['username'].tolist())
                if st.form_submit_button("Create Project"):
                    new_p = pd.DataFrame([{"id": len(projects_df)+1, "name": p_name, "owner": p_owner}])
                    save_data(pd.concat([projects_df, new_p], ignore_index=True), "projects")
                    st.rerun()
            
            st.table(projects_df)

        with t3: # Transfer
            st.subheader("Manual Project Transfer")
            p_to_move = st.selectbox("Project", projects_df['name'].tolist())
            new_recipient = st.selectbox("New Owner", users_df['username'].tolist())
            if st.button("Transfer Now"):
                projects_df.loc[projects_df['name'] == p_to_move, 'owner'] = new_recipient
                save_data(projects_df, "projects")
                st.success("Transferred!")
