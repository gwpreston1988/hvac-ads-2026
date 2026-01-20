#!/bin/bash
# =============================================================================
# HVAC-ADS-2026: Bootstrap VM (run ON the VM)
# =============================================================================
# This script sets up a fresh Ubuntu VM with Docker and the hvac-ads-2026 app.
# Run this script as root (sudo) on the VM after creation.
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
APP_DIR="/opt/hvac-ads-2026"
REPO_URL="${REPO_URL:-https://github.com/gwpreston1988/hvac-ads-2026.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}HVAC-ADS-2026: VM Bootstrap${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (sudo)${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# STEP 1: System updates
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/6] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# -----------------------------------------------------------------------------
# STEP 2: Install dependencies
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/6] Installing dependencies...${NC}"
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    jq \
    htop \
    unzip

# -----------------------------------------------------------------------------
# STEP 3: Install Docker
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/6] Installing Docker...${NC}"

# Remove old versions if any
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify Docker installation
docker --version
docker compose version

echo -e "${GREEN}  Docker installed successfully${NC}"

# -----------------------------------------------------------------------------
# STEP 4: Create app directory and clone repo
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/6] Setting up application directory...${NC}"

# Create app directory
mkdir -p "${APP_DIR}"
cd "${APP_DIR}"

# Clone or update repo
if [ -d "${APP_DIR}/.git" ]; then
    echo "  Repository exists, pulling latest..."
    git fetch origin
    git reset --hard "origin/${REPO_BRANCH}"
else
    echo "  Cloning repository..."
    git clone --branch "${REPO_BRANCH}" "${REPO_URL}" .
fi

# Create data directories
mkdir -p "${APP_DIR}/snapshots"
mkdir -p "${APP_DIR}/reports"
mkdir -p "${APP_DIR}/plans"

echo -e "${GREEN}  App directory ready: ${APP_DIR}${NC}"

# -----------------------------------------------------------------------------
# STEP 5: Set up permissions
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/6] Setting permissions...${NC}"

# Set ownership
chown -R root:root "${APP_DIR}"

# Make bin scripts executable
chmod +x "${APP_DIR}/bin/"* 2>/dev/null || true
chmod +x "${APP_DIR}/infra/gcp/"*.sh 2>/dev/null || true

# Create .env file template if not exists
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "  Creating .env template..."
    cat > "${APP_DIR}/.env" << 'ENVFILE'
# =============================================================================
# HVAC-ADS-2026 Environment Configuration
# =============================================================================
# IMPORTANT: This file contains secrets. Do NOT commit to git.
# Permissions should be 600 (owner read/write only)
# =============================================================================

# -----------------------------------------------------------------------------
# Google Ads API
# -----------------------------------------------------------------------------
GOOGLE_ADS_CUSTOMER_ID=9256598060
GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID=YOUR_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET=YOUR_CLIENT_SECRET
GOOGLE_ADS_LOGIN_CUSTOMER_ID=5194867886
GOOGLE_ADS_REFRESH_TOKEN=YOUR_REFRESH_TOKEN

# -----------------------------------------------------------------------------
# Merchant Center
# -----------------------------------------------------------------------------
MERCHANT_CENTER_ID=5308355318

# -----------------------------------------------------------------------------
# Google Search Console (GSC)
# -----------------------------------------------------------------------------
GSC_SITE_URL=https://buycomfortdirect.com

# -----------------------------------------------------------------------------
# Twilio
# -----------------------------------------------------------------------------
# Option 1: Use Account SID (AC*) + Auth Token
# TWILIO_ACCOUNT_SID=YOUR_ACCOUNT_SID (starts with AC)
# TWILIO_AUTH_TOKEN=YOUR_AUTH_TOKEN

# Option 2: Use API Key SID (SK*) + API Secret (recommended)
TWILIO_ACCOUNT_SID=YOUR_API_KEY_SID
TWILIO_API_SECRET=YOUR_API_SECRET
TWILIO_FORWARD_TO_NUMBER=YOUR_FORWARD_TO_NUMBER

# -----------------------------------------------------------------------------
# BigCommerce (optional)
# -----------------------------------------------------------------------------
BIGCOMMERCE_STORE_HASH=YOUR_STORE_HASH
BIGCOMMERCE_ACCESS_TOKEN=YOUR_ACCESS_TOKEN
BIGCOMMERCE_CLIENT_ID=YOUR_CLIENT_ID

# -----------------------------------------------------------------------------
# Anthropic (for AI features)
# -----------------------------------------------------------------------------
ANTHROPIC_API_KEY=YOUR_API_KEY

# -----------------------------------------------------------------------------
# MCP Server
# -----------------------------------------------------------------------------
MCP_PORT=8080
MCP_HOST=0.0.0.0
ENVFILE

    # Secure the .env file
    chmod 600 "${APP_DIR}/.env"
    echo -e "${YELLOW}  IMPORTANT: Edit ${APP_DIR}/.env with your actual credentials!${NC}"
else
    echo "  .env file already exists"
    chmod 600 "${APP_DIR}/.env"
fi

# -----------------------------------------------------------------------------
# STEP 6: Build and start containers
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[6/6] Building and starting Docker containers...${NC}"

cd "${APP_DIR}"

# Build images
docker compose build

# Start services
docker compose up -d

# Wait for health check
echo "  Waiting for services to start..."
sleep 10

# Check health
if curl -sf http://localhost:8080/health > /dev/null; then
    echo -e "${GREEN}  Health check passed!${NC}"
else
    echo -e "${YELLOW}  Health check pending (may need a moment)${NC}"
fi

# -----------------------------------------------------------------------------
# Output summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}BOOTSTRAP COMPLETE${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""
echo "Application Directory: ${APP_DIR}"
echo ""
echo "Docker Status:"
docker compose ps
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit .env with your actual credentials:"
echo "   sudo nano ${APP_DIR}/.env"
echo ""
echo "2. Restart services after editing .env:"
echo "   cd ${APP_DIR} && sudo docker compose restart"
echo ""
echo "3. View logs:"
echo "   cd ${APP_DIR} && sudo docker compose logs -f"
echo ""
echo "4. Run baseline commands:"
echo "   cd ${APP_DIR} && sudo docker compose exec baseline bin/dump"
echo "   cd ${APP_DIR} && sudo docker compose exec baseline bin/report --latest"
echo ""
echo "5. Test health endpoint:"
echo "   curl http://localhost:8080/health"
echo ""
echo -e "${GREEN}Bootstrap complete!${NC}"
