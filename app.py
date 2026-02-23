import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- GOOGLE SHEETS CONNECTION ---
# Replace this URL with your shared Google Sheet link
SQL_URL = "https://docs.google.com/spreadsheets/d/1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4/edit?usp=sharing"

st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")

# Establish connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet):
    return conn.read(spreadsheet=SQL_URL, worksheet=worksheet)

def update_data(df, worksheet):
    conn.update(spreadsheet=SQL_URL, worksheet=worksheet, data=df)

# --- INITIALIZE TABLES IF EMPTY ---
def init_gsheets():
    try:
        users_df = get_data("users")
    except:
        users_df = pd.DataFrame([{"username": "admin", "password": "admin123", "role": "Admin"}])
        update_data(users_df, "users")

    try:
        projects_df = get_data("projects")
    except:
        projects_df = pd.DataFrame(columns=["id", "name", "owner"])
        update_data(projects_df, "projects")

    try:
        tasks_df = get_data("tasks")
    except:
        tasks_df = pd.DataFrame(columns=["task_id", "project_id", "category", "sub_category", 
                                          "description", "deadline_date", "deadline_half", "status"])
        update_data(tasks_df, "tasks")

init_gsheets()
# --- APP START ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
init_db()

CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report", "Others"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA", "Others"]

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("BeyondWalls Management System")
    with st.form("login"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            res = run_query("SELECT role FROM users WHERE username=? AND password=?", (u, p), fetch=True)
            if res:
                st.session_state.update({'logged_in': True, 'user': u, 'role': res[0][0]})
                st.rerun()
            else: st.error("Invalid Credentials")
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
        my_projects = run_query("SELECT id, name FROM projects WHERE owner=?", (st.session_state.user,), fetch=True)
        
        if my_projects:
            proj_dict = {p[1]: p[0] for p in my_projects}
            sel_proj_name = st.selectbox("Select Project", list(proj_dict.keys()))
            sel_proj_id = proj_dict[sel_proj_name]

            st.divider()
            col_f1, col_f2 = st.columns(2)
            f_cat = col_f1.multiselect("Filter by Category", CATEGORIES)
            f_stat = col_f2.radio("View Status", ["Pending", "Completed", "Closed"], horizontal=True)

            # ADD TASK PANEL (Only for Pending)
            if f_stat == "Pending":
                with st.expander("➕ Add New Task"):
                    with st.form("new_task"):
                        cat = st.selectbox("Category", CATEGORIES)
                        sub_cat = st.selectbox("Report Type", REPORT_SUBS) if cat == "Report" else ""
                        desc = st.text_area("Task Description")
                        d_date = st.date_input("Deadline")
                        d_half = st.selectbox("Half", ["FH", "SH"])
                        if st.form_submit_button("Add Task"):
                            prefix = cat[:3].upper()
                            count = run_query("SELECT COUNT(*) FROM tasks", fetch=True)[0][0]
                            unique_id = f"{prefix}-{101 + count}"
                            run_query("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)", 
                                      (unique_id, sel_proj_id, cat, sub_cat, desc, d_date, d_half, "Pending"))
                            st.success(f"Task {unique_id} added!")
                            st.rerun()

            st.subheader(f"{f_stat} Tasks")
            query = "SELECT task_id, category, sub_category, description, deadline_date, deadline_half FROM tasks WHERE project_id=? AND status=?"
            params = [sel_proj_id, f_stat]
            if f_cat:
                query += f" AND category IN ({','.join(['?']*len(f_cat))})"
                params.extend(f_cat)
            
            tasks = run_query(query, tuple(params), fetch=True)
            if tasks:
                df = pd.DataFrame(tasks, columns=["ID", "Category", "Sub-Cat", "Description", "Deadline", "Half"])
                st.dataframe(df, use_container_width=True)
                
                # ACTION SECTION (Hidden for Closed)
                if f_stat != "Closed":
                    sel_task_id = st.selectbox("Select Task ID to take action:", df["ID"])
                    c1, c2 = st.columns(2)
                    with c1:
                        if f_stat == "Pending":
                            if st.button("✅ Mark Completed"):
                                run_query("UPDATE tasks SET status='Completed' WHERE task_id=?", (sel_task_id,))
                                st.rerun()
                            with st.expander(f"📝 Edit Task {sel_task_id}"):
                                curr = run_query("SELECT category, sub_category, description, deadline_date, deadline_half FROM tasks WHERE task_id=?", (sel_task_id,), fetch=True)[0]
                                with st.form(f"edit_{sel_task_id}"):
                                    e_cat = st.selectbox("Cat", CATEGORIES, index=CATEGORIES.index(curr[0]))
                                    e_sub = st.selectbox("Sub", REPORT_SUBS, index=REPORT_SUBS.index(curr[1]) if curr[1] in REPORT_SUBS else 0) if e_cat=="Report" else ""
                                    e_desc = st.text_area("Desc", value=curr[2])
                                    e_date = st.date_input("Date", value=pd.to_datetime(curr[3]))
                                    e_half = st.selectbox("Half", ["FH", "SH"], index=0 if curr[4]=="FH" else 1)
                                    if st.form_submit_button("Save"):
                                        run_query("UPDATE tasks SET category=?, sub_category=?, description=?, deadline_date=?, deadline_half=? WHERE task_id=?", 
                                                  (e_cat, e_sub, e_desc, e_date, e_half, sel_task_id))
                                        st.rerun()
                        elif f_stat == "Completed":
                            if st.button("↩️ Re-open to Pending"):
                                run_query("UPDATE tasks SET status='Pending' WHERE task_id=?", (sel_task_id,))
                                st.rerun()
                    with c2:
                        if st.button("📁 Move to Closed"):
                            run_query("UPDATE tasks SET status='Closed' WHERE task_id=?", (sel_task_id,))
                            st.warning("Task is now Archived and Locked.")
                            st.rerun()
                else:
                    st.info("Archive View: Closed tasks cannot be edited, re-opened, or deleted.")
            else: st.info(f"No {f_stat.lower()} tasks.")
        else: st.warning("No projects assigned.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Management Dashboard")
        t1, t2, t3 = st.tabs(["Manage Users", "Manage Projects", "Manual Transfer"])
        all_users = [u[0] for u in run_query("SELECT username FROM users", fetch=True)]

        with t1:
            st.subheader("Add User")
            with st.form("ad_u"):
                nu, np = st.text_input("Username"), st.text_input("Password", type="password")
                nr = st.selectbox("Role", ["User", "Admin"])
                if st.form_submit_button("Create"):
                    try: run_query("INSERT INTO users VALUES (?,?,?)", (nu, np, nr)); st.success("Created!"); st.rerun()
                    except: st.error("Exists")
            st.divider()
            du = st.selectbox("Delete User", all_users)
            user_projs = run_query("SELECT id FROM projects WHERE owner=?", (du,), fetch=True)
            if user_projs:
                successor = st.selectbox("Transfer projects to:", [u for u in all_users if u != du])
                if st.button("Transfer & Delete"):
                    run_query("UPDATE projects SET owner=? WHERE owner=?", (successor, du))
                    run_query("DELETE FROM users WHERE username=?", (du,))
                    st.rerun()
            else:
                if st.button("Confirm Delete"): run_query("DELETE FROM users WHERE username=?", (du,)); st.rerun()

        with t2:
            st.subheader("Create Project")
            with st.form("ad_p"):
                pn, po = st.text_input("Project Name"), st.selectbox("Assign to", all_users)
                if st.form_submit_button("Create"): run_query("INSERT INTO projects (name, owner) VALUES (?,?)", (pn, po)); st.rerun()
            st.divider()
            all_p = run_query("SELECT * FROM projects", fetch=True)
            if all_p:
                pdf = pd.DataFrame(all_p, columns=["ID", "Name", "Owner"])
                st.table(pdf)
                dp = st.selectbox("Delete Project ID", pdf["ID"])
                if st.button("Delete Project & Tasks"):
                    run_query("DELETE FROM projects WHERE id=?", (dp,))
                    run_query("DELETE FROM tasks WHERE project_id=?", (dp,))
                    st.rerun()

        with t3:
            st.subheader("Manual Transfer")
            all_p_data = run_query("SELECT id, name, owner FROM projects", fetch=True)
            if all_p_data:
                proj_list = [f"{p[0]} - {p[1]} (Owner: {p[2]})" for p in all_p_data]
                sel_p = st.selectbox("Project", proj_list)
                target = st.selectbox("Recipient", all_users)
                if st.button("Transfer"):
                    run_query("UPDATE projects SET owner=? WHERE id=?", (target, sel_p.split(" - ")[0]))
                    st.rerun()
