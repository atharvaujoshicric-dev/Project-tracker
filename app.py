import streamlit as st
import pandas as pd

# --- CONFIG ---
st.set_page_config(page_title="BeyondWalls Workflow", layout="wide")

# This link converts your Google Sheet into a CSV that the app can read easily.
SHEET_ID = "1fUGPRxOWmew4p1iTuVQ3tUBZ2dtSb2NX1EZ2rVWKDM4"
def get_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

# Tab IDs (GIDs) - These are found at the end of the URL when you click each tab in your browser.
# Update these if they don't match your tabs.
GIDS = {
    "users": "0",          
    "projects": "1520633333", 
    "tasks": "563385732"      
}

def load_data(tab_name):
    url = get_url(GIDS[tab_name])
    try:
        return pd.read_csv(url)
    except:
        st.error(f"Cannot read '{tab_name}' tab. Ensure Sheet is public (Anyone with link can View).")
        return pd.DataFrame()

# --- CONSTANTS ---
CATEGORIES = ["Design", "Copy", "Video", "PPC", "Web Dev", "Report"]
REPORT_SUBS = ["Weekly report", "PPC report", "CP aggregation report", "Pre-Sales report", "TVA"]

# --- APP STATE ---
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
            if not users_df.empty:
                # Ensure password comparison works whether it's a number or text
                user_match = users_df[(users_df['username'] == u) & (users_df['password'].astype(str) == str(p))]
                if not user_match.empty:
                    st.session_state.update({'logged_in': True, 'user': u, 'role': user_match.iloc[0]['role']})
                    st.rerun()
                else: st.error("Wrong Username or Password")
            else: st.error("No user data found in Google Sheet.")
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
        
        # Only show projects assigned to you
        my_projects = projects_df[projects_df['owner'] == st.session_state.user]
        
        if not my_projects.empty:
            sel_proj_name = st.selectbox("Select Project", my_projects['name'].tolist())
            sel_proj_id = my_projects[my_projects['name'] == sel_proj_name]['id'].iloc[0]

            st.divider()
            col1, col2 = st.columns(2)
            f_cat = col1.multiselect("Filter Category", CATEGORIES)
            f_stat = col2.radio("Status", ["Pending", "Completed", "Closed"], horizontal=True)

            # Display Tasks
            if not tasks_df.empty:
                view_df = tasks_df[(tasks_df['project_id'] == sel_proj_id) & (tasks_df['status'] == f_stat)]
                if f_cat: view_df = view_df[view_df['category'].isin(f_cat)]
                
                if not view_df.empty:
                    st.dataframe(view_df, use_container_width=True)
                    
                    # Edit & Move buttons are disabled because public links are "Read-Only"
                    st.info("ℹ️ To add or edit tasks, please update the Google Sheet directly. Public links do not allow writing data from the app.")
                else: st.info(f"No {f_stat.lower()} tasks found.")
        else: st.warning("No projects assigned. Contact Admin.")

    # --- ADMIN VIEW ---
    elif choice == "Admin Control":
        st.header("Admin Control Panel")
        st.info("You are an Admin. View all projects below.")
        projects_df = load_data("projects")
        st.table(projects_df)
