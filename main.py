# main script that handles the client-side of the dashboard
# the old repo was kinda messy, so i started in a newer one

import os
import sqlite3
import time
import pandas as pd
import requests
import streamlit as st
import altair as alt

from dotenv import load_dotenv, find_dotenv

# load the .env file stuff

env_path = find_dotenv()
load_dotenv(env_path, override=True) # this removes the cache (since i ran into an issue where the cache was preventing the network request)

SERVER_IS_CONNECTED = False
SERVER_URL = os.getenv("SERVER_IP") # self-explanatory
DB = "metrics.db" # the sql database name
# the sql database exists to store the server info persistently

st.title("Linux Infrastructure Observability Dashboard")

# returns the sql database thingy
# makes it easier to look-up and save stuff

def get_sqlbase():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS metrics (
        ts REAL PRIMARY KEY, cpu REAL, mem REAL, disk REAL, net REAL, load REAL)""")
    return conn

# this manages the sidebar control stuff (uses the sql base to load info from the past)
# the values are the amount of seconds to compare against

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

# manages the stress simulation manually

st.sidebar.subheader("Server Controls")

stress_kind = st.sidebar.selectbox("Stress class", ["cpu", "vm", "io", "hdd", "sock"])

# simulates stress for the given dropdown item

if st.sidebar.button("Stress"):
    try:
        requests.post(f"{SERVER_URL}/control/stress/{stress_kind}?seconds=30", timeout=3)
        st.toast("Beginning stress... (testing)")
    except requests.RequestException as e:
        st.toast(f"ERROR: {type(e).__name__}")

# crashes the agent service (to demonstrate auto restart)

if st.sidebar.button("Crash Agent (auto-restart test)"):
    try:
        r = requests.post(f"{SERVER_URL}/control/crash", timeout=3)
        st.toast(r.json()["status"])
    except requests.RequestException:
        pass
    st.toast("systemd should restart agent.service in a few seconds")

# a button to removes the old database with the old values 

if st.sidebar.button("Delete Database"):
    if os.path.exists(DB):
        os.remove(DB)
        st.toast("database has been removed")
    else:
        st.toast("database does not exist")

# colors the python text a certain way
# basically, this just helps visualize certain things

def text_color(text: str, color: str):
    color = color.lower()
    return f":{color}[{text}]"

# makes the charts (the original way i did it, didn't allow me to format the time the way i wanted to)
# i followed the docs for this: https://docs.streamlit.io/develop/api-reference/charts/st.altair_chart

def make_chart(df, column, label, usePercent=False):
    y_scale = alt.Scale(domain=[0, 100]) if usePercent else alt.Scale(zero=True)

    return (alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("time:T", title="Time",
                    axis=alt.Axis(format="%H:%M:%S", labelAngle=-45, tickCount=6)),

            y=alt.Y(f"{column}:Q", title=label, scale=y_scale),

            tooltip=[alt.Tooltip("time:T", title="Time", format="%H:%M:%S"),
                     alt.Tooltip(f"{column}:Q", title=label, format=".1f")],
        )
        .properties(height=350)
    )

# basically just a checker for the value stuff

def check_stat(name, value, max):
    if value > max:
        st.error(f"High {name} usage! ({value:.1f}% > {max}%)")

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

        st.write(f"{text_color("Connected", "green")} to Remote Server!")
        SERVER_IS_CONNECTED = True
    except (requests.RequestException, KeyError, ValueError) as e:
        SERVER_IS_CONNECTED = False
        st.write(f"{text_color("Disconnected", "red")} from Remote Server!")

        if isinstance(e, requests.exceptions.ConnectTimeout) or isinstance(e, requests.ConnectionError):
            st.error("Server is likely down or IP is not allowed")

        # st.info(f"INFO: {e}")

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
        st.info("Waiting for data..." if SERVER_IS_CONNECTED else "Server Not Connected...")
        return
    
    df["time"] = (
        pd.to_datetime(df["ts"], unit="s", utc=True)
        .dt.tz_convert("America/New_York")
        .dt.tz_localize(None)
    )

    df["net_kb"] = df["net"] / 1024

    latest = df.iloc[-1]

    # loads all the metric info into its proper graph
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CPU", f"{latest.cpu:.1f}%")
    c2.metric("Memory", f"{latest.mem:.1f}%")
    c3.metric("Disk", f"{latest.disk:.1f}%")
    c4.metric("Network", f"{latest.net / 1024:.1f} KB/s")
    c5.metric("Load (avg 1 min)", f"{latest.load:.2f}")

    # show alerts based on the metric info and if it exceeds the
    # number bars

    check_stat("CPU", latest.cpu, cpu_t)
    check_stat("memory", latest.mem, mem_t)
    check_stat("disk", latest.disk, disk_t)

    # load all the info into line charts

    tabs = st.tabs([
        "CPU", 
        "Memory", 
        "Disk", 
        "Network", 
        "Load (Processor Tasks)"
    ])

    charts = [
        ("cpu", "CPU (%)", True), 
        ("mem", "Memory (%)", True),
        ("disk", "Disk (%)", True), 
        ("net_kb", "Network (kb/s)", False),
        ("load", "Load (avg 1 min)", False)
    ]
    
    for tab, (col, label, pct) in zip(tabs, charts):
        with tab:
            st.altair_chart(make_chart(df, col, label, pct))

if __name__ == "__main__":
    main()