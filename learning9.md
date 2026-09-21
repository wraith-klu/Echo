# Learning 9 — Cloud Deployment: Docker, Nginx, HTTPS, Oracle VM, CI/CD

> **Capstone Step 9 Study Guide** — Interview-focused reference covering containerization, reverse proxies, TLS/HTTPS, cloud VM networking, and deployment automation.

---

## 1. Oracle Cloud Always Free — Provisioning Walkthrough

### Why Oracle Cloud Free Tier?
| Provider | Free CPU | Free RAM | AI workload viability |
|----------|---------|---------|----------------------|
| Oracle Ampere A1 | 4 OCPU (ARM) | 24 GB | ✅ Runs Whisper + NLLB + Piper |
| Render Free | 0.1 vCPU | 512 MB | ❌ OOM on model load |
| AWS EC2 t2.micro | 1 vCPU (x86) | 1 GB | ❌ OOM on model load |
| GCP e2-micro | 0.25 vCPU | 1 GB | ❌ Too small |

Oracle's Always Free A1 (`VM.Standard.A1.Flex`) gives 4 OCPUs + 24 GB RAM at zero cost — the only free tier large enough for this workload.

### Step-by-Step: Provisioning the Instance

```
1. Sign up at cloud.oracle.com (requires credit card for identity — NOT charged)

2. Go to: Compute → Instances → Create Instance
   ┌─────────────────────────────────────────────────────┐
   │ Name: capstron-backend                              │
   │ Availability Domain: AD-1 (check availability)      │
   │ Image: Canonical Ubuntu 22.04 LTS (aarch64/ARM)     │
   │ Shape: VM.Standard.A1.Flex                          │
   │   OCPUs: 2 (up to 4, all free)                     │
   │   Memory: 12 GB (up to 24 GB, all free)            │
   └─────────────────────────────────────────────────────┘

3. Networking:
   - Create new VCN (Virtual Cloud Network) OR use existing
   - Subnet: Public subnet (gets a public IP)
   - Public IP: Assign ephemeral (or Reserved for a static IP)

4. SSH Keys:
   - Generate locally: ssh-keygen -t ed25519 -C "capstron-oracle"
   - Upload the PUBLIC key (.pub) in the OCI console
   - Keep the PRIVATE key safe — this is your only way to SSH in

5. Boot Volume:
   - Size: 50 GB minimum (models need ~15 GB, OS ~5 GB, app ~2 GB)
   - Recommended: 100 GB (still free)

6. Click Create. Wait ~2 minutes for provisioning.
   Public IP: shown in Instance Details → copy it.

7. SSH in:
   ssh -i ~/.ssh/id_ed25519 ubuntu@<PUBLIC_IP>
```

### Opening Ports — Security List (Firewall)

Oracle's "Security List" is OCI's inbound firewall. By default only port 22 (SSH) is open.

```
Go to: Networking → Virtual Cloud Networks → your-VCN
     → Security Lists → Default Security List
     → Add Ingress Rules:

Source CIDR: 0.0.0.0/0 (all IPs)

Rule 1 — HTTP
  Protocol: TCP
  Destination Port: 80

Rule 2 — HTTPS / WSS
  Protocol: TCP
  Destination Port: 443

Rule 3 — (optional dev) Direct FastAPI
  Protocol: TCP
  Destination Port: 8000
```

> **Also**: Ubuntu's `ufw` firewall runs inside the VM and blocks ports independently.
> After SSH-ing in, run:
> ```bash
> sudo ufw allow 22
> sudo ufw allow 80
> sudo ufw allow 443
> sudo ufw enable
> ```

---

## 2. Docker & Containerization Fundamentals

### What Problem Does Docker Solve?

> **"It works on my machine"** → Docker makes it work everywhere.

Docker packages your app + all its dependencies (Python 3.11, ffmpeg, ONNX runtime, etc.) into a portable **image**. That image runs identically on your laptop, the Oracle VM, or any CI server.

