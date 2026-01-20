# HVAC-ADS-2026 GCE Deployment Runbook

Complete step-by-step guide for deploying hvac-ads-2026 to Google Compute Engine.

## Prerequisites

1. **Local Machine Setup**
   - gcloud CLI installed: https://cloud.google.com/sdk/docs/install
   - Authenticated with GCP: `gcloud auth login`
   - Git repo cloned locally
   - Current working directory: `hvac-ads-2026/`

2. **GCP Project**
   - Project ID: `bcd-seo-engine`
   - Billing enabled
   - Owner/Editor permissions

3. **Credentials Ready**
   - Google Ads OAuth refresh token (from existing setup)
   - All other credentials already in local `.env` file

---

## Part 1: Provision VM from Local Machine

### Step 1.1: Run Provisioning Script

```bash
cd infra/gcp
./create_vm.sh
```

**What this does:**
- Enables GCP APIs (Compute, IAM, Search Console, Indexing)
- Creates service account `hvac-ads-runtime@bcd-seo-engine.iam.gserviceaccount.com`
- Reserves static IP
- Creates firewall rules:
  - SSH (port 22): open to 0.0.0.0/0
  - MCP (port 8080): **restricted to your current IP only**
- Provisions e2-standard-2 VM in us-central1-a
- Uploads bootstrap script to VM at `/tmp/bootstrap_vm.sh`

**Expected output:**
```
============================================================================
VM PROVISIONING COMPLETE
============================================================================

VM Details:
  Name:        hvac-ads-prod-01
  Zone:        us-central1-a
  External IP: X.X.X.X
  Service Acct: hvac-ads-runtime@bcd-seo-engine.iam.gserviceaccount.com

Next Steps:
[... detailed instructions ...]
```

**If your IP changes:** To update the firewall rule for port 8080:
```bash
MY_NEW_IP=$(curl -s ifconfig.me)
gcloud compute firewall-rules update allow-mcp-hvac-ads \
  --source-ranges="${MY_NEW_IP}/32"
```

---

## Part 2: Configure Google Search Console Permissions

**REQUIRED** for GSC query and Indexing API tools to work.

### Step 2.1: Add Service Account to GSC Property

1. Go to: https://search.google.com/search-console
2. Select property: **buycomfortdirect.com**
3. Click: **Settings** (left sidebar)
4. Click: **Users and permissions**
5. Click: **Add user** (blue button)
6. Enter email:
   ```
   hvac-ads-runtime@bcd-seo-engine.iam.gserviceaccount.com
   ```
7. Select permission level: **Full** (Owner recommended)
8. Click: **Add**

**Verification:**
- Service account should appear in the users list
- Permission should show "Full" or "Owner"

**Note:** This cannot be done via gcloud CLI - GSC property permissions are managed through the web UI only.

---

## Part 3: Bootstrap VM

### Step 3.1: SSH to VM

```bash
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a
```

### Step 3.2: Run Bootstrap Script

```bash
sudo bash /tmp/bootstrap_vm.sh
```

**What this does:**
- Updates system packages
- Installs Docker + docker-compose
- Clones repo to `/opt/hvac-ads-2026`
- Creates `.env` file from template with placeholders
- Builds and starts Docker containers

**Expected duration:** 5-10 minutes (includes Docker image build)

**Expected output:**
```
============================================================================
BOOTSTRAP COMPLETE
============================================================================

Docker Status:
NAME                   IMAGE                   STATUS
hvac-ads-mcp          hvac-ads-2026_mcp       Up
hvac-ads-baseline     hvac-ads-2026_baseline  Up

Next Steps:
1. Edit .env with your actual credentials:
   sudo nano /opt/hvac-ads-2026/.env
...
```

### Step 3.3: Add Google Ads Refresh Token to .env

```bash
sudo nano /opt/hvac-ads-2026/.env
```

**Find this line:**
```bash
GOOGLE_ADS_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
```

**Replace with your actual token** (from local `.env` file or OAuth flow):
```bash
GOOGLE_ADS_REFRESH_TOKEN=1//01S4itnX3Xc-aCgYIARAAGAESNwF-L9IrCWlCajXf4CI0ylDVrZt0wyEab3B0WcHEF637YrtExWqDE0guEf4cpN6wgd6xdflJ0rc
```

**Save and exit:** Ctrl+O, Enter, Ctrl+X

**All other credentials** (Ads Customer ID, Developer Token, Client ID/Secret, MCC ID, Merchant Center ID, GSC URL, Twilio, BigCommerce, Anthropic) are already filled in from the template.

### Step 3.4: Restart Containers

```bash
cd /opt/hvac-ads-2026
sudo docker compose restart
```

