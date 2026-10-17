## THIS IS NOT RAN WITH main.py FOR THE CLIENT-SIDE
## THIS IS THE PYTHON AGENT SCRIPT IN THE GCP

from fastapi import FastAPI
import psutil

app = FastAPI()

@app.get("/metrics")
def metrics():
    return {

    }