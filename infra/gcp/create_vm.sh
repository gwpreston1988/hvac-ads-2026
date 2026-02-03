#!/bin/bash
# =============================================================================
# HVAC-ADS-2026: Create GCE VM (run LOCALLY)
# =============================================================================
# This script provisions a GCE VM for the hvac-ads-2026 system.
# Run this from your local machine with gcloud configured.
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# CONFIGURATION (edit these if needed)
# -----------------------------------------------------------------------------
GCP_PROJECT_ID="${GCP_PROJECT_ID:-bcd-seo-engine}"
GCP_REGION="${GCP_REGION:-us-central1}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
VM_NAME="${VM_NAME:-hvac-ads-prod-01}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
BOOT_DISK_GB="${BOOT_DISK_GB:-50}"
STATIC_IP_NAME="${STATIC_IP_NAME:-hvac-ads-ip}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-hvac-ads-runtime}"
NETWORK_TAG="hvac-ads-server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}HVAC-ADS-2026: GCE VM Provisioning${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""
echo "Configuration:"
echo "  Project:      ${GCP_PROJECT_ID}"
echo "  Region:       ${GCP_REGION}"
echo "  Zone:         ${GCP_ZONE}"
echo "  VM Name:      ${VM_NAME}"
echo "  Machine Type: ${MACHINE_TYPE}"
echo "  Boot Disk:    ${BOOT_DISK_GB}GB"
echo ""

# -----------------------------------------------------------------------------
# STEP 1: Set project
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/8] Setting GCP project...${NC}"
gcloud config set project "${GCP_PROJECT_ID}"

