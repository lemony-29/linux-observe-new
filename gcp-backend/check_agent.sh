#!/usr/bin/env bash
# /opt/observability/check_agent.sh

LOG=/var/log/observability_check.log
ts() { date '+%F %T'; }

for svc in collect agent; do
  if ! systemctl is-active --quiet "$svc"; then
    echo "$(ts) $svc not active - restarting" >> "$LOG"
    systemctl restart "$svc"
  fi
done

if ! curl -sf --max-time 3 http://localhost:8000/status | grep -q '"status":"ok"'; then
  echo "$(ts) status check failed - restarting collect and agent scripts" >> "$LOG"
  systemctl restart collector agent
fi