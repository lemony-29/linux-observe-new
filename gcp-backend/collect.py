# This utilizes the named pipes

import json
import os
import time

import psutil

PIPE = "/run/observability/metrics_pipe" # directory url to the metric pipe stuff

def verify_dir():
    if not os.path(PIPE):
        os.mkfifo(PIPE)

def main():
    verify_dir()

if __name__ == "__main__":
    main()