**Wait 10 seconds for services to start.**

---

## Part 4: Smoke Tests

Run these commands **on the VM** (stay SSH'd in from Part 3).

### Test 4.1: MCP Health Check

```bash
curl http://localhost:8080/health
```

**Expected:**
```json
{"status": "healthy", "service": "hvac-ads-mcp", "timestamp": "2026-01-20T..."}
```

### Test 4.2: MCP Tools Endpoint

```bash
curl http://localhost:8080/tools
```

**Expected:** JSON array with tools:
```json
{
  "tools": [
    {"name": "gsc_query", "description": "Query Google Search Console performance data", ...},
    {"name": "indexing_publish", "description": "Submit URLs to Google Indexing API", ...},
    {"name": "twilio_events", "description": "Query Twilio call/SMS event logs", ...}
  ]
}
```

### Test 4.3: MCP Tool Invocation (Stub)

```bash
curl -X POST http://localhost:8080/invoke/gsc_query \
  -H "Content-Type: application/json" \
  -d '{"site_url": "https://buycomfortdirect.com", "start_date": "2026-01-01", "end_date": "2026-01-20"}'
```

**Expected:** Stub response (Phase D0 not yet implemented):
```json
{
  "status": "NOT_IMPLEMENTED",
  "tool": "gsc_query",
  "message": "GSC query is not yet implemented",
  "phase": "D0",
  ...
}
```

### Test 4.4: Baseline CLI - Dump

```bash
cd /opt/hvac-ads-2026
sudo docker compose exec baseline bin/dump
```

**Expected:**
- Creates new snapshot in `snapshots/YYYY-MM-DDTHHMMSZ/`
- Outputs: `ads_campaigns.json`, `ads_search_terms.json`, `merchant_product_issues.json`, etc.
- Final line: `Snapshot saved to: snapshots/YYYY-MM-DDTHHMMSZ`

**Note:** This performs **LIVE API READS** from Google Ads and Merchant Center.

### Test 4.5: Baseline CLI - Report

```bash
sudo docker compose exec baseline bin/report --latest
```

**Expected:**
- Reads latest snapshot (from Test 4.4)
- Generates `reports/latest.md`
- Outputs: Campaign summary, search terms, merchant issues, etc.
- Final line: `Report saved to: reports/latest.md`

**Note:** This is **READ-ONLY** from snapshot data, no live API calls.

### Test 4.6: Baseline CLI - Plan

```bash
sudo docker compose exec baseline bin/plan --latest
```

**Expected:**
- Reads latest snapshot + report
- Generates proposed changes (e.g., PMax brand exclusions, exact match migrations)
- Creates `plans/proposed_changes_TIMESTAMP.json`
- Final line: `Plan saved to: plans/proposed_changes_TIMESTAMP.json`

**Note:** This is **READ-ONLY** analysis, no live API calls.

### Test 4.7: Container Logs

```bash
# MCP logs
sudo docker compose logs mcp

# Baseline logs (should be minimal since it's sleep infinity)
sudo docker compose logs baseline

# Follow logs in real-time
sudo docker compose logs -f
```

---

## Part 5: Test from Local Machine

Exit the VM SSH session (Ctrl+D or `exit`).

### Test 5.1: MCP Health from Local Mac

Get the VM external IP:
```bash
gcloud compute instances describe hvac-ads-prod-01 \
  --zone=us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

Test MCP health:
```bash
curl http://<EXTERNAL_IP>:8080/health
```

**Expected:** Same as Test 4.1

**If this fails:**
- Check firewall: `gcloud compute firewall-rules describe allow-mcp-hvac-ads`
- Verify your IP matches: `curl -s ifconfig.me`
- Update firewall if IP changed (see Part 1 "If your IP changes")

---

## Part 6: Ongoing Operations

### View Container Status

```bash
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a
cd /opt/hvac-ads-2026
sudo docker compose ps
```

### Run Baseline Cycle

```bash
# Full cycle: dump → report → plan
sudo docker compose exec baseline bin/dump
sudo docker compose exec baseline bin/report --latest
sudo docker compose exec baseline bin/plan --latest
```

### Apply Changes (LIVE WRITES)

**WARNING:** Only run this after carefully reviewing the plan!

```bash
sudo docker compose exec baseline bin/apply --plan plans/proposed_changes_TIMESTAMP.json
```

### Update Code on VM

```bash
cd /opt/hvac-ads-2026
sudo git pull origin main
sudo docker compose down
sudo docker compose up -d --build
```

### View Logs

```bash
sudo docker compose logs -f mcp
sudo docker compose logs -f baseline
```

### Restart Services

```bash
sudo docker compose restart
```

### Stop Services

```bash
sudo docker compose down
```

### SSH Directly to Baseline Container

```bash
sudo docker compose exec baseline bash
# Now you're inside the container
ls -la snapshots/
exit
```

---

## Known Gaps & Limitations

### 1. Google Ads OAuth
**Status:** Requires manual token
**Workaround:** Copy `GOOGLE_ADS_REFRESH_TOKEN` from local `.env` to VM `.env`
**Why:** OAuth flow requires browser interaction, not practical on headless VM

### 2. GSC Property Permissions
**Status:** Must be done manually in GSC UI
**Workaround:** Part 2 instructions above
**Why:** gcloud CLI does not support GSC property-level permission management

### 3. MCP Tools (Phase D0)
**Status:** All tools return `NOT_IMPLEMENTED`
**Scope:**
- `gsc_query`: GSC performance data
- `indexing_publish`: Indexing API submissions
- `twilio_events`: Call/SMS event logs

**Expected:** Phase D implementation will add live API calls

### 4. Baseline Loop Automation
**Status:** Manual execution required
**Future:** Add cron job or systemd timer for scheduled dumps

### 5. Firewall IP Restriction
**Status:** Port 8080 restricted to single IP
**Limitation:** If your IP changes, MCP becomes inaccessible from your Mac
**Fix:** Run firewall update command (see Part 1)

---

## Troubleshooting

### Container won't start
```bash
sudo docker compose logs mcp
sudo docker compose logs baseline
```

Check for missing env vars or permission issues.

### MCP health check fails
1. Check container status: `sudo docker compose ps`
2. Check logs: `sudo docker compose logs mcp`
3. Test inside VM: `curl http://localhost:8080/health`
4. If works locally but not remotely, check firewall

### Baseline dump fails
1. Check Google Ads refresh token in `.env`
2. Verify service account has GSC permissions (Part 2)
3. Check logs: `sudo docker compose logs baseline`

### Cannot SSH to VM
```bash
# Check VM status
gcloud compute instances describe hvac-ads-prod-01 --zone=us-central1-a

# Check firewall
gcloud compute firewall-rules describe allow-ssh-hvac-ads

# Try with explicit SSH
gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a --ssh-flag="-v"
```

### Disk space issues
```bash
# Check disk usage
df -h

# Clean up Docker
sudo docker system prune -a

# Clean old snapshots (manual)
cd /opt/hvac-ads-2026/snapshots
sudo rm -rf 2026-01-15*  # Example: remove old snapshots
```

---

## Security Notes

1. **Port 8080 Firewall:** Restricted to your IP only. Update if IP changes.
2. **SSH Access:** Port 22 open to 0.0.0.0/0 (standard GCE practice with OS Login)
3. **.env File:** Contains secrets, permissions set to 600 (owner read/write only)
4. **Service Account Scopes:** Limited to:
   - `webmasters.readonly` (GSC read)
   - `indexing` (Indexing API)
   - `logging.write` (Cloud Logging)
   - `monitoring.write` (Cloud Monitoring)
5. **No secrets in git:** `.env` file never committed, only `.env.template` with placeholders

---

## Decommissioning

To tear down the deployment:

```bash
# Delete VM
gcloud compute instances delete hvac-ads-prod-01 --zone=us-central1-a

# Delete static IP
gcloud compute addresses delete hvac-ads-ip --region=us-central1

# Delete firewall rules
gcloud compute firewall-rules delete allow-ssh-hvac-ads
gcloud compute firewall-rules delete allow-mcp-hvac-ads

# Delete service account (optional)
gcloud iam service-accounts delete hvac-ads-runtime@bcd-seo-engine.iam.gserviceaccount.com

# Remove from GSC (manual)
# Go to GSC → Settings → Users → Remove service account
```

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH to VM | `gcloud compute ssh hvac-ads-prod-01 --zone=us-central1-a` |
| Restart containers | `cd /opt/hvac-ads-2026 && sudo docker compose restart` |
| View logs | `sudo docker compose logs -f mcp` |
| Run dump | `sudo docker compose exec baseline bin/dump` |
| Run report | `sudo docker compose exec baseline bin/report --latest` |
| Run plan | `sudo docker compose exec baseline bin/plan --latest` |
| Test MCP health | `curl http://localhost:8080/health` |
| Update code | `sudo git pull && sudo docker compose up -d --build` |
| Check status | `sudo docker compose ps` |
| Get VM IP | `gcloud compute instances describe hvac-ads-prod-01 --zone=us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)"` |

---

**Last updated:** 2026-01-20
**VM:** hvac-ads-prod-01
**Region:** us-central1-a
**Machine Type:** e2-standard-2
