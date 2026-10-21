# linux-observe-new
new repository and codebase for the COP3604 Project

to stop the agent:
sudo systemctl stop agent

to trigger an auto restart:
sudo systemctl kill agent

local device ip:
curl -4 ifconfig.me


test commands:

systemctl status stress --no-pager
systemctl is-enabled stress
journalctl -u stress -f

sudo ls -l /run/observability/
id observer
getent group observer
grep -E "^(User|Group)=" /etc/systemd/system/agent.service
ps -eo user,group,pid,cmd | grep -E "collect|uvicorn" | grep -v grep