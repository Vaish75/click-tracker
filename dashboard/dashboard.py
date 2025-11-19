# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import firebase_admin
from firebase_admin import credentials, db

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Live Click Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Real-Time Click Tracker")
st.markdown("Track user clicks live with interactive charts and KPIs!")

# -------------------------
# Firebase init using Streamlit Secrets
# -------------------------
def init_firebase():
    if not firebase_admin._apps:
        sa_json = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(sa_json)
        firebase_admin.initialize_app(
            cred,
            {"databaseURL": st.secrets["firebase_service_account"]["firebase_database_url"]}
        )

init_firebase()
ref = db.reference("demo_clicks")

# -------------------------
# Fetch data
# -------------------------
@st.cache_data(ttl=5)
def fetch_clicks():
    data = ref.get()
    if not data:
        return pd.DataFrame(columns=["user", "timestamp"])

    rows = [
        {"user": v.get("user"), "timestamp": v.get("timestamp")}
        for _, v in data.items() if isinstance(v, dict)
    ]

    df = pd.DataFrame(rows)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")

    return df

df = fetch_clicks()

# -------------------------
# Sidebar controls
# -------------------------
refresh_seconds = st.sidebar.slider(
    "Auto-refresh every (sec)", min_value=2, max_value=30, value=5
)

pause = st.sidebar.checkbox("Pause auto-refresh", value=False)

# Auto-refresh mechanism (new Streamlit API)
if not pause:
    last = st.session_state.get("last_update", None)
    now = time.time()

    if last is None or (now - last) > refresh_seconds:
        st.session_state["last_update"] = now
        st.cache_data.clear()
        time.sleep(0.1)
        st.rerun()    # <--- UPDATED FIX

# -------------------------
# Dashboard layout
# -------------------------
if df.empty:
    st.warning("No clicks yet. Open the click page and press the button.")
else:
    df["Total_Clicks"] = range(1, len(df) + 1)

    total_clicks = len(df)
    unique_users = df["user"].nunique()
    top_user_clicks = df["user"].value_counts().max()

    # KPI Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Clicks", total_clicks)
    col2.metric("Unique Users", unique_users)
    col3.metric("Top User Clicks", top_user_clicks)

    st.markdown("---")

    # Filters
    users = df["user"].unique()
    selected_user = st.selectbox("Filter by User", options=["All Users"] + list(users))

    if selected_user != "All Users":
        df_filtered = df[df["user"] == selected_user]
    else:
        df_filtered = df.copy()

    # -------------------------
    # Line Chart
    # -------------------------
    fig_line = px.line(
        df_filtered,
        x="timestamp",
        y="Total_Clicks",
        title=f"Clicks Over Time ({selected_user})",
        markers=True,
        template="plotly_dark"
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # -------------------------
    # Top Users Bar Chart
    # -------------------------
    user_counts = df["user"].value_counts().reset_index()
    user_counts.columns = ["User", "Clicks"]
    top_users = user_counts.head(10).sort_values("Clicks", ascending=True)

    fig_bar = px.bar(
        top_users,
        x="Clicks",
        y="User",
        orientation="h",
        text="Clicks",
        title="Top 10 Users by Click Count",
        template="plotly_dark",
        color="Clicks",
        color_continuous_scale=px.colors.sequential.Plasma
    )
    fig_bar.update_traces(marker_line_color="black", marker_line_width=1.5, opacity=0.9)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Full Leaderboard
    st.subheader("Full User Leaderboard")
    st.dataframe(user_counts)

st.caption(f"Dashboard updates approximately every {refresh_seconds} seconds.")
