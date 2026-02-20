import streamlit as st
import sqlite3
import pandas as pd

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('beyondwalls_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (task_id TEXT PRIMARY KEY, project_id INTEGER, category TEXT, 
                  description TEXT, deadline_date DATE, deadline_half TEXT, status TEXT DEFAULT 'Pending')''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('beyondwalls_pro.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.fetchall() if fetch else None

# --- APP START ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
init_db()

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
    st.sidebar.title(f"Logged in: {st.session_state.user}")
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
            f_cat = col_f1.multiselect("Filter by Category", ["Design", "Copy", "Video", "PPC", "Web Dev"])
            f_stat = col_f2.radio("View Status", ["Pending", "Completed"], horizontal=True)

            # ONLY show Add Task Panel if "Pending" is selected
            if f_stat == "Pending":
                with st.expander("➕ Add New Task"):
                    with st.form("new_task"):
                        cat = st.selectbox("Category", ["Design", "Copy", "Video", "PPC", "Web Dev"])
                        desc = st.text_area("Task Description")
                        d_date = st.date_input("Deadline")
                        d_half = st.selectbox("Half", ["FH", "SH"])
                        if st.form_submit_button("Add Task"):
                            prefix = cat[:3].upper()
                            count = run_query("SELECT COUNT(*) FROM tasks", fetch=True)[0][0]
                            unique_id = f"{prefix}-{101 + count}"
                            run_query("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)", 
                                      (unique_id, sel_proj_id, cat, desc, d_date, d_half, "Pending"))
                            st.success(f"Task {unique_id} added!")
                            st.rerun()

            # Display Tasks
            st.subheader(f"{f_stat} Tasks for {sel_proj_name}")
            query = "SELECT task_id, category, description, deadline_date, deadline_half FROM tasks WHERE project_id=? AND status=?"
            params = [sel_proj_id, f_stat]
            if f_cat:
                query += f" AND category IN ({','.join(['?']*len(f_cat))})"
                params.extend(f_cat)
            
            tasks = run_query(query, tuple(params), fetch=True)
            if tasks:
                df = pd.DataFrame(tasks, columns=["ID", "Category", "Task", "Deadline", "Half"])
                st.dataframe(df, use_container_width=True)
                
                sel_task = st.selectbox("Select Task ID to take action:", df["ID"])
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if f_stat == "Pending":
                        if st.button("✅ Mark as Complete"):
                            run_query("UPDATE tasks SET status='Completed' WHERE task_id=?", (sel_task,))
                            st.rerun()
                    else:
                        if st.button("↩️ Re-open Task"):
                            run_query("UPDATE tasks SET status='Pending' WHERE task_id=?", (sel_task,))
                            st.rerun()
                
                with btn_col2:
                    if st.button("❌ Close Permanently (Delete)"):
                        run_query("DELETE FROM tasks WHERE task_id=?", (sel_task,))
                        st.error(f"Task {sel_task} has been deleted forever.")
                        st.rerun()
            else: st.info(f"No {f_stat.lower()} tasks found.")
        else: st.warning("No projects assigned to you.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        st.header("Admin Dashboard")
        t1, t2, t3 = st.tabs(["Manage Users", "Manage Projects", "Transfer Projects"])
        
        with t1: # Manage Users
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Add User")
                nu, np = st.text_input("New Username"), st.text_input("New Password", type="password")
                nr = st.selectbox("Role", ["User", "Admin"])
                if st.button("Create"):
                    try: run_query("INSERT INTO users VALUES (?,?,?)", (nu, np, nr)); st.success("Created!")
                    except: st.error("Exists!")
            with col2:
                st.subheader("Delete User")
                du = st.selectbox("Select User to Remove", [u[0] for u in run_query("SELECT username FROM users", fetch=True)])
                if st.button("Confirm Delete User"):
                    run_query("DELETE FROM users WHERE username=?", (du,))
                    st.rerun()

        with t2: # Manage Projects
            st.subheader("Create New Project")
            pn = st.text_input("Project Name")
            po = st.selectbox("Initial Owner", [u[0] for u in run_query("SELECT username FROM users", fetch=True)])
            if st.button("Create Project"):
                run_query("INSERT INTO projects (name, owner) VALUES (?,?)", (pn, po))
                st.success("Project Created!")
            
            st.divider()
            st.subheader("All Active Projects")
            all_p = run_query("SELECT * FROM projects", fetch=True)
            if all_p:
                pdf = pd.DataFrame(all_p, columns=["ID", "Name", "Owner"])
                st.table(pdf)
                dp = st.selectbox("Delete Project ID Permanently", pdf["ID"])
                if st.button("Delete Project & All Its Tasks"):
                    run_query("DELETE FROM projects WHERE id=?", (dp,))
                    run_query("DELETE FROM tasks WHERE project_id=?", (dp,))
                    st.rerun()

        with t3: # Transfer Projects (ADMIN ONLY)
            st.subheader("Transfer Project Ownership")
            all_p_data = run_query("SELECT id, name, owner FROM projects", fetch=True)
            if all_p_data:
                proj_list = [f"{p[0]} - {p[1]} (Current: {p[2]})" for p in all_p_data]
                selected_p_str = st.selectbox("Select Project to Transfer", proj_list)
                selected_p_id = selected_p_str.split(" - ")[0]
                
                new_owner = st.selectbox("Transfer to New User", [u[0] for u in run_query("SELECT username FROM users", fetch=True)])
                
                if st.button("Confirm Transfer"):
                    run_query("UPDATE projects SET owner=? WHERE id=?", (new_owner, selected_p_id))
                    st.success(f"Project ID {selected_p_id} transferred to {new_owner}")
                    st.rerun()
            else: st.info("No projects available to transfer.")
