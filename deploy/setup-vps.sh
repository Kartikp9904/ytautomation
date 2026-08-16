#!/bin/bash
# ==============================================================================
# YouTube Video Automation Platform - Ubuntu VPS Automated Provisioning Script
# Supported OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS (x86_64 / ARM64)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  YouTube Video Automation Platform - VPS Installer   ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] This script must be run as root. Run with 'sudo bash setup-vps.sh'.${NC}"
    exit 1
fi

# 2. System Package Updates
echo -e "\n${YELLOW}[1/7] Updating system package index...${NC}"
apt update && apt upgrade -y
apt install -y curl git ufw fail2ban nginx certbot python3-certbot-nginx apt-transport-https ca-certificates gnupg lsb-release

# 3. Install Official Docker Engine & Docker Compose Plugin
echo -e "\n${YELLOW}[2/7] Installing Docker Engine & Docker Compose Plugin...${NC}"
if ! command -v docker &> /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    echo -e "${GREEN}[OK] Docker installed successfully.${NC}"
else
    echo -e "${GREEN}[OK] Docker is already installed.${NC}"
fi

# 4. Configure UFW Firewall
echo -e "\n${YELLOW}[3/7] Hardening network firewall (UFW)...${NC}"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP Web'
ufw allow 443/tcp comment 'HTTPS Web'
ufw --force enable
echo -e "${GREEN}[OK] Firewall configured: SSH (22), HTTP (80), HTTPS (443) open.${NC}"

# 5. Configure Fail2ban Intrusion Prevention
echo -e "\n${YELLOW}[4/7] Configuring Fail2ban intrusion prevention...${NC}"
if [ -f "deploy/fail2ban/jail.local" ]; then
    cp deploy/fail2ban/jail.local /etc/fail2ban/jail.local
    systemctl restart fail2ban
    systemctl enable fail2ban
    echo -e "${GREEN}[OK] Fail2ban configured & active.${NC}"
fi

# 6. Deploy Application Directory & Permissions
echo -e "\n${YELLOW}[5/7] Setting up application workspace at /opt/ytvideosautomation...${NC}"
INSTALL_DIR="/opt/ytvideosautomation"
mkdir -p "$INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/docker-compose.yml" ]; then
    cp -r . "$INSTALL_DIR/"
fi

cd "$INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "${YELLOW}Generating default .env from template...${NC}"
    cp .env.docker.example .env
    
    # Generate cryptographic keys
    GEN_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i "s/generate_a_secure_64_character_random_hex_key_here/$GEN_SECRET/" .env
    
    chmod 600 .env
    echo -e "${GREEN}[OK] Secure .env generated with random SECRET_KEY (Permissions: 600).${NC}"
fi

# 7. Configure Systemd Service
echo -e "\n${YELLOW}[6/7] Installing Systemd auto-start service...${NC}"
cp deploy/systemd/ytvideosautomation.service /etc/systemd/system/ytvideosautomation.service
systemctl daemon-reload
systemctl enable ytvideosautomation.service
echo -e "${GREEN}[OK] Systemd service enabled.${NC}"

# 8. Start Containers
echo -e "\n${YELLOW}[7/7] Launching Docker containers...${NC}"
docker compose up -d --build

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  Installation & Hardening Completed Successfully!     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Next steps:"
echo -e "1. Edit /opt/ytvideosautomation/.env with your Google OAuth credentials:"
echo -e "   ${BLUE}nano /opt/ytvideosautomation/.env${NC}"
echo -e "2. Restart containers after editing credentials:"
echo -e "   ${BLUE}cd /opt/ytvideosautomation && docker compose restart${NC}"
echo -e "3. Configure SSL with Let's Encrypt Certbot:"
echo -e "   ${BLUE}certbot --nginx -d yourdomain.com${NC}"
echo -e "4. Access your dashboard at: ${BLUE}http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')${NC}\n"
