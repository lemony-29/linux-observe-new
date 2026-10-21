import json
import os
import time

import psutil

PIPE = "/run/observability/metrics_pipe" # directory url to the metric pipe stuff

# makes sure the pipe directory is a thing before anything else is done
def verify_dir():
    if not os.path.exists(PIPE):
        os.mkfifo(PIPE, 0o660)
    os.chmod(PIPE, 0o660)
    
# gets all the metric info then puts it into the pipe file
# this was headache-inducing, but i managed to get it working
def read_metrics(prev_net, prev_time):
    now = time.time()

    net = psutil.net_io_counters() # returns network stats and stuff (i.e. sent bytes)
    total = net.bytes_sent + net.bytes_recv # total bytes being sent and received
    elapsed = max(now - prev_time, 0.001) # time in between network updates
    net_rate = (total - prev_time) / elapsed # how many bytes are being transferred within updates

    data = {
        "time": now,
        "byte_data": net,
        "total_bytes": total,
        "delta": elapsed,
        "rate": net_rate,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "net_bytes_per_sec": round(net_rate, 1),
        "load_avg_1min": psutil.getloadavg()[0],
    }

    return data, total, now

def main():
    verify_dir()

    net = psutil.net_io_counters()
    prev_net = net.bytes_sent + net.bytes_recv
    prev_time = time.time()

    # constantly writes to the pipie file with updated info for the dashboard to see
    #TODO: try to figure out a better way of doing this
    while True:
        with open(PIPE, "w") as pipe:
            try:
                while True:
                    data, prev_time, prev_net = read_metrics(prev_net, prev_time)
                    pipe.write(json.dumps(data) + "\n") # dump the data to the file for the dashboard to read
                    pipe.flush()
            except BrokenPipeError:
                # the api might've restarted, so just do everything again
                continue


if __name__ == "__main__":
    main()