# -----------------------------------------------------------------------------
# STEP 2: Enable required APIs
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/8] Enabling required APIs...${NC}"
APIS=(
    "compute.googleapis.com"
    "iam.googleapis.com"
    "serviceusage.googleapis.com"
    "searchconsole.googleapis.com"
    "indexing.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo "  Enabling ${api}..."
    gcloud services enable "${api}" --quiet 2>/dev/null || true
done

# -----------------------------------------------------------------------------
# STEP 3: Create service account (if not exists)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/8] Creating service account...${NC}"
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "  Service account already exists: ${SA_EMAIL}"
else
    echo "  Creating service account: ${SERVICE_ACCOUNT_NAME}"
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="HVAC Ads Runtime Service Account" \
        --description="Service account for hvac-ads-2026 VM runtime" \
        --project="${GCP_PROJECT_ID}"
fi

# Assign minimal roles
echo "  Assigning roles..."
ROLES=(
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${role}" \
        --quiet 2>/dev/null || true
done

echo ""
echo -e "${GREEN}  Service Account Email: ${SA_EMAIL}${NC}"
echo -e "${YELLOW}  NOTE: To use GSC/Indexing API, add this email as an owner in Google Search Console!${NC}"
echo ""

# -----------------------------------------------------------------------------
# STEP 4: Reserve static IP (if not exists)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/8] Reserving static IP...${NC}"
if gcloud compute addresses describe "${STATIC_IP_NAME}" --region="${GCP_REGION}" &>/dev/null; then
    echo "  Static IP already exists: ${STATIC_IP_NAME}"
else
    echo "  Creating static IP: ${STATIC_IP_NAME}"
    gcloud compute addresses create "${STATIC_IP_NAME}" \
        --region="${GCP_REGION}" \
        --network-tier=PREMIUM
fi

EXTERNAL_IP=$(gcloud compute addresses describe "${STATIC_IP_NAME}" \
    --region="${GCP_REGION}" \
    --format="value(address)")
echo -e "${GREEN}  External IP: ${EXTERNAL_IP}${NC}"

# -----------------------------------------------------------------------------
# STEP 5: Create firewall rules (if not exist)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/8] Creating firewall rules...${NC}"

# Allow SSH (port 22)
if gcloud compute firewall-rules describe "allow-ssh-hvac-ads" &>/dev/null; then
    echo "  Firewall rule 'allow-ssh-hvac-ads' already exists"
else
    echo "  Creating firewall rule for SSH..."
    gcloud compute firewall-rules create "allow-ssh-hvac-ads" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:22 \
        --source-ranges=0.0.0.0/0 \
        --target-tags="${NETWORK_TAG}"
fi

# Allow MCP port (8080) - restricted to your IP
# Get current IP if not set
if [ -z "${MY_IP}" ]; then
    echo "  Detecting your public IP..."
    MY_IP=$(curl -s ifconfig.me)
    echo -e "${GREEN}  Detected IP: ${MY_IP}${NC}"
    echo -e "${YELLOW}  Port 8080 will be restricted to ${MY_IP}/32${NC}"
    echo -e "${YELLOW}  To allow different IP, set MY_IP env var before running this script${NC}"
fi

if gcloud compute firewall-rules describe "allow-mcp-hvac-ads" &>/dev/null; then
    echo "  Firewall rule 'allow-mcp-hvac-ads' already exists"
else
    echo "  Creating firewall rule for MCP (8080)..."
    gcloud compute firewall-rules create "allow-mcp-hvac-ads" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:8080 \
        --source-ranges="${MY_IP}/32" \
        --target-tags="${NETWORK_TAG}"
fi

# -----------------------------------------------------------------------------
# STEP 6: Create VM instance
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[6/8] Creating VM instance...${NC}"

if gcloud compute instances describe "${VM_NAME}" --zone="${GCP_ZONE}" &>/dev/null; then
    echo -e "${YELLOW}  VM '${VM_NAME}' already exists. Skipping creation.${NC}"
else
    echo "  Creating VM: ${VM_NAME}"
    gcloud compute instances create "${VM_NAME}" \
        --zone="${GCP_ZONE}" \
        --machine-type="${MACHINE_TYPE}" \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size="${BOOT_DISK_GB}GB" \
        --boot-disk-type=pd-balanced \
        --address="${EXTERNAL_IP}" \
        --service-account="${SA_EMAIL}" \
        --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/indexing,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write \
        --tags="${NETWORK_TAG}" \
        --metadata=enable-oslogin=TRUE
fi

# -----------------------------------------------------------------------------
# STEP 7: Upload bootstrap script to VM
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[7/8] Uploading bootstrap script to VM...${NC}"

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BOOTSTRAP_SCRIPT="${SCRIPT_DIR}/bootstrap_vm.sh"

if [ -f "${BOOTSTRAP_SCRIPT}" ]; then
    echo "  Waiting for VM to be ready..."
    sleep 10

    echo "  Uploading ${BOOTSTRAP_SCRIPT} to VM..."
    gcloud compute scp "${BOOTSTRAP_SCRIPT}" \
        "${VM_NAME}:/tmp/bootstrap_vm.sh" \
        --zone="${GCP_ZONE}" \
        --quiet || {
            echo -e "${YELLOW}  Warning: Could not upload bootstrap script. You'll need to copy it manually.${NC}"
        }

    echo -e "${GREEN}  Bootstrap script uploaded to /tmp/bootstrap_vm.sh${NC}"
else
    echo -e "${YELLOW}  Warning: Bootstrap script not found at ${BOOTSTRAP_SCRIPT}${NC}"
    echo -e "${YELLOW}  You'll need to copy it manually to the VM${NC}"
fi

# -----------------------------------------------------------------------------
# STEP 8: Output summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=============================================================================${NC}"
echo -e "${GREEN}VM PROVISIONING COMPLETE${NC}"
echo -e "${GREEN}=============================================================================${NC}"
echo ""
echo "VM Details:"
echo "  Name:        ${VM_NAME}"
echo "  Zone:        ${GCP_ZONE}"
echo "  External IP: ${EXTERNAL_IP}"
echo "  Service Acct: ${SA_EMAIL}"
echo ""
echo "Next Steps:"
echo ""
echo "1. Add service account to Google Search Console (REQUIRED for GSC/Indexing API):"
echo -e "   ${GREEN}${SA_EMAIL}${NC}"
echo "   "
echo "   Manual steps (must be done in GSC UI):"
echo "   a. Go to: https://search.google.com/search-console"
echo "   b. Select property: buycomfortdirect.com"
echo "   c. Settings → Users and permissions → Add user"
echo "   d. Email: ${SA_EMAIL}"
echo "   e. Permission level: Full (Owner recommended)"
echo "   f. Click Add"
echo ""
echo "2. SSH into the VM:"
echo -e "   ${GREEN}gcloud compute ssh ${VM_NAME} --zone=${GCP_ZONE}${NC}"
echo ""
echo "3. Run the bootstrap script (already uploaded to /tmp):"
echo -e "   ${GREEN}sudo bash /tmp/bootstrap_vm.sh${NC}"
echo ""
echo "4. Edit .env file on VM with your Google Ads OAuth token:"
echo "   sudo nano /opt/hvac-ads-2026/.env"
echo "   # Add GOOGLE_ADS_REFRESH_TOKEN (all other credentials are already set)"
echo ""
echo "5. Restart containers after editing .env:"
echo "   cd /opt/hvac-ads-2026"
echo "   sudo docker compose restart"
echo ""
echo "6. Test the deployment:"
echo "   MCP Health:  curl http://${EXTERNAL_IP}:8080/health"
echo "   MCP Tools:   curl http://${EXTERNAL_IP}:8080/tools"
echo "   Baseline:    sudo docker compose exec baseline bin/dump"
echo ""
echo -e "${GREEN}Firewall: Port 8080 restricted to ${MY_IP}/32${NC}"
