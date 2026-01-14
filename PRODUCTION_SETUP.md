# Production Deployment Guide - Complete Setup

This guide covers the complete production deployment of Amarktai Network with all features enabled.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [WebSocket Configuration](#websocket-configuration)
6. [Platform Configuration](#platform-configuration)
7. [Testing & Validation](#testing--validation)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

```
┌─────────────────┐
│   Nginx (443)   │ ← HTTPS/WSS termination
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼────┐ ┌─▼────────┐
│ Static │ │  Backend │ ← FastAPI (port 8000)
│  Files │ │   API    │
└────────┘ └──┬───────┘
              │
         ┌────┴────┐
         │ MongoDB │ ← Database (port 27017)
         └─────────┘
```

### Real-Time Architecture

- **Primary**: WebSocket (`wss://domain.com/api/ws`)
- **Fallback**: HTTP polling (auto-enabled if WS fails)
- **Authentication**: JWT token (query param or header)
- **Reconnection**: Exponential backoff (max 10 attempts)

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 24.04 LTS
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 20GB minimum
- **CPU**: 2 cores minimum

### Software Requirements

```bash
# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install MongoDB (Docker)
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo docker run -d --name amarktai-mongo --restart always \
  -p 127.0.0.1:27017:27017 \
  -v /var/amarktai/mongodb:/data/db \
  mongo:7

# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## Backend Setup

### 1. Clone Repository

```bash
sudo mkdir -p /var/amarktai
cd /var/amarktai
sudo git clone https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment.git app
cd app
```

### 2. Install Python Dependencies

```bash
python3.12 -m venv /var/amarktai/venv
source /var/amarktai/venv/bin/activate
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required Environment Variables:**

```bash
# Security (MUST change for production!)
JWT_SECRET=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 24)

# Database
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=amarktai_production

# Feature Flags (enable for production)
ENABLE_TRADING=1
ENABLE_SCHEDULERS=1
ENABLE_CCXT=1
ENABLE_AUTOPILOT=0  # Enable after testing

# Exchange API Keys (add your keys)
LUNO_API_KEY=your_key
LUNO_API_SECRET=your_secret
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
KUCOIN_API_KEY=your_key
KUCOIN_API_SECRET=your_secret
KUCOIN_PASSWORD=your_password
KRAKEN_API_KEY=your_key
KRAKEN_API_SECRET=your_secret
VALR_API_KEY=your_key
VALR_API_SECRET=your_secret

# AI Services (optional)
OPENAI_API_KEY=sk-your-key-here

# CORS (set your domain)
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 4. Initialize Database

```bash
# Test database connection
python -c "from database import connect; import asyncio; asyncio.run(connect()); print('✅ Database connected')"
```

### 5. Create Systemd Service

Create `/etc/systemd/system/amarktai-backend.service`:

```ini
[Unit]
Description=Amarktai Trading Platform - Backend API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/amarktai/app/backend
Environment="PATH=/var/amarktai/venv/bin"
ExecStart=/var/amarktai/venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/amarktai

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable amarktai-backend
sudo systemctl start amarktai-backend
sudo systemctl status amarktai-backend
```

### 6. Verify Backend

```bash
# Test health endpoint
curl http://localhost:8000/api/health/ping

# Expected: {"status":"healthy","db":"connected","timestamp":"..."}

# Test platforms endpoint
TOKEN="your-jwt-token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/system/platforms

# Expected: {"platforms":[{"name":"luno",...},{"name":"binance",...},...]}
```

---

## Frontend Setup

### 1. Install Dependencies

```bash
cd /var/amarktai/app/frontend
npm install
```

### 2. Configure Environment (if needed)

Create `.env.production`:

```bash
# API will be proxied through Nginx, so use relative paths
REACT_APP_API_BASE=/api
```

### 3. Run Asset Validation

```bash
npm run check:assets
```

Expected output:
```
✅ All asset references are valid!
```

### 4. Build for Production

```bash
npm run build
```

This creates an optimized build in `frontend/build/`.

### 5. Verify Build

```bash
# Check build output
ls -lh build/

# Should see:
# - index.html
# - static/js/*.js
# - static/css/*.css
# - assets/*.png, *.jpg, *.mp4
```

---

## WebSocket Configuration

### 1. Verify Backend WebSocket Endpoint

```bash
# Test WebSocket using websocat (install: cargo install websocat)
websocat "ws://localhost:8000/api/ws?token=YOUR_JWT_TOKEN"

# Or use the browser console:
# const ws = new WebSocket('ws://localhost:8000/api/ws?token=YOUR_TOKEN');
# ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### 2. Configure Nginx for WebSocket

Add to your Nginx configuration:

```nginx
# WebSocket upgrade headers
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend static files
    location / {
        root /var/amarktai/app/frontend/build;
        try_files $uri /index.html;
        add_header Cache-Control "public, max-age=3600";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        
        # Timeouts for WebSocket
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. Test WebSocket Through Nginx

```bash
# Test WSS connection
websocat "wss://your-domain.com/api/ws?token=YOUR_JWT_TOKEN"
```

---

## Platform Configuration

### 1. Verify All 5 Platforms

The system supports 5 platforms:
- **Luno** 🌙
- **Binance** 🔶
- **KuCoin** 🔷
- **Kraken** 🐙
- **VALR** 💎

Verify they're all enabled:

```bash
curl -H "Authorization: Bearer $TOKEN" https://your-domain.com/api/system/platforms | jq '.platforms | length'

# Expected: 5
```

### 2. Test API Keys for Each Platform

```bash
# Test each platform's API key
for platform in luno binance kucoin kraken valr; do
    echo "Testing $platform..."
    curl -H "Authorization: Bearer $TOKEN" \
         -X POST \
         "https://your-domain.com/api/api-keys/$platform/test"
done
```

---

## Testing & Validation

### 1. Run Endpoint Self-Test

```bash
cd /var/amarktai/app
./scripts/test-endpoints.sh https://your-domain.com YOUR_JWT_TOKEN
```

This tests all critical endpoints and reports pass/fail.

### 2. Manual UI Testing

Follow the **GO_LIVE_CHECKLIST.md** for comprehensive UI testing:

1. Login / Authentication
2. Dashboard loads
3. All 5 platforms visible
4. WebSocket connected
5. Real-time updates working
6. Bot creation works
7. Trades display
8. Wallet loads
9. Whale Flow displays
10. Decision Trace displays
11. Metrics load
12. Admin panel gating works

### 3. Load Testing (Optional)

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Test API performance
ab -n 1000 -c 10 https://your-domain.com/api/health/ping

# Test authenticated endpoint
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" \
   https://your-domain.com/api/bots
```

---

## Monitoring & Maintenance

### 1. System Logs

```bash
# Backend logs
sudo journalctl -u amarktai-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# MongoDB logs (Docker)
sudo docker logs -f amarktai-mongo
```

### 2. Prometheus Metrics

Access system metrics:

```bash
curl https://your-domain.com/api/metrics
```

### 3. Health Checks

```bash
# System health
curl https://your-domain.com/api/system/health

# Database connectivity
curl https://your-domain.com/api/health/ping
```

### 4. Automated Monitoring

Set up cron job for health checks:

```bash
# Add to crontab
*/5 * * * * /usr/bin/curl -f https://your-domain.com/api/health/ping || /usr/bin/systemctl restart amarktai-backend
```

### 5. Database Backups

```bash
# Create backup script: /var/amarktai/backup.sh
#!/bin/bash
BACKUP_DIR="/var/amarktai/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup MongoDB
sudo docker exec amarktai-mongo mongodump \
  --out /data/backup_$DATE

sudo docker cp amarktai-mongo:/data/backup_$DATE \
  $BACKUP_DIR/

# Keep only last 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;
```

Add to crontab:

```bash
0 2 * * * /var/amarktai/backup.sh
```

---

## Troubleshooting

### WebSocket Not Connecting

**Symptoms**: "WebSocket error" in console, connection stuck on "Disconnected"

**Solutions**:
1. Check Nginx WebSocket configuration (Upgrade headers)
2. Verify firewall allows WSS (port 443)
3. Check browser console for CORS errors
4. Test direct backend connection: `ws://localhost:8000/api/ws?token=TOKEN`

### Assets Not Loading (404 errors)

**Symptoms**: Broken images, missing logo/background

**Solutions**:
1. Run asset validator: `npm run check:assets`
2. Ensure build copied assets: `ls frontend/build/assets/`
3. Check Nginx static file serving
4. Verify file permissions: `sudo chmod -R 755 /var/amarktai/app/frontend/build`

### 401 Unauthorized Errors

**Symptoms**: API calls fail with 401, redirect to login

**Solutions**:
1. Check JWT token in localStorage: `localStorage.getItem('token')`
2. Verify JWT_SECRET matches between frontend/backend
3. Check token expiration (default 24 hours)
4. Clear localStorage and re-login

### Platforms Not Showing

**Symptoms**: Empty platform selector, missing platforms

**Solutions**:
1. Verify endpoint: `curl -H "Authorization: Bearer $TOKEN" /api/system/platforms`
2. Check backend logs for errors
3. Ensure all 5 platforms configured in backend

### Bot Creation Fails

**Symptoms**: "Failed to create bot" error

**Solutions**:
1. Check API key is configured for selected platform
2. Verify capital requirements met
3. Check platform supports selected trading mode (paper/live)
4. Review backend logs for specific error

### High Memory Usage

**Symptoms**: System slow, OOM kills

**Solutions**:
1. Reduce uvicorn workers: `--workers 1`
2. Limit bot count per platform
3. Increase swap space
4. Monitor with: `htop` or `free -h`

### Database Connection Lost

**Symptoms**: "db":"disconnected" in health check

**Solutions**:
1. Check MongoDB running: `sudo docker ps | grep mongo`
2. Restart MongoDB: `sudo docker restart amarktai-mongo`
3. Check MongoDB logs: `sudo docker logs amarktai-mongo`
4. Verify network connectivity: `nc -zv 127.0.0.1 27017`

---

## Security Checklist

- [ ] JWT_SECRET is strong and unique
- [ ] ADMIN_PASSWORD is strong and unique
- [ ] MongoDB not exposed to internet (127.0.0.1 only)
- [ ] SSL certificate valid and auto-renewing
- [ ] Firewall configured (allow 80, 443, 22 only)
- [ ] Backend port 8000 not exposed externally
- [ ] Strong passwords for all exchange API keys
- [ ] API keys have minimal required permissions
- [ ] Regular database backups configured
- [ ] Logs monitored for suspicious activity
- [ ] Rate limiting enabled in Nginx (optional)
- [ ] Fail2ban configured (optional)

---

## Performance Optimization

### Nginx Caching

Add to Nginx config:

```nginx
# Cache static assets
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|mp4)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Gzip Compression

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
gzip_min_length 1000;
```

### Backend Tuning

```bash
# Increase file descriptor limits
sudo nano /etc/security/limits.conf

# Add:
* soft nofile 65536
* hard nofile 65536
```

---

## Support & Resources

- **Documentation**: See ENDPOINTS.md, WEBSOCKET_SCHEMAS.md
- **Go-Live Checklist**: GO_LIVE_CHECKLIST.md
- **Endpoint Testing**: `./scripts/test-endpoints.sh`
- **Asset Validation**: `npm run check:assets`

---

**Last Updated**: 2026-01-14  
**Version**: 1.0.0
