---
name: docker-deploy
description: Instructions and best practices for building, optimizing, and orchestrating Docker containers and Nginx reverse proxy configurations.
---

# Docker & Deployment Skill

Procedures for containerization, production deployments, reverse proxy routing, and service health management.

## Key Services in Architecture
1. **Rasa Core / NLU Server**: Port `5005`
2. **Rasa Action Server**: Port `5055`
3. **Nginx Reverse Proxy**: Port `80` / `443` (manages SSL termination & path routing)
4. **Web Frontend / Dashboard**: Next.js / React / Static assets

## Container Best Practices
* Use lightweight base images (e.g. `python:3.10-slim`, `node:20-alpine`).
* Employ multi-stage builds to minimize final image footprint.
* Never bake secret `.env` files into Docker images; mount them via Docker runtime or secrets manager.
* Implement non-root user execution inside containers for security.

## Nginx Reverse Proxy Configuration
* Reference: `nginx_rasa.conf`
* Direct `/socket.io` or `/webhooks/` traffic to the Rasa backend (`http://localhost:5005`).
* Forward `/webhook` for actions to the action server (`http://localhost:5055`).
* Enable Gzip / Brotli compression and cache headers for static assets.

## Deployment Verification
```bash
# Test Nginx syntax
sudo nginx -t

# Reload Nginx without downtime
sudo systemctl reload nginx

# Check service status
curl -i http://localhost:5005/status
```
