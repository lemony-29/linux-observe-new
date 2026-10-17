from fastapi import FastAPI
import psutil

app = FastAPI()

@app.get("/metrics")
def metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "net_bytes_sent": psutil.net_io_counters().bytes_sent,
        "load_avg_1min": psutil.getloadavg()[0],
    }