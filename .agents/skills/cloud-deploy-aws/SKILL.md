---
name: cloud-deploy-aws
description: AWS Cloud deployment patterns, EC2 instance setup, Security Groups configuration, Elastic IP assignment, and S3 asset backup.
---

# AWS Cloud Deployment Skill

Procedures for orchestrating workloads on Amazon Web Services (AWS EC2, VPC, Security Groups, S3).

## EC2 Setup & Security Groups

### Required Inbound Port Rules:
| Port | Protocol | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `22` | TCP | SSH Administration | Admin IP / Bastion |
| `80` | TCP | HTTP (Nginx / Certbot) | `0.0.0.0/0` |
| `443` | TCP | HTTPS (SSL Web Traffic) | `0.0.0.0/0` |
| `5005` | TCP | Rasa REST Webhook API | App Clients / `0.0.0.0/0` |
| `5055` | TCP | Rasa Action Server | Internal / Localhost (`127.0.0.1`) |

## Elastic IP (EIP) Attachment
* Allocate an Elastic IP in the AWS VPC console and associate it with the EC2 instance to prevent IP changes upon reboot.

## S3 Backup Automation
Daily database backup sync to AWS S3:
```bash
aws s3 sync /home/ubuntu/agency-agents/storage/ s3://my-alya-backup-bucket/storage/ --exclude "*" --include "*.db"
```