| Without Docker | With Docker |
|---------------|-------------|
| Install Python 3.11 on VM | `docker pull` |
| Install ffmpeg, libgomp | Baked into image |
| Match OS versions | Isolated container |
| Manually manage venv | `pip install` inside image |
| "Works on my machine" | Works everywhere |

### Key Concepts

```
Image   → Read-only blueprint (like a class definition)
Container → Running instance of an image (like an object)
Layer   → Each RUN/COPY instruction adds a filesystem layer; layers are cached
Registry → Docker Hub, GHCR — stores and distributes images
Volume  → Persistent storage outside the container (survives restarts)
Network → Virtual LAN between containers (services find each other by name)
```

### Multi-Stage Build — Why?

A naive Dockerfile includes build tools (gcc, curl, Poetry) in the final image.
Multi-stage keeps only what's needed at runtime:

```dockerfile
# Stage 1: builder — has gcc, Poetry, build-essential
FROM python:3.11-slim AS builder
RUN poetry install ...

# Stage 2: runtime — only has ffmpeg, libgomp, installed packages
FROM python:3.11-slim AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages ...
```

**Result:** Image goes from ~2 GB → ~700 MB — faster pulls, smaller attack surface.

### Where Should AI Models Live? (The Key Architecture Decision)

| Strategy | Description | Verdict |
|----------|-------------|---------|
| **Bake into image** | `RUN python -c "from transformers import ..."` during build | ❌ Image is 10-15 GB; slow CI/CD; model updates require full rebuild |
| **Download at startup** | Container downloads model on first boot | ⚠️ First boot takes 5-20 min; needs internet; OK if behind a Docker volume |
| **Docker volume** ✅ | Download once, cache in named volume; subsequent starts skip download | ✅ Best for this project |
| **NFS / object storage** | Mount S3/OCI Object Storage bucket | ✅ Production-grade; overkill for capstone |

**This project uses: Docker volume (`model_cache`) + download-on-first-boot.**  
- First `docker compose up`: models download → volume filled (~10-15 GB, ~20 min)  
- Every subsequent restart: volume already has models → fast startup (~30-90 sec)

---

## 3. Reverse Proxy — What Is It and Why?

### What Is a Reverse Proxy?

A reverse proxy sits **in front of** your application server and is the only service the internet talks to directly.

```
Internet ──→ Nginx (port 443, HTTPS) ──→ FastAPI (port 8000, HTTP, inside Docker network)
              ↑ handles SSL, routing,
                compression, rate limiting
```

**Why not expose FastAPI directly?**
- FastAPI/Uvicorn are not designed to handle raw internet traffic (no SSL, limited connection handling)
- Nginx handles thousands of concurrent connections efficiently
- SSL termination in one place — Uvicorn only needs to speak plain HTTP
- Nginx can serve static files, rate-limit, and add security headers without touching app code

### Why WebSockets Need Special Proxy Config

WebSocket upgrades use HTTP/1.1 with a protocol upgrade handshake:

```
Client → Nginx:
  GET /ws/audio HTTP/1.1
  Host: api.example.com
  Upgrade: websocket         ← must be forwarded
  Connection: Upgrade        ← must be forwarded (NOT "keep-alive"!)
```

By default Nginx **drops** the `Connection` header (it normalizes it to `close` or `keep-alive`). Without the two magic directives, the WebSocket handshake fails silently:

```nginx
# These two lines are MANDATORY for WebSocket proxying
proxy_http_version 1.1;
proxy_set_header   Upgrade    $http_upgrade;
proxy_set_header   Connection "upgrade";
```

Also critical: set long timeouts. A 60-second default timeout will kill a WebSocket session mid-translation:
```nginx
proxy_read_timeout  3600s;   # 1 hour — keep session alive
proxy_buffering     off;     # stream binary audio frames immediately, don't buffer
```

---

## 4. HTTPS / TLS — How It Works

### TLS Handshake (Simplified)

