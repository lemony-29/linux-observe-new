import json
import threading
import time
import os
import signal
import subprocess

from fastapi import FastAPI, HTTPException

app = FastAPI()

PIPE = "/run/observability/metrics_pipe"

latest = {}
latest_update = 0

# stress options since i forgot to add the button
stress_proc = None

STRESS_OPTIONS = { # arguments sent (what the artificial stress should be)
    "cpu":  ["--cpu", "0"],
    "vm":   ["--vm", "1", "--vm-bytes", "50%"],
    "io":   ["--io", "2"],
    "hdd":  ["--hdd", "1", "--hdd-bytes", "256M"],
    "sock": ["--sock", "2"],
}


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

# begin the stress process
# this sets the stress on a given class for the provided amount of seconds, basically
@app.post("/control/stress/{kind}")
def start_stress(kind: str, seconds: int = 30):
    global stress_proc
    if kind not in STRESS_OPTIONS:
        raise HTTPException(status_code=400, detail="unknown stress class")
    
    if stress_proc and stress_proc.poll() is None:
        return {"status": "already running"}
    
    seconds = max(5, min(seconds, 120))
    stress_proc = subprocess.Popen( # executes the stress-ng command
        ["stress-ng", *STRESS_OPTIONS[kind], "--timeout", f"{seconds}s"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return {"status": "started", "class": kind, "seconds": seconds}

# kill the process
@app.post("/control/crash")
def crash():
    threading.Timer(0.5, lambda: os.kill(os.getpid(), signal.SIGKILL)).start()

    return {"status": "crashing in 0.5s"}