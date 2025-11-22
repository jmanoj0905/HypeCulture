# app.py — Streamlit
import streamlit as st
from db_connector import create_connection
from customer_view import show_customer_menu
from admin_seller_views import show_admin_menu, show_seller_menu

# ---------- DB utilities ----------
@st.cache_resource(show_spinner=False)
def get_connection():
    conn = create_connection()
    return conn

def do_register(connection, first_name, last_name, email, password):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Users (first_name, last_name, email, password_hash, user_role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (first_name, last_name, email, password, 'customer')
        )
        connection.commit()
        user_id = cursor.lastrowid
    return (user_id, 'customer', first_name)

def do_login(connection, email, password):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, user_role, first_name FROM Users WHERE email = %s AND password_hash = %s",
            (email, password)
        )
        row = cursor.fetchone()
    return row  # (user_id, user_role, first_name) or None

# ---------- UI ----------
st.set_page_config(page_title="HYPEculture", page_icon="👟", layout="wide")

st.markdown(
    """
    <div style="text-align:center">
      <h1>👟 HYPECULTURE</h1>
      <h4>Your Ultimate Shoe Marketplace</h4>
    </div>
    """,
    unsafe_allow_html=True
)

# Top bar: spacer + logout on the right when logged in
if "user" not in st.session_state:
    st.session_state.user = None
if st.session_state.user:
    spacer, right = st.columns([10, 2])
    with right:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

st.markdown("---")

connection = get_connection()
if not connection:
    st.error("Could not connect to the database. Please check your DB settings.")
    st.stop()

# Session init (auth mode)
st.session_state.setdefault("auth_mode", "Login")  # or "Register"

# Sidebar (status only; logout is top-right)
with st.sidebar:
    st.header("Account")
    if st.session_state.user:
        uid, role, name = st.session_state.user
        st.success(f"Signed in as **{name}** ({role})")
    else:
        st.info("You are not signed in.")
        st.session_state.auth_mode = st.radio(
            "Choose an action", ["Login", "Register"], index=0, horizontal=True
        )

# Auth panels
if not st.session_state.user:
    if st.session_state.auth_mode == "Register":
        st.subheader("Create your account")
        # ❌ removed enter_to_submit
        with st.form("register_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("First name")
            last_name = c2.text_input("Last name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Register")
        if submitted:
            if not (first_name and last_name and email and password):
                st.warning("Please fill out all fields.")
            else:
                try:
                    user = do_register(connection, first_name, last_name, email, password)
                    uid, role, name = user
                    role = (role or "").strip().lower()
                    st.session_state.user = (uid, role, name)
                    st.success("Registration successful! You're now logged in.")
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred during registration: {e}")
    else:
        st.subheader("Welcome back")
        # ❌ removed enter_to_submit
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            try:
                user = do_login(connection, email, password)
                if user:
                    uid, role, name = user
                    role = (role or "").strip().lower()
                    st.session_state.user = (uid, role, name)
                    st.success(f"Welcome back, {name}!")
                    st.rerun()
                else:
                    st.error("Login failed. Invalid email or password.")
            except Exception as e:
                st.error(f"An error occurred during login: {e}")

# Post-login routing
if st.session_state.user:
    user_id, role, name = st.session_state.user
    st.markdown(f"### Hi, {name}!")
    try:
        if role == 'customer':
            show_customer_menu(connection, user_id)   # shopping/browse page
        elif role == 'seller':
            show_seller_menu(connection, user_id)
        elif role == 'admin':
            show_admin_menu(connection)
        else:
            st.info(f"Unknown role '{role}'. Please contact support.")
    except Exception as e:
        st.warning(
            "A view raised an exception (this can happen if an old CLI view is still being used). "
            "Please ensure all views use Streamlit widgets (st.*) instead of input()/print()."
        )
        st.exception(e)

st.write("---")
st.caption("© HYPEculture")
