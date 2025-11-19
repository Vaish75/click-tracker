# Animated live counter example in dashboard.py

import streamlit as st
import pandas as pd
import time
import firebase_admin
from firebase_admin import credentials, db

st.set_page_config(page_title="Live Click Dashboard", layout="wide")
st.title("📊 Real-Time Click Tracker")

# -------------------------
# Firebase init
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
# Fetch clicks
# -------------------------
@st.cache_data(ttl=5)
def fetch_clicks():
    data = ref.get()
    if not data:
        return pd.DataFrame(columns=["user", "timestamp"])
    rows = [{"user": v.get("user"), "timestamp": v.get("timestamp")} for k, v in data.items() if isinstance(v, dict)]
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")
    return df

df = fetch_clicks()

# -------------------------
# Animated Counter
# -------------------------
st.subheader("Live Click Counter")
counter_placeholder = st.empty()  # placeholder for animation

if df.empty:
    counter_placeholder.metric("Total Clicks", 0)
else:
    total_clicks = len(df)
    # Animate counter
    for i in range(total_clicks + 1):
        counter_placeholder.metric("Total Clicks", i)
        time.sleep(0.05)  # 50ms per increment for smooth animation
