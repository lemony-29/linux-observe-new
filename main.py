# main script that handles the client-side of the dashboard
# the old repo was kinda messy, so i started in a newer one

import os
import sqlite3
import time
import pandas as pd
import requests
import streamlit as st

from dotenv import load_dotenv, find_dotenv

# load the .env file stuff

env_path = find_dotenv()
load_dotenv(env_path, override=True) # this removes the cache (since i ran into an issue where the cache was preventing the network request)

SERVER_URL = os.getenv("SERVER_IP") # self-explanatory
DB = "metrics.db" # the sql database name
# the sql database exists to store the server info persistently

# st.set_page_config(page_title="Observability Dashboard", layout="wide")

st.title("Linux Infrastructure Observability Dashboard")

# returns the sql database thingy

def get_sqlbase():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS metrics (
        ts REAL PRIMARY KEY, cpu REAL, mem REAL, disk REAL, net REAL, load REAL)""")
    return conn

# this manages the sidebar control stuff (uses the sql base to load info from the past)

st.sidebar.header("Historic")
windows = {
    "Last 30 seconds": 30, 
    "Last 5 minutes": 300,
    "Last hour": 3600, 
    "Last 24 hours": 86400
}

window = windows[st.sidebar.selectbox("Time window", list(windows), index=1)]

# this manages the thresholds for an alert to show

st.sidebar.subheader("Alert thresholds")
cpu_t = st.sidebar.slider("CPU (%)", 0, 100, 80)
mem_t = st.sidebar.slider("Memory (%)", 0, 100, 80)
disk_t = st.sidebar.slider("Disk (%)", 0, 100, 90)

# the main function thats ran every 5 seconds

@st.fragment(run_every=5)
def main():
    try:
        # this calls the gcp web worker for the metrics info
        # if it failed for whatever reason, then an error is called
        # otherwise, it converts the data to json and loads the returned info

        r = requests.get(f"{SERVER_URL}/metrics", timeout=3)
        r.raise_for_status()
        m = r.json()

        conn = get_sqlbase()
        conn.execute(
            "INSERT OR IGNORE INTO metrics VALUES (?,?,?,?,?,?)",
            (
                m["time"], 
                m["cpu_percent"], 
                m["memory_percent"],
                m["disk_percent"], 
                m["net_bytes_per_sec"], 
                m["load_avg_1min"]
            )
        )

        conn.commit()
        conn.close()
    except (requests.RequestException, KeyError, ValueError) as e:
        st.error("Server is either down or something broke (check below)")
        st.info(f"INFO: {e}")

    # gets the data from whatever is chosen from the sidebar

    conn = get_sqlbase()
    df = pd.read_sql_query(
        "SELECT * FROM metrics WHERE ts > ? ORDER BY ts",
        conn, 
        params=(time.time() - window,)
    )

    conn.close()

    # nothing has been returned yet

    if df.empty:
        st.info("Waiting for data...")
        return
    
    df["Time"] = pd.to_datetime(df["ts"], unit="s") # converts the current time to something readable

    latest = df.iloc[-1]

    # loads all the metric info into its proper graph
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CPU", f"{latest.cpu:.1f}%")
    c2.metric("Memory", f"{latest.mem:.1f}%")
    c3.metric("Disk", f"{latest.disk:.1f}%")
    c4.metric("Network", f"{latest.net / 1024:.1f} KB/s")
    c5.metric("Load (1 min)", f"{latest.load:.2f}")

    # show alerts based on the metric info and if it exceeds the
    # number bars

    if latest.cpu > cpu_t:
        st.error(f"High CPU usage! ({latest.cpu:.1f}% > {cpu_t}%)")
    if latest.mem > mem_t:
        st.error(f"High memory usage! ({latest.mem:.1f}% > {mem_t}%)")
    if latest.disk > disk_t:
        st.error(f"High disk usage! ({latest.disk:.1f}% > {disk_t}%)")

    # load all the info into line charts

    tabs = st.tabs(["CPU", "Memory", "Disk", "Network", "Load"])

    for tab, col in zip(tabs, ["CPU Usage", "Memory Usage", "Disk Usage", "Network", "Processor Load"]):
        with tab:
            st.line_chart(df, x="Time", y=col)

if __name__ == "__main__":
    main()