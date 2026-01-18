# Amarktai Network - Production Deployment Guide

**Last Updated:** 2026-01-15
**Target Environment:** Ubuntu 24.04 LTS
**Production Ready:** ✅ YES

---

## 🚀 QUICK START (If System Already Set Up)

If this is an **update deployment** on an already-running system:

```bash
# 1. Pull latest changes
cd /var/amarktai/app
git pull origin main

# 2. Run production readiness verification
python3 scripts/verify_production_ready.py
# Must show: 🎉 ALL CHECKS PASSED - Production Ready

# 3. Update backend dependencies (if needed)
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Restart services
sudo systemctl restart amarktai-api
sudo systemctl status amarktai-api

# 5. Verify deployment
python3 scripts/verify_go_live.py
curl http://localhost:8001/api/health/ping
```

**Critical Notes:**
- Auth system now supports backward-compatible password hash fields
- JWT tokens use consistent `user_id` claim
- Price endpoint resilient to missing API keys
- All API key endpoints properly secured with JWT auth
- Paper trading enabled by default (live trading requires explicit flag)

**Environment Variables:**
- `ENABLE_LIVE_TRADING=false` (default, safe)
- `JWT_SECRET` must be set (min 32 chars)
- `JWT_ALGORITHM=HS256` (default, can override)

For **first-time setup**, continue reading below.

---

## Prerequisites

### System Requirements

- **OS:** Ubuntu 24.04 LTS (or similar)
- **Python:** 3.11 or higher
- **Node.js:** 20.x or higher
- **MongoDB:** 4.4 or higher
- **Nginx:** Latest stable
- **RAM:** Minimum 4GB (8GB recommended)
- **Disk:** Minimum 20GB free space

### Required Services

1. **MongoDB** - Running and accessible
2. **Nginx** - For reverse proxy and static file serving
3. **SSL/TLS Certificate** - Let's Encrypt recommended
4. **systemd** - For service management

---

## Part 1: Environment Setup

### 1.1 Clone Repository

```bash
git clone https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment.git
cd Amarktai-Network---Deployment
```

### 1.2 Backend Environment Variables

Create `/home/runner/work/Amarktai-Network---Deployment/Amarktai-Network---Deployment/backend/.env`:

```bash
# ============================================================================
# REQUIRED ENVIRONMENT VARIABLES
# ============================================================================

# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=amarktai_trading

# Security (REQUIRED - Generate with: openssl rand -hex 32)
JWT_SECRET=your_generated_secret_key_here_change_this

# AI Integration (REQUIRED for AI features)
OPENAI_API_KEY=sk-your-openai-key-here

# ============================================================================
# OPTIONAL: SMTP EMAIL CONFIGURATION
# ============================================================================

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Amarktai Network
DAILY_REPORT_TIME=08:00

# ============================================================================
# FEATURE FLAGS (Safe defaults for production)
# ============================================================================

# Start with conservative settings
ENABLE_TRADING=false
ENABLE_AUTOPILOT=false
ENABLE_CCXT=true
ENABLE_SCHEDULERS=false
ENABLE_REALTIME=true

# Enable gradually:
# Step 1: ENABLE_CCXT=true (price data only) ✅ Safe
# Step 2: ENABLE_TRADING=true (paper trading only)
# Step 3: ENABLE_SCHEDULERS=true (autonomous features)
# Step 4: ENABLE_AUTOPILOT=true (full autopilot)

# ============================================================================
# TRADING LIMITS (Production defaults)
# ============================================================================

MAX_TRADES_PER_BOT_DAILY=50
MAX_TRADES_PER_USER_DAILY=500
BURST_LIMIT_ORDERS_PER_EXCHANGE=10
BURST_LIMIT_WINDOW_SECONDS=10

# Circuit Breaker Thresholds
MAX_DRAWDOWN_PERCENT=0.20
MAX_DAILY_LOSS_PERCENT=0.10
MAX_CONSECUTIVE_LOSSES=5
MAX_ERRORS_PER_HOUR=10

# Fee Coverage Configuration
MIN_EDGE_BPS=10.0
SAFETY_MARGIN_BPS=5.0
SLIPPAGE_BUFFER_BPS=10.0

# Daily Reinvestment Configuration
REINVEST_THRESHOLD=500
REINVEST_TOP_N=3
REINVEST_PERCENTAGE=80
DAILY_REINVEST_TIME=02:00

# ============================================================================
# OPTIONAL: EXTERNAL INTEGRATIONS
# ============================================================================

FETCHAI_API_KEY=
FLOKX_API_KEY=
PAYMENT_AGENT_ENABLED=false
ENABLE_UAGENTS=false
```