```
1. Client → Server: "ClientHello" (TLS version, cipher suites supported)
2. Server → Client: "ServerHello" + Certificate (public key, domain, expiry)
3. Client validates: Is this cert signed by a trusted CA? Is the domain correct?
4. Client → Server: Generate session key (encrypted with server's public key)
5. Both sides now have the same symmetric session key
6. All further traffic is encrypted with AES (symmetric — fast)
```

The asymmetric (RSA/ECDHE) step only happens once. All real data uses fast symmetric AES encryption.

### Let's Encrypt — How It Works

Let's Encrypt is a free, automated Certificate Authority (CA).

```
1. You run: certbot certonly --webroot -d your-domain.com
2. Certbot generates a challenge token and writes it to: /var/www/certbot/.well-known/acme-challenge/TOKEN
3. Let's Encrypt servers fetch: http://your-domain.com/.well-known/acme-challenge/TOKEN
4. If the file matches → domain ownership proven → certificate issued
5. Certificate is valid for 90 days → auto-renew every 60 days
```

Nginx serves the `/.well-known/acme-challenge/` path over HTTP (port 80) — that's why the HTTP server block must NOT redirect this path to HTTPS.

### Commands to Get SSL Certificates

```bash
# Issue certificate (run on the VM, after nginx is running on port 80)
docker compose run --rm \
  --profile certbot \
  certbot certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    -d your-domain.com \
    --email your@email.com \
    --agree-tos \
    --non-interactive

# Renew (add to crontab: 0 3 * * * docker compose run --rm certbot renew)
docker compose run --rm certbot renew

# After renewing, reload nginx config (no downtime)
docker compose exec nginx nginx -s reload
```

> **Before SSL**: Use a plain HTTP config first (comment out the 443 server block), verify the app works, then issue certs.

---

## 5. Secrets Management

### The Problem

`.env` files contain database passwords. If committed to git → passwords are exposed forever (git history).

### This Project's Approach

```
.gitignore:
  backend/.env.production      # ← never committed

On the VM:
  nano ~/capstron/backend/.env.production
  chmod 600 ~/capstron/backend/.env.production   # only owner (ubuntu) can read
```

### Hierarchy

| File | Committed? | Purpose |
|------|-----------|---------|
| `backend/.env.example` | ✅ Yes | Template with fake values for documentation |
| `backend/.env.production.example` | ✅ Yes | Template for production (no real secrets) |
| `backend/.env` | ❌ No | Local dev secrets |
| `backend/.env.production` | ❌ No | Production secrets on VM only |

### How ESP32 Firmware Gets the WebSocket URL

The ESP32 firmware needs to know `wss://your-domain.com/ws/audio`. This is **hardcoded or configured in the firmware**:

```cpp
// firmware/config.h (committed to git)
#define WS_HOST     "api.capstron.example.com"
#define WS_PORT     443
#define WS_PATH     "/ws/audio"
#define WS_USE_SSL  true   // ArduinoWebsockets uses SSL when port is 443
```

If the domain changes: update `config.h`, recompile, re-flash.

For a more flexible approach: store the URL in ESP32 EEPROM/NVS (non-volatile storage) and provide a BLE/WiFi provisioning interface to update it — but that's beyond this capstone scope.

---

## 6. CI/CD — Capstone vs Production

### This Project: "CI/CD-lite" (Deploy Script)

```bash
# From your laptop:
ssh ubuntu@YOUR_VM_IP "cd ~/capstron && ./deploy.sh"
```

The `deploy.sh` script does:
1. `git pull` — get latest code
2. Check `.env.production` exists
3. `docker compose build` — rebuild only changed layers
4. `alembic upgrade head` — run DB migrations before restart
5. `docker compose up -d` — rolling restart
6. Health check + log tail

**Trigger manually** after every pushed commit. This is sufficient for a capstone.

### "Proper" CI/CD for Reference (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Oracle VM

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        run: |
          pip install pytest
          pytest backend/tests/

      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.ORACLE_VM_IP }}
          username: ubuntu
          key: ${{ secrets.ORACLE_SSH_KEY }}
          script: |
            cd ~/capstron
            ./deploy.sh
