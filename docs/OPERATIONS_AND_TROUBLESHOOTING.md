# Operations & Troubleshooting Guide

This guide provides operational procedures, incident response instructions, and diagnostic commands for system administrators managing the **YouTube Video Scheduling & Automation Platform**.

---

## 1. System Health & Container Monitoring

### Inspect Running Containers
```bash
cd /opt/ytvideosautomation
docker compose ps
```

### Inspect Container Logs
```bash
# Real-time backend application logs
docker compose logs -f backend

# Real-time worker upload activity
docker compose logs -f backend | grep -E "(WorkerPool|uploader|scheduler_engine)"

# Nginx host access & error logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 2. YouTube API Quotas & Limits

### Understanding Quota Costs
Each standard YouTube video upload consumes **1,600 units** of the default **10,000 daily project units** allotted by Google Cloud.
- Max daily uploads per GCP project: **6 videos/day** ($6 \times 1600 = 9600$ units).
- Thumbnail updates consume **50 units**.
- Metadata edits consume **50 units**.

### Quota Exceeded Alerts (`QUOTA_EXCEEDED`)
- The system automatically blocks subsequent scheduled uploads if the remaining quota cannot safely cover the 1,600 unit cost.
- **Remediation**:
  1. Quotas reset automatically every day at midnight Pacific Time (00:00 PST / 08:00 UTC).
  2. To increase quota, apply for a free quota extension in the Google Cloud Console:
     - Navigate to `APIs & Services` $\rightarrow$ `YouTube Data API v3` $\rightarrow$ `Quotas` $\rightarrow$ `Request Quota Increase`.

---

## 3. Crash Recovery & Orphan File Cleanup

### Automatic Startup Reconciliation
On server reboots or container restarts, the `ReconciliationService` automatically runs in the FastAPI lifespan to:
1. Identify any jobs stuck in `IN_PROGRESS` or `DOWNLOADING`.
2. Safely unlink orphaned temporary files in `/app/temp/`.
3. Reset occurrence statuses back to `QUEUED`.

### Manual Reconciliation Trigger
If a pipeline job gets stalled due to network drops:
```bash
# Via API:
curl -X POST http://localhost:8000/api/v1/uploads/reconcile
```
Or click the **"Run Crash Reconciliation"** button directly on the `/logs` page of the Web UI.

---

## 4. Backups, Database Recovery & Maintenance

### Run On-Demand Backup
```bash
sudo bash /opt/ytvideosautomation/deploy/backup.sh
```
Archives are securely stored in `/opt/yt_backups/`.

### Restore Database from Backup
```bash
# 1. Stop backend container
cd /opt/ytvideosautomation
docker compose stop backend

# 2. Extract database file into volume
tar -xzf /opt/yt_backups/yt_backup_YYYYMMDD_HHMMSS.tar.gz -C /tmp/
docker run --rm -v yt_automation_data:/target -v /tmp/backup_YYYYMMDD_HHMMSS/data:/source alpine cp -r /source/. /target/

# 3. Restart backend
docker compose start backend
```

---

## 5. Security & Fail2ban Jails

### Check Banned IPs
```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status nginx-http-auth
sudo fail2ban-client status nginx-limit-req
```

### Unban a Legitimate IP Address
```bash
sudo fail2ban-client set sshd unbanip 198.51.100.42
```
