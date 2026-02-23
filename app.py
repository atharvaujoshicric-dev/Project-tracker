import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")

SHEET_ID = "1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4"

# Use the 'gviz' API for better stability than the standard export link
def get_url(sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

def load_data(tab_name):
    url = get_url(tab_name)
    try:
        df = pd.read_csv(url)
        # Clean column names (removes hidden spaces)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

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
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if not users_df.empty and 'username' in users_df.columns:
                user_match = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
                if not user_match.empty:
                    st.session_state.update({'logged_in': True, 'user': u, 'role': user_match.iloc[0]['role']})
                    st.rerun()
                else: st.error("Wrong Username or Password")
            else: st.error("The 'users' tab is empty or headers are missing.")
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
        st.header("Your Project Tasks")
        projects_df = load_data("projects")
        tasks_df = load_data("tasks")
        
        # Check if projects_df is empty or missing 'owner' column
        if not projects_df.empty and 'owner' in projects_df.columns:
            my_projects = projects_df[projects_df['owner'] == st.session_state.user]
            
            if not my_projects.empty:
                sel_proj_name = st.selectbox("Select Project", my_projects['name'].tolist())
                sel_proj_id = my_projects[my_projects['name'] == sel_proj_name]['id'].iloc[0]

                st.divider()
                f_stat = st.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

                if not tasks_df.empty and 'status' in tasks_df.columns:
                    view_df = tasks_df[(tasks_df['project_id'] == sel_proj_id) & (tasks_df['status'] == f_stat)]
                    st.dataframe(view_df, use_container_width=True)
                else:
                    st.info("The 'tasks' tab is currently empty.")
            else:
                st.warning("No projects are assigned to your username in the Google Sheet.")
        else:
            st.error("Projects data could not be loaded. Please check your Google Sheet headers.")

    # --- ADMIN VIEW ---
    elif choice == "Admin Control":
        st.header("Admin Control Panel")
        projects_df = load_data("projects")
        if not projects_df.empty:
            st.subheader("All Active Projects")
            st.table(projects_df)
        else:
            st.info("No projects found in the Google Sheet.")