```

Secrets stored in GitHub → Settings → Secrets — never in the repo.

---

## 7. Monitoring & Memory Management

### Is the App Alive? (Uptime Check)

```bash
# Manual
curl https://your-domain.com/health

# Expected response
{"status": "ok"}

# Free uptime monitoring services
# - UptimeRobot (free, checks every 5 min, alerts by email/Telegram)
# - BetterUptime
# Configure: ping GET https://your-domain.com/health every 5 minutes
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Just the app
docker compose logs -f web --tail=100

# Filter for errors
docker compose logs web | grep -i "error\|warning\|exception"

# Check nginx access log
docker compose exec nginx tail -f /var/log/nginx/access.log
```

### Memory Management — Running 3 AI Models on 12-24 GB RAM

| Model | RAM footprint |
|-------|--------------|
| Whisper `base` (int8) | ~300 MB |
| NLLB-200 600M (quantized int8) | ~1.2 GB |
| Piper voice (ONNX, per language) | ~60-120 MB |
| **Total** | **~1.8 GB active** |
| Python + FastAPI overhead | ~200 MB |
| PostgreSQL | ~100 MB |
| **Grand total** | **~2.1 GB** |

With 12 GB RAM this is very comfortable. But model loading spikes RAM:

**Mitigations:**
1. **Lazy loading** — Piper voices are already lazy-loaded on first TTS call per language. Whisper and NLLB load on startup.
2. **Load order** — Load in RAM-ascending order: TTS → Whisper → NLLB. If NLLB OOMs, at least ASR works.
3. **Swap space** — Protect against occasional spikes:
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
4. **Docker memory limit** — Set in docker-compose.yml:
   ```yaml
   web:
     deploy:
       resources:
         limits:
           memory: 10G
   ```
5. **Monitor live**:
   ```bash
   watch -n 2 'free -h && docker stats --no-stream'
   ```

---

## 8. Full Deployment: Fresh VM → Running Backend

Run these commands on the Oracle VM in order (paste into a terminal after SSH-ing in):

```bash
# ============================================================
# Phase 0: Initial VM Setup (run once)
# ============================================================

# Update OS
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker Engine (official script)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # add ubuntu user to docker group
newgrp docker                   # reload group (or log out/in)

# Verify Docker works
docker run --rm hello-world

# Install Docker Compose plugin (included with modern Docker Engine)
docker compose version

# Install git
sudo apt-get install -y git

# ============================================================
# Phase 1: Clone the project
# ============================================================
git clone https://github.com/YOUR_USERNAME/capstron-project.git ~/capstron
cd ~/capstron

# ============================================================
# Phase 2: Configure secrets
# ============================================================
cp backend/.env.production.example backend/.env.production
nano backend/.env.production
# Fill in: POSTGRES_PASSWORD, BACKEND_CORS_ORIGINS, etc.
chmod 600 backend/.env.production

# ============================================================
# Phase 3: Configure domain in Nginx
# ============================================================
# Replace YOUR_DOMAIN with your actual domain in nginx config
sed -i 's/YOUR_DOMAIN/api.yourdomain.com/g' nginx/conf.d/app.conf
# (Or manually edit the file)

# ============================================================
# Phase 4: Ufw firewall
# ============================================================
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# ============================================================
# Phase 5: First boot (HTTP only — before SSL certs)
# ============================================================
# Comment out the HTTPS server block in nginx/conf.d/app.conf first,
# or use a minimal HTTP-only config to pass the ACME challenge.

# Start database and nginx (HTTP only)
docker compose up -d db nginx

# ============================================================
# Phase 6: Issue SSL certificate
# ============================================================
docker compose run --rm --profile certbot certbot certonly \
  --webroot --webroot-path /var/www/certbot \
  -d api.yourdomain.com \
  --email your@email.com \
  --agree-tos --non-interactive

# ============================================================
# Phase 7: Enable HTTPS and start full stack
# ============================================================
# Uncomment the HTTPS server block in nginx/conf.d/app.conf
# (Un-comment the 443 server block and SSL directives)

