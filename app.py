import streamlit as st
import sqlite3
import pandas as pd

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('beyondwalls_projects.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    # Added 'status' column to projects table
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                  owner TEXT, deadline_date DATE, deadline_half TEXT, status TEXT DEFAULT 'Pending')''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    conn.close()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('beyondwalls_projects.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetch: return c.fetchall()

# --- APP START ---
st.set_page_config(page_title="BeyondWalls Tracker", layout="wide")
init_db()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in, st.session_state.user, st.session_state.role = False, None, None

if not st.session_state.logged_in:
    st.title("BeyondWalls Project Portal")
    with st.form("login"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            res = run_query("SELECT role FROM users WHERE username=? AND password=?", (u, p), fetch=True)
            if res:
                st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u, res[0][0]
                st.rerun()
            else: st.error("Invalid Login")
else:
    st.sidebar.title(f"User: {st.session_state.user}")
    menu = ["My Projects", "Add Project"]
    if st.session_state.role == 'Admin': menu.append("Admin Panel")
    choice = st.sidebar.selectbox("Go to", menu)
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADD PROJECT ---
    if choice == "Add Project":
        st.header("New Project Assignment")
        with st.form("add_p"):
            name = st.text_input("Project Name")
            date = st.date_input("Deadline Date")
            half = st.selectbox("Deadline Half", ["FH", "SH"])
            if st.form_submit_button("Assign to Me"):
                run_query("INSERT INTO projects (name, owner, deadline_date, deadline_half) VALUES (?,?,?,?)", (name, st.session_state.user, date, half))
                st.success(f"Project '{name}' added!")

    # --- MY PROJECTS ---
    elif choice == "My Projects":
        st.header("Project Management")
        
        # Filter for Completion Status
        status_filter = st.radio("View Status:", ["Pending", "Completed"], horizontal=True)
        
        data = run_query("SELECT id, name, deadline_date, deadline_half FROM projects WHERE owner=? AND status=?", (st.session_state.user, status_filter), fetch=True)
        df = pd.DataFrame(data, columns=["ID", "Project", "Deadline", "Half"])
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("Action")
                target = st.selectbox("Select Project", df["Project"])
                if status_filter == "Pending":
                    if st.button("✅ Mark as Completed"):
                        run_query("UPDATE projects SET status='Completed' WHERE name=? AND owner=?", (target, st.session_state.user))
                        st.balloons()
                        st.rerun()
                else:
                    if st.button("↩️ Re-open Task"):
                        run_query("UPDATE projects SET status='Pending' WHERE name=? AND owner=?", (target, st.session_state.user))
                        st.rerun()

            with c2:
                st.subheader("Transfer")
                users = [u[0] for u in run_query("SELECT username FROM users WHERE username != ?", (st.session_state.user,), fetch=True)]
                to_u = st.selectbox("Transfer to", users)
                if st.button("Transfer Project"):
                    run_query("UPDATE projects SET owner=? WHERE name=? AND owner=?", (to_u, target, st.session_state.user))
                    st.warning("Transferred!")
                    st.rerun()

            with c3:
                st.subheader("Delete")
                if st.button("🗑️ Delete Project"):
                    run_query("DELETE FROM projects WHERE name=? AND owner=?", (target, st.session_state.user))
                    st.error("Deleted.")
                    st.rerun()
        else:
            st.info(f"No {status_filter.lower()} projects found.")

    # --- ADMIN ---
    elif choice == "Admin Panel":
        st.header("Admin Controls")
        # Same Admin Logic as before...
        st.write("Manage Users and Global Projects here.")
        # [Existing admin logic would go here]
