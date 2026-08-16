# Ubuntu VPS Production Deployment & Hardening Guide

A complete, step-by-step guide to provisioning, deploying, and securing the **YouTube Video Scheduling & Automation Platform** on an Ubuntu Linux VPS (Hetzner, DigitalOcean, Linode, AWS EC2, Vultr, etc.).

---

## 🖥️ System Requirements

- **Operating System**: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS (x86_64 or ARM64)
- **CPU**: 1 vCPU minimum (2 vCPU recommended for video upload streams)
- **RAM**: 2 GB RAM minimum (1 GB swap recommended)
- **Disk**: 20 GB SSD minimum (more if storing local video library files)
- **Network**: Static public IPv4 address

---

## ⚡ Quick Start: 1-Click Automated Setup

SSH into your freshly provisioned Ubuntu VPS as `root`:

```bash
# 1. Clone repository
git clone https://github.com/your-username/ytvideosautomation.git /opt/ytvideosautomation
cd /opt/ytvideosautomation

# 2. Run the automated VPS installer & hardening script
sudo bash deploy/setup-vps.sh
```

The script automatically:
1. Updates all system packages.
2. Installs Docker Engine, Docker Compose plugin, Nginx, Certbot, UFW, and Fail2ban.
3. Configures UFW firewall (permitting only ports 22 SSH, 80 HTTP, 443 HTTPS).
4. Sets up Fail2ban brute-force protection.
5. Generates a hardened `.env` file with random cryptographic keys.
6. Configures a systemd service (`ytvideosautomation.service`) for automatic restart on VPS boot.
7. Builds and launches the container stack.

---

## 🔑 Configure Environment & Google OAuth Credentials

Edit the `.env` configuration file:

```bash
nano /opt/ytvideosautomation/.env
```

Ensure the following variables are set:

```ini
ENVIRONMENT=production
SECRET_KEY=your_random_64_char_secret_key
ENCRYPTION_KEY=your_fernet_key

# Google Drive OAuth (from Google Cloud Console)
GOOGLE_DRIVE_CLIENT_ID=your_id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your_secret
GOOGLE_DRIVE_REDIRECT_URI=https://yourdomain.com/api/v1/drive/oauth/callback

# YouTube Data API OAuth (from Google Cloud Console)
YOUTUBE_CLIENT_ID=your_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_secret
YOUTUBE_REDIRECT_URI=https://yourdomain.com/api/v1/youtube/oauth/callback

# CORS Allowed Origins
CORS_ORIGINS=["https://yourdomain.com", "http://yourdomain.com"]
```

After modifying `.env`, restart the containers:

```bash
cd /opt/ytvideosautomation
docker compose restart
```

---

## 🔒 Domain & SSL Setup (Certbot & Nginx)

### 1. Configure DNS
Point your domain's DNS `A` record to your VPS IP address (e.g. `automation.yourdomain.com` $\rightarrow$ `192.0.2.1`).

### 2. Configure Host Nginx
Copy the pre-configured Nginx reverse proxy template:

```bash
cp /opt/ytvideosautomation/deploy/nginx/yt-automation.conf /etc/nginx/sites-available/yt-automation.conf

# Replace YOUR_DOMAIN_OR_IP with your actual domain
sed -i 's/YOUR_DOMAIN_OR_IP/automation.yourdomain.com/g' /etc/nginx/sites-available/yt-automation.conf

# Enable site
ln -s /etc/nginx/sites-available/yt-automation.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test configuration
nginx -t
```

### 3. Obtain Free Let's Encrypt SSL Certificate

```bash
certbot --nginx -d automation.yourdomain.com
```

Certbot will automatically install the certificate, configure HTTP/2, and enable auto-renewal via systemd timers.

---

## 🛡️ Security & Hardening Checklist

1. **Firewall (UFW)**:
   ```bash
   ufw status verbose
   ```
   *Expected: Only ports 22, 80, 443 are active.*

2. **Intrusion Prevention (Fail2ban)**:
   ```bash
   fail2ban-client status
   fail2ban-client status sshd
   ```

3. **File Permissions**:
   ```bash
   chmod 600 /opt/ytvideosautomation/.env
   chown -R root:root /opt/ytvideosautomation
   ```

4. **Non-Root Container Execution**:
   *The backend Docker container automatically runs as `appuser` (UID 1000).*

---

## 💾 Automated Database & Credential Backups

Add a daily automated backup cron job:

```bash
chmod +x /opt/ytvideosautomation/deploy/backup.sh

# Open crontab
crontab -e
```

Add the following line to run daily backups at 03:00 AM:

```cron
0 3 * * * /bin/bash /opt/ytvideosautomation/deploy/backup.sh >> /var/log/yt_backup.log 2>&1
```

Backups are compressed, secured with `chmod 600`, and stored in `/opt/yt_backups/` with a 14-day retention cycle.

---

## 🛠️ Maintenance & Useful Commands

| Task | Command |
|---|---|
| View container status | `cd /opt/ytvideosautomation && docker compose ps` |
| View backend logs | `cd /opt/ytvideosautomation && docker compose logs -f backend` |
| View upload worker logs | `cd /opt/ytvideosautomation && docker compose logs -f backend \| grep -i worker` |
| Restart platform | `sudo systemctl restart ytvideosautomation` |
| Update to latest version | `git pull && docker compose up -d --build` |
| Run manual backup | `sudo bash /opt/ytvideosautomation/deploy/backup.sh` |
