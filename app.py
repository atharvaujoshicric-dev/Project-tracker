import streamlit as st
import sqlite3
import pandas as pd

# --- DATABASE SETUP ---
def init_db():
    # v3 to ensure a clean slate and avoid column mismatch errors
    conn = sqlite3.connect('beyondwalls_v3.db') 
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (task_id TEXT PRIMARY KEY, project_id INTEGER, category TEXT, sub_category TEXT,
                  description TEXT, deadline_date DATE, deadline_half TEXT, status TEXT DEFAULT 'Pending')''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('beyondwalls_v3.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.fetchall() if fetch else None

# --- APP START ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")
init_db()

CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA"]

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
                
                sel_task_id = st.selectbox("Select Task ID:", df["ID"])
                c1, c2 = st.columns(2)
                with c1:
                    if f_stat == "Pending":
                        if st.button("✅ Mark Completed"):
                            run_query("UPDATE tasks SET status='Completed' WHERE task_id=?", (sel_task_id,))
                            st.rerun()
                        # Edit Expander
                        with st.expander(f"📝 Edit Task {sel_task_id}"):
                            curr = run_query("SELECT category, sub_category, description, deadline_date, deadline_half FROM tasks WHERE task_id=?", (sel_task_id,), fetch=True)[0]
                            with st.form(f"edit_{sel_task_id}"):
                                e_cat = st.selectbox("Cat", CATEGORIES, index=CATEGORIES.index(curr[0]))
                                e_sub = st.selectbox("Sub", REPORT_SUBS, index=REPORT_SUBS.index(curr[1]) if curr[1] in REPORT_SUBS else 0) if e_cat=="Report" else ""
                                e_desc = st.text_area("Desc", value=curr[2])
                                e_date = st.date_input("Date", value=pd.to_datetime(curr[3]))
                                e_half = st.selectbox("Half", ["FH", "SH"], index=0 if curr[4]=="FH" else 1)
                                if st.form_submit_button("Save Changes"):
                                    run_query("UPDATE tasks SET category=?, sub_category=?, description=?, deadline_date=?, deadline_half=? WHERE task_id=?", 
                                              (e_cat, e_sub, e_desc, e_date, e_half, sel_task_id))
                                    st.rerun()
                    elif f_stat == "Completed":
                        if st.button("↩️ Re-open to Pending"):
                            run_query("UPDATE tasks SET status='Pending' WHERE task_id=?", (sel_task_id,))
                            st.rerun()
                with c2:
                    if f_stat != "Closed":
                        if st.button("📁 Move to Closed"):
                            run_query("UPDATE tasks SET status='Closed' WHERE task_id=?", (sel_task_id,))
                            st.rerun()
                    else:
                        # User can only delete in Closed status, no re-open
                        if st.button("🗑️ Delete Permanently"):
                            run_query("DELETE FROM tasks WHERE task_id=?", (sel_task_id,))
                            st.error("Task Deleted Forever.")
                            st.rerun()
            else: st.info(f"No {f_stat.lower()} tasks.")
        else: st.warning("No projects assigned.")

    # --- ADMIN CONTROL ---
    elif choice == "Admin Control":
        # ... (Rest of the Admin logic remains the same as the previous full version)
