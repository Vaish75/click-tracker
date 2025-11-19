# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import json
import time
import os
import firebase_admin
from firebase_admin import credentials, db

st.set_page_config(page_title="Live Click Dashboard", layout="wide")
st.title("📊 Real-Time Click Tracker")

# -------------------------
# Firebase Admin init from Streamlit secrets or local file
# -------------------------
def init_firebase():
    if firebase_admin._apps:
        return

    # Try to load service account from Streamlit secrets (recommended on cloud)
    if "firebase_service_account" in st.secrets:
        # st.secrets["firebase_service_account"] should be a JSON object (not a string)
        sa_json = st.secrets["firebase_service_account"]
        # write to a temporary file and initialize
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as f:
            json.dump(sa_json, f)
            key_path = f.name
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": st.secrets.get("firebase_database_url")
        })
        # optional: remove temp file
        try:
            os.remove(key_path)
        except OSError:
            pass
    else:
        # Local dev fallback — looks for a file at secrets/firebase_key.json
        local_path = "secrets/firebase_key.json"
        if os.path.exists(local_path):
            cred = credentials.Certificate(local_path)
            firebase_admin.initialize_app(cred, {
                "databaseURL": os.environ.get("FIREBASE_DB_URL")
            })
        else:
            st.error("Firebase credentials not found. Add them to Streamlit secrets (recommended) or place file at 'secrets/firebase_key.json' locally.")
            st.stop()

init_firebase()
ref = db.reference("demo_clicks")

# -------------------------
# Helper to read data
# -------------------------
@st.cache_data(ttl=5)  # cache for a few seconds to reduce reads
def fetch_clicks():
    data = ref.get()
    if not data:
        return pd.DataFrame(columns=["user", "timestamp"])
    rows = []
    for k,v in data.items():
        if isinstance(v, dict):
            rows.append({"user": v.get("user"), "timestamp": v.get("timestamp")})
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        # assume timestamp is millis
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values("timestamp")
    return df

# -------------------------
# UI
# -------------------------
refresh_seconds = st.sidebar.slider("Auto-refresh every (sec)", min_value=2, max_value=30, value=3)

placeholder = st.empty()

# Manual controls
col1, col2 = st.columns([1,3])
with col1:
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.experimental_rerun()
    pause = st.checkbox("Pause auto-refresh", value=False)
with col2:
    st.markdown("Auto refresh keeps dashboard near real-time. Use 'Pause' to stop.")

# Auto-refresh mechanism (simple)
if not pause:
    # set up automatic rerun using session state - sleep then rerun
    last = st.session_state.get("last_update", None)
    now = time.time()
    if last is None or (now - last) > refresh_seconds:
        st.session_state["last_update"] = now
        st.cache_data.clear()
        # small delay to avoid tight loop on new deploy
        time.sleep(0.2)
        st.experimental_rerun()

# Fetch and show
df = fetch_clicks()
if df.empty:
    st.warning("No clicks yet. Open the click page and press the button.")
else:
    # Total clicks over time
    df["Total_Clicks"] = range(1, len(df)+1)
    fig = px.line(df, x="timestamp", y="Total_Clicks", title="Growing Click Count Over Time", markers=True, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # Top users
    user_counts = df['user'].value_counts().reset_index()
    user_counts.columns = ['User', 'Clicks']
    st.subheader("Top Users")
    st.dataframe(user_counts.head(20))

    # Live counter
    st.metric("Total Clicks", len(df))

st.caption("Dashboard updated every {} seconds (approx).".format(refresh_seconds))
