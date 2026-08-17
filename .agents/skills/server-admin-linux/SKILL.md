---
name: server-admin-linux
description: Linux system administration, systemd service units, process management (PM2/Tmux/Supervisor), firewall/UFW, SSL Certbot, and logs.
---

# Linux Server Administration Skill

Procedures for managing Linux cloud instances (Ubuntu/Debian), configuring background daemons, and troubleshooting system resources.

## Systemd Service Management

### Service Unit Template (`/etc/systemd/system/rasa.service`)
```ini
[Unit]
Description=Rasa Open Source Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agency-agents
ExecStart=/home/ubuntu/rasa-env/bin/rasa run --enable-api --cors "*" --port 5005
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Essential System Commands
```bash
# Reload daemon definitions
sudo systemctl daemon-reload

# Manage service lifecycle
sudo systemctl enable rasa.service
sudo systemctl start rasa.service
sudo systemctl status rasa.service
sudo systemctl restart rasa.service

# View live service logs
journalctl -u rasa.service -f -n 100
```

## System Monitoring & Triage
* `htop` / `top`: Monitor CPU and memory consumption.
* `df -h`: Check disk space usage.
* `netstat -tulnp` / `ss -tulnp`: Check listening network ports and binding addresses.
* `ufw status`: Check active firewall rules.
