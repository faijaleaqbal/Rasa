---
name: cloud-backup-sync
description: Multi-device cloud sync, Rclone / GDrive / S3 sync automation, checksum-based incremental backups, and disaster recovery.
---

# Cloud Backup & Multi-Device Sync Skill

Automates continuous data backups, multi-device synchronization (Google Drive, S3, Nextcloud), and state snapshotting.

## Sync Patterns
* **Incremental Backup**: Sync modified files only using MD5/SHA256 checksums (`rclone sync` or `aws s3 sync`).
* **Database Snapshot**: Daily SQLite dumps with gzip compression (`storage/data.db.gz`).
* **Encrypted Archives**: Encrypt backup bundles before uploading to public cloud storage.
