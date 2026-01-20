# HVAC-ADS-2026: GCP VM Deployment

This directory contains scripts and documentation for deploying the hvac-ads-2026 system to a Google Compute Engine VM.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GCE VM (hvac-ads-prod-01)                   │
│                     Ubuntu 22.04 LTS                             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Docker Compose                         │    │
│  │                                                           │    │
│  │  ┌─────────────────┐      ┌─────────────────┐           │    │
│  │  │   mcp (8080)    │      │    baseline     │           │    │
│  │  │                 │      │                 │           │    │
│  │  │  MCP Server     │      │  CLI Runner     │           │    │
│  │  │  (FastAPI)      │      │  (sleep inf)    │           │    │
│  │  └────────┬────────┘      └────────┬────────┘           │    │
│  │           │                        │                     │    │
│  │           └────────────┬───────────┘                     │    │
│  │                        │                                 │    │
│  │              ┌─────────▼─────────┐                       │    │
│  │              │  Shared Volumes   │                       │    │
│  │              │  /app/snapshots   │                       │    │
│  │              │  /app/reports     │                       │    │
│  │              │  /app/plans       │                       │    │
│  │              │  /app/diag        │                       │    │
│  │              └───────────────────┘                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Service Account: hvac-ads-runtime@bcd-seo-engine.iam...        │
│  Scopes: cloud-platform (for ADC)                               │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Access to `bcd-seo-engine` GCP project
- Git access to the repository

## Quick Start

### 1. Provision the VM (run locally)

```bash
# From repo root
chmod +x infra/gcp/create_vm.sh
./infra/gcp/create_vm.sh
```

This will:
- Enable required GCP APIs
- Create service account `hvac-ads-runtime`
- Reserve static IP
- Create firewall rules (SSH + port 8080)
- Create VM with Ubuntu 22.04 LTS

### 2. Bootstrap the VM (run on VM)

```bash
# SSH into the VM
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a

# Run bootstrap script
curl -sSL https://raw.githubusercontent.com/gwpreston1988/hvac-ads-2026/main/infra/gcp/bootstrap_vm.sh | sudo bash
```

Or manually:
```bash
# Copy and run
scp infra/gcp/bootstrap_vm.sh hvac-ads-prod-01:~/
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a -- 'sudo bash ~/bootstrap_vm.sh'
```

### 3. Configure Credentials

```bash
# SSH into VM
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a

# Edit .env file
sudo nano /opt/hvac-ads-2026/.env

# Restart services
cd /opt/hvac-ads-2026 && sudo docker compose restart
```

### 4. Verify Deployment

```bash
# Get external IP
EXTERNAL_IP=$(gcloud compute addresses describe hvac-ads-ip --region=us-central1 --format="value(address)")

# Test health endpoint
curl http://${EXTERNAL_IP}:8080/health

# Test tools endpoint
curl http://${EXTERNAL_IP}:8080/tools
```

---

## Operations Commands

### SSH Access

```bash
# Standard SSH
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a

# With port forwarding (for local testing)
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a -- -L 8080:localhost:8080
```

### Deploy Updates

```bash
# SSH into VM first
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a

# Pull latest code and restart
cd /opt/hvac-ads-2026
sudo git pull origin main
sudo docker compose build
sudo docker compose up -d
```

### View Logs

```bash
# All services
sudo docker compose logs -f

# MCP server only
sudo docker compose logs -f mcp

# Baseline runner only
sudo docker compose logs -f baseline

# Last 100 lines
sudo docker compose logs --tail=100 mcp
```

### Run Baseline CLI Commands

```bash
# Phase A: Dump state (live API reads)
sudo docker compose exec baseline bin/dump

# Phase B: Generate report (snapshot-only)
sudo docker compose exec baseline bin/report --latest

# Phase C: Generate plan (snapshot-only)
sudo docker compose exec baseline bin/plan --latest

# Phase C: Apply plan (live API writes - USE WITH CAUTION)
sudo docker compose exec baseline bin/apply --plan plans/runs/<plan-file>.json
```

### Container Management

```bash
# Check status
sudo docker compose ps

# Restart all services
sudo docker compose restart

# Restart specific service
sudo docker compose restart mcp
sudo docker compose restart baseline

# Stop all services
sudo docker compose down

# Stop and remove volumes (CAUTION: loses data)
sudo docker compose down -v

# Rebuild images
sudo docker compose build --no-cache
```

