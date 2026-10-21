#!/usr/bin/env bash
CLASSES=(cpu vm io hdd sock)

systemd-notify --ready

while true; do
  for class in "${CLASSES[@]}"; do                  # i mostly followed a bash tutorial for these (and for the stress-ng stuff)
    case $class in
      cpu)  args=(--cpu 0) ;;                       
      vm)   args=(--vm 1 --vm-bytes 50%) ;;         
      io)   args=(--io 2) ;;
      hdd)  args=(--hdd 1 --hdd-bytes 256M) ;;
      sock) args=(--sock 2) ;;
    esac

    duration=$(( (RANDOM % 31) + 20 ))              # should be a random duration between 20 - 50 seconds
    echo "START $class for ${duration}s"
    stress-ng "${args[@]}" --timeout "${duration}s" &
    pid=$!

    while kill -0 "$pid" 2>/dev/null; do
      systemd-notify WATCHDOG=1
      sleep 5
    done

    wait "$pid"
    echo "END $class"

    for _ in 1 2 3 4 5 6; do
      systemd-notify WATCHDOG=1
      sleep 5
    done
  done
done