**Security Notes:**
- ⚠️ **NEVER** commit `.env` to git
- ⚠️ Generate unique JWT_SECRET: `openssl rand -hex 32`
- ⚠️ Use app-specific passwords for Gmail SMTP
- ⚠️ Restrict file permissions: `chmod 600 backend/.env`

---

## Part 2: Backend Deployment

### 2.1 Install Python Dependencies

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.2 Verify Backend Installation

```bash
# Test backend imports
python3 -c "import fastapi; import motor; import ccxt; print('✅ Dependencies OK')"

# Check MongoDB connection
python3 -c "from motor.motor_asyncio import AsyncIOMotorClient; import asyncio; asyncio.run(AsyncIOMotorClient('mongodb://localhost:27017').admin.command('ping')); print('✅ MongoDB OK')"
```

### 2.3 Start Backend (Development)

```bash
# From backend/ directory with venv activated
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: `http://localhost:8000`

**Test Backend:**
```bash
curl http://localhost:8000/api/system/ping
# Should return: {"status":"ok","timestamp":"2026-01-14T..."}
```

---

## Part 3: Frontend Deployment

### 3.1 Install Frontend Dependencies

```bash
cd frontend

# Install dependencies
npm install

# Or with yarn
yarn install
```

### 3.2 Build Frontend for Production

```bash
# Create production build
npm run build

# Build output will be in frontend/build/
```

### 3.3 Verify Frontend Build

```bash
# Check build output
ls -lh build/
# Should see: index.html, static/, asset-manifest.json

# Test build locally
npx serve -s build -p 3000
# Open browser to http://localhost:3000
```

---

## Part 4: Production Deployment with systemd

### 4.1 Create Backend systemd Service

Create `/etc/systemd/system/amarktai-backend.service`:

```ini
[Unit]
Description=Amarktai Network Backend API
After=network.target mongod.service
Requires=mongod.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/amarktai/backend
Environment="PATH=/var/www/amarktai/backend/venv/bin"
ExecStart=/var/www/amarktai/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/var/log/amarktai-backend.log
StandardError=append:/var/log/amarktai-backend-error.log

[Install]
WantedBy=multi-user.target
```

### 4.2 Deploy Backend to Production

```bash
# Copy application to production directory
sudo mkdir -p /var/www/amarktai
sudo cp -r /path/to/Amarktai-Network---Deployment/backend /var/www/amarktai/

# Set permissions
sudo chown -R www-data:www-data /var/www/amarktai
sudo chmod 600 /var/www/amarktai/backend/.env

# Create log files
sudo touch /var/log/amarktai-backend.log
sudo touch /var/log/amarktai-backend-error.log
sudo chown www-data:www-data /var/log/amarktai-*.log

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable amarktai-backend
sudo systemctl start amarktai-backend

# Check status
sudo systemctl status amarktai-backend
sudo journalctl -u amarktai-backend -f
```

---

## Part 5: Nginx Configuration

### 5.1 Create Nginx Configuration

Create `/etc/nginx/sites-available/amarktai.conf`:

```nginx
# Amarktai Network - Production Configuration

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ws_limit:10m rate=5r/s;

# WebSocket connection upgrade
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend - Serve React build
    root /var/www/amarktai/frontend/build;
    index index.html;

    # Frontend routing (React Router)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API (with rate limiting)
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket endpoints (with rate limiting)
    location ~ ^/(api/ws|ws/decisions)$ {
        limit_req zone=ws_limit burst=5 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Server-Sent Events (SSE)
    location /api/realtime/events {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE specific settings
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        chunked_transfer_encoding on;
        
        # NGINX specific for SSE
        add_header X-Accel-Buffering no;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Logs
    access_log /var/log/nginx/amarktai-access.log;
    error_log /var/log/nginx/amarktai-error.log;
}
```

### 5.2 Enable Nginx Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/amarktai.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## Part 6: SSL/TLS with Let's Encrypt

### 6.1 Install Certbot

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
```

### 6.2 Obtain SSL Certificate

```bash
# Get certificate (replace yourdomain.com)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certbot will:
# 1. Verify domain ownership
# 2. Issue certificate
# 3. Update Nginx config automatically
```

### 6.3 Test Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot auto-renewal is configured via cron/systemd
```

---

## Part 7: Post-Deployment Verification

### 7.1 Health Checks

```bash
# Backend health
curl https://yourdomain.com/api/system/ping

# Platform info
curl https://yourdomain.com/api/system/platforms

# Health check
curl https://yourdomain.com/api/health/ping
```

### 7.2 Create Admin User

```bash
# From backend directory
python3 -c "
from motor.motor_asyncio import AsyncIOMotorClient
from auth import get_password_hash
import asyncio
import os

async def create_admin():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.getenv('DB_NAME', 'amarktai_trading')]
    
    admin_user = {
        'id': 'admin',
        'first_name': 'Admin',
        'email': 'admin@yourdomain.com',
        'password_hash': get_password_hash('CHANGE_THIS_PASSWORD'),
        'currency': 'ZAR',
        'is_admin': True,
        'role': 'admin',
        'created_at': '2026-01-14T00:00:00Z'
    }
    
    await db.users.insert_one(admin_user)
    print('✅ Admin user created')

asyncio.run(create_admin())
"
```

### 7.3 Test Frontend

1. Open browser to `https://yourdomain.com`
2. Register a new user or login with admin
3. Verify dashboard loads without errors
4. Check browser console for errors (F12)

---

## Part 8: Monitoring & Logs

### 8.1 View Backend Logs

```bash
# Real-time logs
sudo journalctl -u amarktai-backend -f

# Last 100 lines
sudo journalctl -u amarktai-backend -n 100

# Specific log files
sudo tail -f /var/log/amarktai-backend.log
sudo tail -f /var/log/amarktai-backend-error.log
```

### 8.2 View Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/amarktai-access.log

# Error logs
sudo tail -f /var/log/nginx/amarktai-error.log
```

### 8.3 MongoDB Logs

```bash
sudo journalctl -u mongod -f
```

---

## Part 9: Enable Trading (Gradual Rollout)

### 9.1 Enable Paper Trading

```bash
# Update backend/.env
ENABLE_TRADING=true
ENABLE_CCXT=true

# Restart backend
sudo systemctl restart amarktai-backend
```

### 9.2 Enable Schedulers & Autonomous Features

```bash
# Update backend/.env
ENABLE_SCHEDULERS=true

# Restart backend
sudo systemctl restart amarktai-backend
```

### 9.3 Enable Autopilot (Full Autonomous)

```bash
# Update backend/.env
ENABLE_AUTOPILOT=true

# Restart backend
sudo systemctl restart amarktai-backend
```

---

## Part 10: Backup & Recovery

### 10.1 Database Backup

```bash
# Backup MongoDB
mongodump --uri="mongodb://localhost:27017/amarktai_trading" --out=/backup/amarktai-$(date +%Y%m%d)

