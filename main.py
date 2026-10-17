import time
import streamlit as st
import pandas as pd
import requests

import os
from dotenv import load_dotenv

load_dotenv() # load the stuff in the .env file 
# (because i don't want to expose the server ip and the repo is public)

SERVER_IP = os.getenv("SERVER_IP")

# initialize data to hold dashboard info
if "old" not in st.session_state:
    st.session_state.old = []

# returns the metrics data reported from the server
def get_metrics():
    return_data = None

    try:
        r = requests.get(f"{SERVER_IP}/metrics", timout=5)
        r.raise_for_status()

        return_data = { 
            "time": time.time(), # idk if i'll actually need this, but i'll attach it 
            # basically just stores the time the fetch was successful
            "status": r.status_code,
            "info": { **r.json() } # unpack all the returned json data
        }
    except requests.exceptions.RequestException as e:
        st.error(f"FAILED TO GET GCP DATA: {e}")

    return return_data

def main():
    st.title("Test page title")

    data = get_metrics()
    if data == None:
        return
    
    return

if __name__ == "__main__":
    main()