import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")

# Your Base Sheet ID from the URL you provided
SHEET_ID = "1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4"

# Function to generate the export URL for different tabs
def get_csv_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

# Map your GIDs (You can find these at the end of the URL when you click each tab)
# Default 'Sheet1' is usually gid=0. Please update these if your GIDs are different.
GIDS = {
    "users": "0",          # Replace with GID for 'users' tab
    "projects": "1520633333", # Replace with GID for 'projects' tab
    "tasks": "563385732"      # Replace with GID for 'tasks' tab
}

def load_data(worksheet_name):
    url = get_csv_url(GIDS[worksheet_name])
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error loading {worksheet_name}. Check if GID is correct and Sheet is Public.")
        return pd.DataFrame()

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
    
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if not users_df.empty:
                user_row = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
                if not user_row.empty:
                    st.session_state.update({'logged_in': True, 'user': u, 'role': user_row.iloc[0]['role']})
                    st.rerun()
                else: st.error("Invalid Username/Password")
            else: st.error("User database is empty or inaccessible.")
else:
    # Sidebar
    st.sidebar.title(f"Hello, {st.session_state.user}")
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

            # View Tasks
            st.subheader(f"{f_stat} Tasks")
            if not tasks_df.empty:
                view_df = tasks_df[(tasks_df['project_id'] == sel_proj_id) & (tasks_df['status'] == f_stat)]
                if f_cat: view_df = view_df[view_df['category'].isin(f_cat)]
                
                if not view_df.empty:
                    st.dataframe(view_df, use_container_width=True)
                else: st.info("No tasks found.")
            
            # Note for Writing Data
            st.info("💡 Note: Public links are 'Read-Only'. To save new tasks, you must update the Google Sheet directly or use a Service Account.")