# Automate with cron (daily at 3 AM)
0 3 * * * mongodump --uri="mongodb://localhost:27017/amarktai_trading" --out=/backup/amarktai-$(date +\%Y\%m\%d) >> /var/log/mongodb-backup.log 2>&1
```

### 10.2 Restore Database

```bash
# Restore from backup
mongorestore --uri="mongodb://localhost:27017" /backup/amarktai-20260114/
```

---

## Part 11: Scaling & Performance

### 11.1 Backend Scaling

```bash
# Increase workers in systemd service
# Edit /etc/systemd/system/amarktai-backend.service
ExecStart=/var/www/amarktai/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000 --workers 8

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart amarktai-backend
```

### 11.2 MongoDB Optimization

```bash
# Enable MongoDB authentication
# Create indexes for performance
mongo amarktai_trading
db.bots.createIndex({"user_id": 1, "status": 1})
db.trades.createIndex({"user_id": 1, "timestamp": -1})
db.trades.createIndex({"bot_id": 1, "timestamp": -1})
```

---

## Part 12: Troubleshooting

### Common Issues

#### Backend won't start
```bash
# Check logs
sudo journalctl -u amarktai-backend -n 50

# Check MongoDB connection
sudo systemctl status mongod

# Verify .env file exists and has correct permissions
ls -la /var/www/amarktai/backend/.env
```

#### Frontend shows blank page
```bash
# Check Nginx logs
sudo tail -f /var/log/nginx/amarktai-error.log

# Verify build exists
ls -la /var/www/amarktai/frontend/build/

# Check browser console (F12)
```

#### WebSocket connection fails
```bash
# Check Nginx WebSocket configuration
sudo nginx -t

# Verify backend is listening
sudo netstat -tlnp | grep 8000

# Check browser network tab for WS handshake
```

#### 404 errors on API calls
```bash
# Verify backend is running
curl http://localhost:8000/api/system/ping

# Check Nginx proxy configuration
sudo nginx -t
```

---

## Part 13: Security Checklist

- [ ] Strong JWT_SECRET generated (`openssl rand -hex 32`)
- [ ] MongoDB authentication enabled
- [ ] SSL/TLS certificate installed and valid
- [ ] Firewall configured (ufw/iptables)
- [ ] MongoDB port 27017 restricted to localhost only
- [ ] `.env` file permissions set to 600
- [ ] Admin user password changed from default
- [ ] Rate limiting enabled in Nginx
- [ ] Security headers configured in Nginx
- [ ] Logs are being written and rotated
- [ ] Backups are automated and tested
- [ ] SMTP credentials secured (app-specific password)

---

## Part 14: Quick Reference

### Restart Services
```bash
sudo systemctl restart amarktai-backend
sudo systemctl reload nginx
sudo systemctl restart mongod
```

### View Logs
```bash
sudo journalctl -u amarktai-backend -f
sudo tail -f /var/log/nginx/amarktai-error.log
```

### Update Code
```bash
cd /var/www/amarktai
sudo -u www-data git pull
sudo systemctl restart amarktai-backend
```

### Emergency Stop
```bash
# Stop trading immediately
sudo systemctl stop amarktai-backend