docker compose up -d --build
# This triggers model downloads — WAIT ~20 min for first startup

# Watch startup progress
docker compose logs -f web

# ============================================================
# Phase 8: Run migrations
# ============================================================
docker compose run --rm \
  -e POSTGRES_HOST=db \
  --env-file backend/.env.production \
  web python -m alembic upgrade head

# ============================================================
# Phase 9: Verify everything
# ============================================================
curl https://api.yourdomain.com/health
# Expected: {"status": "ok"}

curl https://api.yourdomain.com/api/v1/status
# Expected: {"services": {"ingestion": "ready", "asr": "ready", ...}}

# ============================================================
# Phase 10: Set up auto-renewal for SSL
# ============================================================
# Add to crontab: renew at 3 AM daily (certbot is a no-op if not due)
(crontab -l 2>/dev/null; echo "0 3 * * * cd ~/capstron && docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload") | crontab -

# ============================================================
# Phase 11: Add swap space (safety net)
# ============================================================
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 9. Common Interview Questions

**Q1: What is Docker and what problem does it solve?**  
> Docker packages an application and all its dependencies into a portable **container image**. This ensures the app runs identically everywhere — eliminating "works on my machine" issues. Key concepts: images (immutable blueprints), containers (running instances), layers (cached incremental changes), volumes (persistent storage). Docker achieves isolation using Linux kernel features: **namespaces** (process/network/filesystem isolation) and **cgroups** (CPU/RAM limits).

**Q2: What is a reverse proxy and why is Nginx used instead of exposing the app directly?**  
> A reverse proxy sits in front of application servers and is the single public entry point. Nginx handles: **SSL termination** (only Nginx needs a certificate — the app uses plain HTTP internally), **connection multiplexing** (Nginx handles thousands of concurrent connections efficiently), **security headers**, **rate limiting**, and **static file serving**. Exposing Uvicorn directly means every client establishes a raw TCP connection to your Python process, with no TLS, no buffering protection, and no access control.

**Q3: Why do WebSockets need special handling in Nginx?**  
> WebSocket connections start as HTTP/1.1 requests with `Upgrade: websocket` and `Connection: Upgrade` headers. By default, Nginx rewrites the `Connection` header (removes `Upgrade`), causing the WebSocket handshake to fail. The fix is two directives: `proxy_set_header Upgrade $http_upgrade;` and `proxy_set_header Connection "upgrade";`. Additionally, WebSocket sessions are long-lived, so `proxy_read_timeout` must be extended (default 60s → hours), and `proxy_buffering off` ensures audio frames are streamed immediately rather than buffered.

**Q4: How does HTTPS/TLS work at a high level?**  
> TLS uses **asymmetric cryptography** for the initial handshake (server proves identity via certificate, client generates a session key encrypted with the server's public key) and **symmetric cryptography** (AES) for all actual data (fast). The certificate is signed by a trusted **Certificate Authority (CA)** — browsers trust a built-in list of CAs. Let's Encrypt is a free, automated CA that issues certificates valid for 90 days, renewed via the ACME protocol (a challenge/response to prove domain ownership).

**Q5: What is a VCN / Security List in Oracle Cloud?**  
> A **VCN (Virtual Cloud Network)** is a software-defined private network in Oracle Cloud — analogous to an AWS VPC. It contains **subnets** (CIDR ranges like 10.0.0.0/24) that VMs are placed into. A **Security List** is OCI's stateful firewall that controls inbound/outbound traffic at the subnet level using rules (protocol + port + source CIDR). Unlike AWS Security Groups (per-instance), Oracle Security Lists apply to all resources in a subnet. To accept HTTPS traffic you must add an Ingress Rule: protocol=TCP, port=443, source=0.0.0.0/0.

---

*Step 9 complete. Next: Step 10 — ESP32 Firmware Integration (I2S microphone capture → WebSocket stream → I2S speaker playback).*