### Health Checks

```bash
# Local check (on VM)
curl http://localhost:8080/health

# Remote check
curl http://<EXTERNAL_IP>:8080/health

# JSON response
curl -s http://localhost:8080/health | jq .
```

---

## Configuration

### Environment Variables

The `.env` file at `/opt/hvac-ads-2026/.env` contains all credentials:

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_ADS_CUSTOMER_ID` | Google Ads account ID | Yes |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API developer token | Yes |
| `GOOGLE_ADS_CLIENT_ID` | OAuth client ID | Yes |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth client secret | Yes |
| `GOOGLE_ADS_REFRESH_TOKEN` | OAuth refresh token | Yes |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | MCC account ID | Optional |
| `MERCHANT_CENTER_ID` | Google Merchant Center ID | Yes |
| `GSC_SITE_URL` | Google Search Console site URL | For GSC features |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For Twilio features |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For Twilio features |
| `TWILIO_FORWARD_TO_NUMBER` | Phone number to forward calls | For Twilio features |
| `ANTHROPIC_API_KEY` | Anthropic API key | For AI features |

### Service Account

The VM runs with the `hvac-ads-runtime` service account attached, which:
- Has `cloud-platform` scope for ADC (Application Default Credentials)
- Has `logging.logWriter` and `monitoring.metricWriter` roles

For GSC/Indexing API access:
1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add `hvac-ads-runtime@bcd-seo-engine.iam.gserviceaccount.com` as an owner
3. The VM can then use ADC for these APIs

---

## File Locations

| Path | Description |
|------|-------------|
| `/opt/hvac-ads-2026/` | Application root |
| `/opt/hvac-ads-2026/.env` | Environment configuration (secrets) |
| `/opt/hvac-ads-2026/snapshots/` | Snapshot data (persisted) |
| `/opt/hvac-ads-2026/reports/` | Generated reports (persisted) |
| `/opt/hvac-ads-2026/plans/` | Generated plans (persisted) |
| `/opt/hvac-ads-2026/diag/` | Diagnostic files (persisted) |

---

## Troubleshooting

### Container won't start

```bash
# Check logs
sudo docker compose logs mcp

# Check if port is in use
sudo lsof -i :8080

# Check Docker status
sudo systemctl status docker
```

### Permission denied errors

```bash
# Fix ownership
sudo chown -R root:root /opt/hvac-ads-2026

# Fix .env permissions
sudo chmod 600 /opt/hvac-ads-2026/.env
```

### Can't connect to VM

```bash
# Check VM status
gcloud compute instances describe hvac-ads-prod-01 --zone=us-central1-a

# Check firewall rules
gcloud compute firewall-rules list --filter="name~hvac"

# Restart VM
gcloud compute instances reset hvac-ads-prod-01 --zone=us-central1-a
```

### API authentication issues

```bash
# Check if ADC works (on VM)
gcloud auth application-default print-access-token

# Re-authenticate
gcloud auth application-default login
```

---

## Costs

Estimated monthly costs for `e2-standard-2`:
- VM: ~$50/month
- Static IP: ~$7/month (if attached)
- Disk (50GB): ~$5/month
- **Total: ~$62/month**

To reduce costs:
- Use `e2-small` for lower traffic: ~$15/month
- Use preemptible VM: ~60% discount (but can be terminated)

---

## Security Notes

1. **Never commit `.env`** - It contains secrets
2. **Firewall is minimal** - Only SSH (22) and MCP (8080) are open
3. **Service account has minimal roles** - Only logging/monitoring
4. **OAuth tokens for Google Ads** - Must be refreshed via OAuth flow
5. **Consider adding TLS** - If exposing to internet long-term

---

## Scripts Reference

| Script | Run Where | Purpose |
|--------|-----------|---------|
| `create_vm.sh` | Local | Provisions GCE VM and networking |
| `bootstrap_vm.sh` | VM | Installs Docker and deploys app |

---

## Acceptance Checklist

After deployment, verify:

- [ ] VM is reachable via SSH: `gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a`
- [ ] Docker is running: `sudo docker --version`
- [ ] Containers are up: `sudo docker compose ps`
- [ ] Health check passes: `curl http://<IP>:8080/health`
- [ ] Tools endpoint works: `curl http://<IP>:8080/tools`
- [ ] Baseline CLI works: `sudo docker compose exec baseline bin/report --latest`