# Or via API
curl -X POST https://yourdomain.com/api/emergency-stop/emergency-stop
```

---

## Support

For issues, contact: admin@yourdomain.com

**Documentation:** https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment

---

**Last Updated:** 2026-01-14 14:50 UTC
**Version:** 1.0.0

---

## ✅ GO-LIVE CHECKLIST

### Fresh Deployment → Paper Trading → Keys Saved → Live Trading Enabled

This checklist provides the exact steps to go from a fresh deployment to a fully operational production system.

---

### Phase 1: Fresh Deployment (30-60 minutes)

**Prerequisites:**
- [ ] Ubuntu 24.04 VPS with SSH access
- [ ] Domain name pointed to server IP
- [ ] MongoDB installed and running
- [ ] Python 3.11+ and Node.js 20+ installed

**Steps:**

1. **Clone and Setup Repository**
   ```bash
   cd /var/www
   sudo git clone https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment.git amarktai
   cd amarktai
   ```

2. **Configure Environment Variables**
   ```bash
   cd backend
   cp .env.example .env
   
   # Generate JWT secret
   openssl rand -hex 32
   
   # Edit .env and set:
   nano .env
   ```
   
   **Required Settings:**
   - `JWT_SECRET=<generated-secret>`
   - `MONGO_URL=mongodb://localhost:27017`
   - `DB_NAME=amarktai_trading`
   - `ENABLE_CCXT=true` (safe - needed for market data)
   - `ENABLE_TRADING=false` (start disabled)
   - `ENABLE_LIVE_TRADING=false` (start disabled)
   - `ENABLE_AUTOPILOT=false` (start disabled)
   - `ENABLE_SELF_LEARNING=true` (safe - improves strategy)
   - `ENABLE_SELF_HEALING=true` (safe - protects against losses)
   - `ENABLE_SCHEDULERS=false` (start disabled)

3. **Install Backend Dependencies**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Install Frontend Dependencies**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

5. **Setup systemd Service**
   ```bash
   sudo cp /var/www/amarktai/deployment/amarktai-api.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable amarktai-api
   sudo systemctl start amarktai-api
   ```

6. **Setup Nginx**
   ```bash
   sudo cp /var/www/amarktai/deployment/nginx/amarktai.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/amarktai.conf /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

7. **Setup SSL (Let's Encrypt)**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

8. **Run Verification Script**
   ```bash
   cd /var/www/amarktai
   python3 scripts/verify_production_ready.py
   # MUST show: 🎉 ALL CHECKS PASSED - Production Ready
   ```

**Expected Result:**
- ✅ Backend running on port 8001 (check: `curl http://localhost:8001/api/health/ping`)
- ✅ Frontend accessible via https://yourdomain.com
- ✅ All verification tests passing
- ✅ No API keys required for market data
- ✅ Paper trading ready (but not yet enabled)

---

### Phase 2: Enable Paper Trading (5-10 minutes)

**Goal:** Enable paper trading to test the system with simulated funds.

1. **Enable Paper Trading**
   ```bash
   cd /var/www/amarktai/backend
   nano .env
   ```
   
   **Update Settings:**
   ```bash
   ENABLE_TRADING=true        # Enable trading execution
   ENABLE_CCXT=true          # Already true
   ENABLE_SCHEDULERS=false   # Keep disabled for now
   ```

2. **Restart Backend**
   ```bash
   sudo systemctl restart amarktai-api
   sudo systemctl status amarktai-api
   ```

3. **Register User via Dashboard**
   - Open https://yourdomain.com
   - Click "Register"
   - Fill in details and register
   - Login with your credentials

4. **Create Paper Trading Bot**
   - Go to "Bots" section
   - Click "Create Bot"
   - Set:
     - Name: "My First Paper Bot"
     - Initial Capital: R1000
     - Risk Mode: Safe
     - Exchange: Luno
     - Trading Mode: **Paper** (default)
   - Click "Create"

5. **Verify Paper Trading**
   ```bash
   # Check logs
   sudo journalctl -u amarktai-api -f | grep "Paper"
   
   # Should see paper trades executing
   ```

6. **Monitor Dashboard**
   - Go to "Dashboard" → "Overview"
   - Should see:
     - Active bots: 1
     - Mode: Paper Trading
     - Trades executing (may take 5-15 min for first trade)
     - No "luno requires apiKey" errors in logs

**Expected Result:**
- ✅ Paper trading bot created
- ✅ Paper trades executing and recording to DB
- ✅ Dashboard shows paper trading activity
- ✅ No crashes or API key errors
- ✅ System running with NO exchange API keys

---

### Phase 3: Save Exchange API Keys (10-15 minutes)

**Goal:** Connect real exchange accounts for live market data and future live trading.

