import json
import threading
import time
import os

from fastapi import FastAPI

app = FastAPI()

PIPE = "/run/observability/metrics_pipe"

latest = {}
latest_update = 0

# the default errors didn't really fit what i
# was looking for, so i ended up making my own
class NoDataError(Exception):
    pass

# reads the info in the metric_pipe pipe 
def read_pipe_data():
    global latest, latest_update
    # this is a loop that runs immediately after the collect.py file
    # finishes writing to the pipe
    while True:
        if not os.path.exists(PIPE): # quick bug fix since it errored sometimes
            os.mkfifo(PIPE, 0o660)

        with open(PIPE, "r") as pipe:
            for line in pipe:
                try:
                    latest = json.loads(line)
                    latest_update = time.time()
                except json.JSONDecodeError:
                    continue # something went wrong with this line (somehow)

# runs when the app starts
#TODO: replace this with the lifespan stuff
@app.on_event("startup")
def init_read():
    threading.Thread(target=read_pipe_data, daemon=True).start()

# returns the actual metrics info back to the dashboard
@app.get("/metrics")
def metrics():
    if not latest:
        raise NoDataError("Metrics info hasn't been loaded and cached yet!")
    return latest

# used by the cron job to see whether the service needs to restart or not
@app.get("/status")
def agent_status():
    age = time.time() - latest_update if latest_update else None
    return {"status": "ok" if age is not None and age < 5 else "stale", "data_age_sec": age}