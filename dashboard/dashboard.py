# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import firebase_admin
from firebase_admin import credentials, db

st.set_page_config(page_title="Live Click Dashboard", layout="wide")
st.title("📊 Real-Time Click Tracker")

# -------------------------
# Firebase Admin init using Streamlit Secrets
# -------------------------
def init_firebase():
    if not firebase_admin._apps:
        sa_json = dict(st.secrets["firebase_service_account"])

        cred = credentials.Certificate(sa_json)

        firebase_admin.initialize_app(
            cred,
            {
                "databaseURL": st.secrets["firebase_service_account"]["firebase_database_url"]
            }
        )

init_firebase()
ref = db.reference("demo_clicks")

# -------------------------
# Helper to read data
# -------------------------
@st.cache_data(ttl=5)
def fetch_clicks():
    data = ref.get()
    if not data:
        return pd.DataFrame(columns=["user", "timestamp"])

    rows = []
    for k, v in data.items():
        if isinstance(v, dict):
            rows.append({
                "user": v.get("user"),
                "timestamp": v.get("timestamp")
            })

    df = pd.DataFrame(rows)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")

    return df

# -------------------------
# UI
# -------------------------
refresh_seconds = st.sidebar.slider(
    "Auto-refresh every (sec)", min_value=2, max_value=30, value=3
)

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.experimental_rerun()

    pause = st.checkbox("Pause auto-refresh", value=False)

with col2:
    st.markdown("Auto refresh keeps dashboard near real-time. Use 'Pause' to stop.")

# Auto-refresh
if not pause:
    last = st.session_state.get("last_update", None)
    now = time.time()

    if last is None or (now - last) > refresh_seconds:
        st.session_state["last_update"] = now
        st.cache_data.clear()
        time.sleep(0.2)
        st.experimental_rerun()

# -------------------------
# Display Data
# -------------------------
df = fetch_clicks()

if df.empty:
    st.warning("No clicks yet. Open the click page and press the button.")
else:
    df["Total_Clicks"] = range(1, len(df) + 1)

    fig = px.line(
        df,
        x="timestamp",
        y="Total_Clicks",
        title="Growing Click Count Over Time",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

    user_counts = df["user"].value_counts().reset_index()
    user_counts.columns = ["User", "Clicks"]

    st.subheader("Top Users")
    st.dataframe(user_counts.head(20))

    st.metric("Total Clicks", len(df))

st.caption(f"Dashboard updated every {refresh_seconds} seconds (approx).")