**Recommended Exchange:** Luno (South African, ZAR support)

1. **Get Luno API Keys**
   - Login to https://www.luno.com
   - Go to Settings → API Keys
   - Create new API key with permissions:
     - ✅ View balance
     - ✅ Place orders
     - ✅ Cancel orders
     - ❌ Withdraw (NOT needed, keep disabled)
   - Copy API Key and Secret

2. **Save Keys via Dashboard**
   - Login to dashboard
   - Go to "Settings" → "API Keys"
   - Select "Luno"
   - Paste:
     - API Key: `<your-luno-key>`
     - API Secret: `<your-luno-secret>`
   - Click "Save"
   - Should see: "✅ Saved Luno API key"

3. **Test API Keys**
   - Click "Test Connection" next to saved key
   - Should see: "✅ Luno connection successful"
   - If error: "❌ Invalid credentials" - re-check keys

4. **Verify Key Save in Backend**
   ```bash
   # Check logs
   sudo journalctl -u amarktai-api -n 50 | grep "API key"
   
   # Should see: "✅ Saved LUNO API key for user..."
   ```

**Expected Result:**
- ✅ Luno API keys saved and encrypted in database
- ✅ Test connection successful
- ✅ Dashboard shows "Saved & Tested ✅" status
- ✅ No plaintext keys in logs or database
- ✅ Keys work for both market data and future trading

**Optional: Add More Exchanges**
- Repeat steps for Binance, KuCoin, etc.
- Each exchange requires separate API keys

---

### Phase 4: Monitor & Optimize Paper Trading (7 days)

**Goal:** Let paper trading run for 7 days to build performance history.

**Required for Live Trading:**
- Minimum 7 days of paper trading
- Minimum 25 trades executed
- Minimum 52% win rate
- Minimum 3% total profit

1. **Monitor Performance Daily**
   ```bash
   # View bot performance
   curl -H "Authorization: Bearer <your-token>" https://yourdomain.com/api/bots
   
   # View recent trades
   curl -H "Authorization: Bearer <your-token>" https://yourdomain.com/api/trades/recent
   ```

2. **Check Live Eligibility**
   - Dashboard → "Settings" → "Live Trading"
   - Should show current status:
     - Days elapsed: X/7
     - Total trades: Y/25
     - Win rate: Z%
     - Profit: R###

3. **Enable Autonomous Features (Optional)**
   ```bash
   cd /var/www/amarktai/backend
   nano .env
   ```
   
   **Update Settings:**
   ```bash
   ENABLE_SCHEDULERS=true     # Enable background jobs
   ENABLE_SELF_LEARNING=true  # Already true
   ENABLE_SELF_HEALING=true   # Already true
   ```
   
   ```bash
   sudo systemctl restart amarktai-api
   ```

**Expected Result:**
- ✅ Paper trades executing consistently
- ✅ No crashes or errors
- ✅ Performance metrics improving
- ✅ System stable for 7 days

---

### Phase 5: Enable Live Trading (CAREFUL!)

**DANGER:** This uses REAL FUNDS. Proceed with extreme caution.

**Prerequisites:**
- [ ] 7+ days of successful paper trading
- [ ] 52%+ win rate achieved
- [ ] 3%+ profit achieved
- [ ] 25+ trades executed
- [ ] Exchange account funded
- [ ] Risk guardrails configured

1. **Check Eligibility**
   ```bash
   curl -H "Authorization: Bearer <your-token>" \
     https://yourdomain.com/api/system/live-eligibility
   
   # Should return: "eligible": true
   ```

2. **Request Live Trading Approval**
   - Dashboard → "Settings" → "Live Trading"
   - Click "Request Live Trading"
   - Should see eligibility status
   - If eligible: "✅ Approved for live trading"
   - If not: Review reasons and continue paper trading

3. **Enable Live Trading Flag**
   ```bash
   cd /var/www/amarktai/backend
   nano .env
   ```
   
   **Update Settings:**
   ```bash
   ENABLE_LIVE_TRADING=true   # ⚠️ DANGER: Enables live trading
   ```
   
   ```bash
   sudo systemctl restart amarktai-api
   ```

4. **Switch Bot to Live Mode (Double Confirmation)**
   - Dashboard → "Bots" → Select bot
   - Click "Promote to Live"
   - **Confirmation Dialog 1:** Review performance stats
   - **Confirmation Dialog 2:** Type "I UNDERSTAND" or OTP
   - Bot switches to LIVE mode

5. **Monitor Live Trading Closely**
   ```bash
   # Watch logs in real-time
   sudo journalctl -u amarktai-api -f | grep "LIVE"
   
   # Should see: "💹 LIVE TRADE: ..." entries
   ```

6. **Set Risk Limits (CRITICAL)**
   - Dashboard → "Settings" → "Risk Management"
   - Set:
     - Max position size: 5-10% of capital
     - Max daily loss: 5%
     - Max open trades: 3-5
     - Circuit breaker: Enable

**Expected Result:**
- ✅ Live trading flag enabled
- ✅ Bot promoted to live mode with double confirmation
- ✅ Real trades executing on exchange
- ✅ Risk guardrails active
- ✅ Emergency stop accessible

---

### Phase 6: Emergency Stop (If Needed)

**If anything goes wrong:**

1. **Via Dashboard:**
   - Dashboard → "Emergency Stop" button (top right)
   - Click → Confirm → All trading STOPS

2. **Via CLI:**
   ```bash
   curl -X POST -H "Authorization: Bearer <your-token>" \
     https://yourdomain.com/api/system/emergency-stop
   ```

3. **Via systemd (Nuclear option):**
   ```bash
   sudo systemctl stop amarktai-api
   ```

4. **Resume After Fix:**
   ```bash
   # Resume trading
   curl -X POST -H "Authorization: Bearer <your-token>" \
     https://yourdomain.com/api/system/emergency-stop/disable
   
   # Restart service
   sudo systemctl restart amarktai-api
   ```

**Expected Result:**
- ✅ All trading stops IMMEDIATELY
- ✅ Open positions remain (not auto-closed)
- ✅ System safe and stable
- ✅ Can resume when ready

---

### Ongoing Maintenance

**Daily:**
- [ ] Check dashboard for bot performance
- [ ] Review recent trades
- [ ] Monitor system logs for errors

**Weekly:**
- [ ] Review profit/loss reports
- [ ] Check for system updates
- [ ] Verify backups are running

**Monthly:**
- [ ] Review and optimize bot strategies
- [ ] Update dependencies if needed
- [ ] Review risk limits and adjust

**Commands:**
```bash
# Check system health
python3 /var/www/amarktai/scripts/verify_go_live.py

# View recent logs
sudo journalctl -u amarktai-api -n 100

# Restart if needed
sudo systemctl restart amarktai-api

# Update code
cd /var/www/amarktai
sudo git pull origin main
sudo systemctl restart amarktai-api
```

---

### Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| "luno requires apiKey" error | ✅ FIXED: System uses public market data, no keys required |
| "NoneType round" crash | ✅ FIXED: All numeric values sanitized before rounding |
| Prices endpoint returns 0 | Check if Luno API is accessible, ensure ENABLE_CCXT=true |
| Paper trades not executing | Check ENABLE_TRADING=true, verify logs for errors |
| Can't save API keys | Verify JWT token valid, check auth endpoint `/api/auth/me` |
| Live trading not working | Check ENABLE_LIVE_TRADING=true, verify eligibility first |
| Emergency stop not working | Try CLI or systemd stop as backup |

---

**Support & Updates:**
- GitHub: https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment
- Documentation: See `docs/` folder
- Issues: Open GitHub issue or contact admin

**Last Updated:** 2026-01-18
**Version:** 2.0.0 (Production-Ready)

