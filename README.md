# Amarktai Network - Production Trading Platform

**Production-grade, plug-and-play deployment** for Ubuntu 24.04 with systemd + nginx. Clean installation with Python 3.12, Node 20, and **modular dependencies**.

---

## 🚀 Install in 5 Minutes (Ubuntu 24.04)

### Prerequisites
- Ubuntu 24.04 LTS
- Root or sudo access
- 2GB RAM minimum

### Step 1: Install MongoDB (Docker)
```bash
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo docker run -d --name amarktai-mongo --restart always \
  -p 127.0.0.1:27017:27017 \
  -v /var/amarktai/mongodb:/data/db mongo:7
```

### Step 2: Clone and Install
```bash
sudo mkdir -p /var/amarktai
cd /var/amarktai
sudo git clone https://github.com/amarktainetwork-blip/Amarktai-Network---Deployment.git app
cd app
python3.12 -m venv /var/amarktai/venv
source /var/amarktai/venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements/base.txt
```

### Step 3: Configure
```bash
cp backend/.env.example backend/.env
# Edit .env with your values:
# JWT_SECRET=$(openssl rand -hex 32)
# ADMIN_PASSWORD=$(openssl rand -base64 24)
# MONGO_URL=mongodb://127.0.0.1:27017
nano backend/.env
```

### Step 4: Run Sanity Check
```bash
bash scripts/sanity_check.sh
```

### Step 5: Start Service
```bash
sudo bash tools/systemd_install.sh
sudo systemctl status amarktai-api
```

### Step 6: Verify
```bash
curl http://127.0.0.1:8000/api/health/ping
# Expected: {"status":"healthy","db":"connected","timestamp":"..."}
```

### Optional: Setup Nginx Reverse Proxy
```bash
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/amarktai > /dev/null <<'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/amarktai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🎯 New: Modular Requirements System

Dependencies are now split into optional modules for faster, conflict-free installations:

- **`backend/requirements/base.txt`** - Core API (FastAPI, MongoDB, Auth) - **Required**
- **`backend/requirements/trading.txt`** - CCXT exchange integration - *Optional*
- **`backend/requirements/ai.txt`** - ML, transformers, LangChain - *Optional*
- **`backend/requirements/agents.txt`** - Fetch.ai uAgents - *Optional, conflicts with AI*
- **`backend/requirements/dev.txt`** - Testing, linting - *Development only*

**Installation time:** 30 seconds (base) vs 5 minutes (all features)

See **[reports/dependency-audit.md](reports/dependency-audit.md)** for complete details.

## 🚀 Quick Start (Modular Installation)

### Prerequisites
- Ubuntu 24.04 LTS
- Root or sudo access
- 2GB RAM minimum (4GB recommended)
- MongoDB 7+ (Docker or native)

### Step 1: Clone Repository

```bash
# Clone to /var/amarktai/app
sudo mkdir -p /var/amarktai
cd /var/amarktai
sudo git clone https://github.com/amarktainetwork-blip/Amarktai-Network---Deployment.git app
cd app
```

### Step 2: Choose Your Installation

#### Option A: Minimal (API Only - 30 seconds)
```bash
cd backend
python3.12 -m venv /var/amarktai/venv
source /var/amarktai/venv/bin/activate
pip install --upgrade pip
pip install -r requirements/base.txt
```

**Use case:** Testing, development, API-only deployments
**Packages:** ~40 packages, ~50MB
**Features:** Health endpoints, OpenAPI, authentication, scheduling

#### Option B: With Trading (1 minute)
```bash
pip install -r requirements/base.txt -r requirements/trading.txt
```

**Use case:** Trading functionality without AI
**Additional:** CCXT, exchange integration

#### Option C: With AI (3 minutes)
```bash
pip install -r requirements/base.txt -r requirements/ai.txt
```

**Use case:** AI features without trading
**Additional:** NumPy, SciPy, transformers, LangChain, OpenAI

#### Option D: Full Stack (3.5 minutes)
```bash
pip install -r requirements/base.txt \
            -r requirements/trading.txt \
            -r requirements/ai.txt
```

**Use case:** Complete production deployment
**Everything:** Trading + AI + ML features

#### Option E: Development (4 minutes)
```bash
pip install -r requirements/base.txt \
            -r requirements/trading.txt \
            -r requirements/ai.txt \
            -r requirements/dev.txt
```

**Use case:** Local development
**Additional:** pytest, black, flake8, mypy

### Step 3: Configure Environment

```bash
# Copy and edit .env file
cp backend/.env.example backend/.env
nano backend/.env
```

**Required variables:**
```bash
# Security (MUST change!)
JWT_SECRET=<run: openssl rand -hex 32>
ADMIN_PASSWORD=<run: openssl rand -base64 24>

# Database
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=amarktai_trading

# AI (if using ai.txt)
OPENAI_API_KEY=sk-your-key-here
```

**Feature flags (control what runs):**
```bash
# Start with safe defaults
ENABLE_TRADING=false      # Requires trading.txt
ENABLE_AI=false           # Requires ai.txt  
ENABLE_AUTOPILOT=false    # Autonomous trading
ENABLE_CCXT=true          # Price data (safe, requires trading.txt)
ENABLE_AGENTS=false       # Requires agents.txt
```

### Step 4: Install Systemd Service (Optional)

**Option A: Docker (Recommended)**
```bash
sudo apt-get install docker.io
sudo docker run -d \
  --name amarktai-mongo \
  -p 127.0.0.1:27017:27017 \
  -v /var/amarktai/mongodb:/data/db \
  --restart always \
  mongo:7
```

**Option B: Native Installation**
```bash
# See reports/deployment-notes.md for full MongoDB setup
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
# ... (see full guide in deployment-notes.md)
```

### Step 5: Install Systemd Service

```bash
# Install and start systemd service
sudo bash tools/systemd_install.sh
```

This script:
- ✅ Creates systemd service file
- ✅ Enables auto-start on boot
- ✅ Starts service immediately
- ✅ Configures security hardening

### Step 6: Verify Deployment

```bash
# Run comprehensive health check
bash tools/health_check.sh
```

Checks:
- ✅ System dependencies (Python 3.12, Node 20)
- ✅ Directory structure
- ✅ Systemd service status
- ✅ API endpoints (/api/health/ping)
- ✅ OpenAPI routes
- ✅ No errors in logs

## Production Boot Verification

After deployment, verify the backend boots correctly:

```bash
# 1. Test database module directly
cd /var/amarktai/app/backend
source /var/amarktai/venv/bin/activate
python tools/selftest_boot.py

# 2. Test health endpoint
curl http://127.0.0.1:8000/api/health/ping

# Expected response:
# {"status":"healthy","db":"connected","timestamp":"2025-12-30T06:00:00.000000Z"}
```

### Common Issues

**AttributeError: module 'database' has no attribute 'wallet_balances'**
- Fix: Ensure `database.py` has wallet_balances and capital_injections aliases defined
- Run: `python tools/selftest_boot.py` to verify

**Health endpoint returns 503**
- If DB is connected but health returns 503, check optional services are not blocking
- Only database connectivity should affect health status

**Systemd restart loop**
- Check logs: `journalctl -u amarktai-backend -n 50`
- Look for ImportError or AttributeError
- Run selftest to identify missing attributes

### Step 7: Frontend Setup (Optional)

```bash
# Build frontend for production
sudo bash tools/frontend_setup.sh
```

This installs Node.js 20 and builds the React frontend.

### Step 8: Configure Nginx (Optional)

```nginx
# /etc/nginx/sites-available/amarktai
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/amarktai/app/frontend/build;
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/amarktai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🚀 Quick Start (VPS Deployment)

### Prerequisites
- Ubuntu 24.04 LTS
- Python 3.12 (recommended) or 3.11+
- MongoDB 6.0+ (or 7.0+ recommended)
- systemd
- 2GB RAM minimum (4GB recommended)

### Fresh VPS Installation (Step-by-Step)

#### 1. Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 if not present
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install MongoDB (Docker method - recommended)
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo docker run -d \
  --name amarktai-mongo \
  --restart always \
  -p 127.0.0.1:27017:27017 \
  -v /var/amarktai/mongodb:/data/db \
  mongo:7
```

#### 2. Clone Repository
```bash
# Create application directory
sudo mkdir -p /var/amarktai
cd /var/amarktai

# Clone repository
sudo git clone https://github.com/amarktainetwork-blip/Amarktai-Network---Deployment.git app
cd app

# Set permissions
sudo chown -R $USER:$USER /var/amarktai
```

#### 3. Setup Python Environment
```bash
# Create virtual environment
python3.12 -m venv /var/amarktai/venv

# Activate virtual environment
source /var/amarktai/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies (this must succeed with no conflicts)
cd /var/amarktai/app/backend
pip install -r requirements.txt

# Verify installation
pip check
# Should output: "No broken requirements found."
```

#### 4. Configure Environment
```bash
# Create .env file
cp /var/amarktai/app/backend/.env.example /var/amarktai/app/backend/.env

# Edit configuration
nano /var/amarktai/app/backend/.env
```

**Required environment variables:**
```bash
# Database
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=amarktai_trading

# Security (CHANGE THESE!)
JWT_SECRET=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 24)

# Feature Flags (safe defaults - all disabled)
ENABLE_TRADING=0
ENABLE_AUTOPILOT=0
ENABLE_CCXT=0
ENABLE_SCHEDULERS=0

# Optional: AI features
# OPENAI_API_KEY=sk-your-key-here
```

#### 5. Run Preflight Checks
```bash
# Must pass before starting server
cd /var/amarktai/app/backend
python -m preflight

# Expected output:
# ✅ Database connected and collections initialized
# ✅ Server imported successfully
# ✅ All required auth functions present
# 🎉 PREFLIGHT PASSED - Server can start safely
```

#### 6. Test Manual Start
```bash
# Start server manually to verify
cd /var/amarktai/app/backend
uvicorn server:app --host 127.0.0.1 --port 8000

# In another terminal, test health endpoint
curl http://127.0.0.1:8000/api/health/ping
# Should return: {"status":"healthy","timestamp":"..."}

# Check port binding
ss -tlnp | grep 8000
# Should show: LISTEN 0 4096 127.0.0.1:8000
```

#### 7. Setup Systemd Service
```bash
# Create systemd service file
sudo tee /etc/systemd/system/amarktai-backend.service > /dev/null <<EOF
[Unit]
Description=Amarktai Network Backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/amarktai/app/backend
Environment="PATH=/var/amarktai/venv/bin"
ExecStart=/var/amarktai/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable amarktai-backend
sudo systemctl start amarktai-backend

# Check status
sudo systemctl status amarktai-backend
# Should show: Active: active (running)

# View logs
sudo journalctl -u amarktai-backend -f
```

#### 8. Setup Nginx (Optional - for production)
```bash
# Install nginx
sudo apt install -y nginx

# Create nginx configuration
sudo tee /etc/nginx/sites-available/amarktai > /dev/null <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /var/amarktai/app/frontend/build;
        try_files $uri /index.html;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/amarktai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Common Failures & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: cannot import name 'X'` | Missing export in database.py | All collections now exported, update to latest |
| `ModuleNotFoundError: No module named 'motor'` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `AttributeError: 'NoneType' object has no attribute 'add_job'` | Autopilot scheduler not initialized | Fixed - scheduler created in __init__ |
| `RuntimeWarning: coroutine 'stop' was never awaited` | Async shutdown not awaited | Fixed - all stop() calls properly awaited |
| Server doesn't bind to port 8000 | Import-time crash before uvicorn starts | Run `python -m backend.preflight` to diagnose |
| `ss -tlnp` shows no process on 8000 | Systemd restart loop | Check logs: `journalctl -u amarktai-backend -n 100` |
| `ResolutionImpossible` during pip install | Dependency conflicts | Fixed - single pycares==4.11.0 pin |
| `Database connection failed` | MongoDB not running | Start MongoDB: `sudo systemctl start docker` |

### Validation Checklist

After deployment, verify all of these:

```bash
# ✅ 1. Dependencies installed without conflicts
pip check
# Output: "No broken requirements found."

# ✅ 2. Database connection works
python -c "import asyncio; import database; asyncio.run(database.connect()); print('✅ DB OK')"

# ✅ 3. Server imports successfully
python -c "import server; print('✅ Server imports OK')"

# ✅ 4. Preflight passes
python -m preflight
# Output: "🎉 PREFLIGHT PASSED"

# ✅ 5. Port 8000 listening
ss -tlnp | grep 8000
# Output: "LISTEN ... 127.0.0.1:8000"

# ✅ 6. Health endpoint responds
curl -f http://127.0.0.1:8000/api/health/ping
# Output: {"status":"healthy","timestamp":"..."}

# ✅ 7. Systemd service running
sudo systemctl is-active amarktai-backend
# Output: "active"
```

**If all checks pass:** ✅ Deployment successful!

**If any check fails:** See Common Failures table above or check logs with `journalctl -u amarktai-backend -n 100`

### Quick Troubleshooting

```bash
# View real-time logs
sudo journalctl -u amarktai-backend -f

# Restart service
sudo systemctl restart amarktai-backend

# Check what's using port 8000
sudo lsof -i :8000

# Test MongoDB connection
docker exec amarktai-mongo mongosh --eval "db.runCommand({ ping: 1 })"

# Re-run preflight
cd /var/amarktai/app/backend
source /var/amarktai/venv/bin/activate
python -m preflight
```

## 📚 Documentation

- **[Backend Dependencies Audit](reports/backend-deps-audit.md)** - Python 3.12 fixes
- **[Frontend Dependencies Audit](reports/frontend-deps-audit.md)** - Node 20 + React 19
- **[Deployment Notes](reports/deployment-notes.md)** - Complete deployment guide
- **[Systemd Notes](reports/systemd-notes.md)** - Service management

## 🔧 Service Management

```bash
# View status
sudo systemctl status amarktai-api

# View logs (live)
sudo journalctl -u amarktai-api -f

# Restart
sudo systemctl restart amarktai-api

# Stop
sudo systemctl stop amarktai-api

# Start
sudo systemctl start amarktai-api
```

## 🛡️ Feature Flags

Feature flags allow safe gradual enablement:

### Phase 1: Health Check (Day 1)
```bash
ENABLE_TRADING=false
ENABLE_AUTOPILOT=false
ENABLE_CCXT=true  # Price data only
```

- Verify service starts
- Test health endpoints
- Dashboard loads
- Price data works

### Phase 2: Paper Trading (Day 2-7)
```bash
ENABLE_TRADING=true
ENABLE_AUTOPILOT=false
ENABLE_CCXT=true
```

- Test paper trades
- Monitor logs
- Verify bot creation
- No real money at risk

### Phase 3: Autonomous Management (Day 7+)
```bash
ENABLE_TRADING=true
ENABLE_AUTOPILOT=true
ENABLE_CCXT=true
```

- Enable reinvestment
- Monitor autonomous actions
- Test bot spawning
- Review capital allocation

### Phase 4: Live Trading (After Validation)
- Configure exchange API keys
- Enable per-bot live trading (requires 7-day paper training)
- Start with small capital
- Monitor closely

## 🔒 Security Best Practices

1. **Change default secrets:**
   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   ADMIN_PASSWORD=$(openssl rand -base64 24)
   ```

2. **Firewall configuration:**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

3. **SSL/TLS (Let's Encrypt):**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

4. **File permissions:**
   ```bash
   sudo chmod 600 /var/amarktai/app/backend/.env
   ```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u amarktai-api -n 50

# Common issues:
# 1. .env file missing → sudo cp .env.example .env
# 2. MongoDB not running → sudo systemctl start mongod
# 3. Port 8000 in use → sudo lsof -i :8000
```

### Dependencies Failed

```bash
# Backend
cd /var/amarktai/app/backend
source /var/amarktai/venv/bin/activate
pip install -r requirements.txt

# Frontend
cd /var/amarktai/app/frontend
rm -rf node_modules
npm install
npm run build
```

### Health Check Failed

```bash
# Run with verbose output
bash tools/health_check.sh

# Manual test
curl http://127.0.0.1:8000/api/health/ping
```

## 🔄 Updates

```bash
# Pull latest code
cd /var/amarktai/app
sudo git pull

# Update backend
source /var/amarktai/venv/bin/activate
pip install -r backend/requirements.txt

# Rebuild frontend (if changed)
cd frontend && npm install && npm run build

# Restart service
sudo systemctl restart amarktai-api

# Verify
bash tools/health_check.sh
```

## ✅ What's Fixed (December 2025)

### Backend Dependencies
- ✅ NumPy version conflict (scipy <2.3 requirement)
- ✅ Huggingface hub version (<1.0 for transformers)
- ✅ Tokenizers version (<0.21 for transformers)
- ✅ Packaging version (<25 for langchain)
- ✅ Protobuf version (3.19.5-7.0 range)
- ✅ Moved uagents/cosmpy to optional requirements-ai.txt

### Frontend Dependencies  
- ✅ react-day-picker upgraded to v9 (removes date-fns conflict)
- ✅ React 19 compatibility verified
- ✅ Fixed syntax errors in WalletHub.js and WalletOverview.js
- ✅ npm install works on Node 20
- ✅ npm run build succeeds

### Backend Code Issues
- ✅ autopilot.start() now uses await (no more RuntimeWarning)
- ✅ autopilot.stop() is idempotent with try/except
- ✅ All shutdown calls wrapped in try/except (no cascade failures)
- ✅ CCXT sessions close all 3 exchanges (luno, binance, kucoin)
- ✅ Duplicate self_healing imports fixed
- ✅ Added is_admin() and require_admin() to auth.py
- ✅ Feature flags added (ENABLE_TRADING, etc.)

### Deployment
- ✅ Python 3.12 compatibility
- ✅ Node 20 compatibility
- ✅ Automated setup scripts
- ✅ Systemd service with security hardening
- ✅ Health check script
- ✅ Comprehensive documentation

## 🎯 Phase 1: Ledger-First Accounting

**Immutable ledger** for fills and events provides single source of truth for all accounting:
- ✅ **Fills Ledger**: Immutable trade execution records
- ✅ **Ledger Events**: Funding, transfers, allocations
- ✅ **Derived Metrics**: Equity, realized PnL, fees, drawdown
- ✅ **Endpoints**: `/api/portfolio/summary`, `/api/profits`, `/api/countdown/status`
- ✅ **Phase 1 Status**: Read-only + parallel write (opt-in)

See [Ledger Documentation](#ledger-first-accounting) section below for details.

## 🚀 Features

### Trading
- **Paper Trading**: 95% realistic simulation with real market data
- **Live Trading**: Real exchange orders with full risk management
- **Multi-Exchange**: Support for LUNO, Binance, KuCoin, Kraken, VALR
- **Smart Budget Allocation**: Fair distribution across bots (floor(budget/N))
- **Rate Limiting**: Exchange-aware limits to prevent bans

### Bot Management
- **Pause/Resume**: Fine-grained control over individual or all bots
- **Cooldown Periods**: Custom trade intervals (5-120 minutes)
- **Lifecycle Management**: Automatic promotion from paper to live
- **Performance Tracking**: Real-time profit, win rate, trade count

### Autonomous Systems
- **Trading Scheduler**: Continuous staggered execution (24/7)
- **Autopilot Engine**: Auto-manages capital and bot spawning
- **AI Bodyguard**: Detects and pauses rogue bots
- **Self-Healing**: Automatic error recovery
- **AI Learning**: Learns from trade performance

### Real-Time Updates
- **WebSocket**: Instant notifications for trades, profits, bot status
- **Server-Sent Events**: Live price feeds, system metrics
- **Dashboard Sync**: Multi-device real-time synchronization

## 📚 Key Files

| File/Directory | Purpose |
|----------------|---------|
| `backend/server.py` | FastAPI application with lifespan management |
| `backend/engines/trade_budget_manager.py` | Fair budget allocation per exchange |
| `backend/routes/bot_lifecycle.py` | Bot pause/resume/cooldown endpoints |
| `deployment/quick_setup.sh` | Automated setup script |
| `deployment/amarktai-api.service` | Systemd service configuration |
| `deployment/nginx-amarktai.conf` | Nginx reverse proxy config |
| `deployment/smoke_test.sh` | Health check validation |
| `DEPLOYMENT.md` | Comprehensive deployment guide |
| `.env.example` | Environment configuration template |

## 🔌 API Endpoints

### Core
- `GET /api/health/ping` - Simple health check
- `GET /api/health/indicators` - Comprehensive health
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Bots
- `GET /api/bots` - List all bots
- `POST /api/bots` - Create bot
- `POST /api/bots/{id}/start` - Start bot trading
- `POST /api/bots/{id}/pause` - Pause bot
- `POST /api/bots/{id}/resume` - Resume bot
- `POST /api/bots/{id}/stop` - Stop bot permanently
- `POST /api/bots/{id}/cooldown` - Set cooldown (5-120 min)
- `GET /api/bots/{id}/status` - Detailed status with performance
- `POST /api/bots/pause-all` - Pause all user bots
- `POST /api/bots/resume-all` - Resume all user bots

### Dashboard & Analytics
- `GET /api/overview` - Dashboard overview
- `GET /api/profits?period=daily|weekly|monthly` - Profit breakdown
- `GET /api/countdown/status` - Countdown to R1M with projections
- `GET /api/portfolio/summary` - Complete portfolio metrics
- `GET /api/analytics/pnl_timeseries` - PnL timeseries (5m-1d intervals)
- `GET /api/analytics/capital_breakdown` - Funded vs realized vs unrealized
- `GET /api/analytics/performance_summary` - Win rate, profit factor

### Trading
- `GET /api/trades/recent` - Recent trades
- `GET /api/analytics/profit-history` - Profit history
- `GET /api/prices/live` - Live crypto prices

### API Keys (Encrypted Storage)
- `POST /api/keys/test` - Test API key before saving
- `POST /api/keys/save` - Save encrypted API key
- `GET /api/keys/list` - List saved keys (masked)
- `DELETE /api/keys/{provider}` - Delete API key

### Reports
- `POST /api/reports/daily/send-test` - Send test daily report
- `POST /api/reports/daily/send-all` - Send reports to all users (admin)
- `GET /api/reports/daily/config` - Get SMTP configuration

### System
- `GET /api/system/mode` - Get trading modes
- `PUT /api/system/mode` - Update trading modes
- `WS /api/ws` - WebSocket connection
- `GET /api/realtime/events` - SSE stream

Full API reference in [DEPLOYMENT.md](DEPLOYMENT.md).

## 🔒 Security

- ✅ JWT token authentication
- ✅ Encrypted API keys in MongoDB
- ✅ Per-user isolated data
- ✅ Rate limiting per exchange
- ✅ CORS protection
- ✅ CodeQL security scanning (0 vulnerabilities)

## 📊 Monitoring

```bash
# Check service status
sudo systemctl status amarktai-api

# View logs
sudo journalctl -u amarktai-api -f

# Run smoke tests
./deployment/smoke_test.sh
```

## 🛠️ Development

```bash
# Backend (Python)
cd backend
source venv/bin/activate
python -m uvicorn server:app --reload

# Frontend (if applicable)
cd frontend
npm install
npm run dev
```

## 📊 Ledger-First Accounting

### Phase 1: Read-Only + Parallel Write (Current)

**Status**: ✅ Implemented and deployed

#### Collections

1. **`fills_ledger`** - Immutable fill records
   - `fill_id`, `user_id`, `bot_id`
   - `exchange`, `symbol`, `side`, `qty`, `price`
   - `fee`, `fee_currency`
   - `timestamp`, `order_id`, `client_order_id`, `exchange_trade_id`
   - `is_paper` flag

2. **`ledger_events`** - Funding and allocation events
   - `event_id`, `user_id`, `bot_id`
   - `event_type` (funding, transfer, allocation, circuit_breaker)
   - `amount`, `currency`, `timestamp`
   - `description`, `metadata`

#### Endpoints

**Read-Only** (Phase 1):
```bash
# Portfolio summary (from ledger)
GET /api/portfolio/summary
# Returns: equity, realized_pnl, unrealized_pnl, fees_total, drawdown

# Profit time series
GET /api/profits?period=daily&limit=30
# Returns: Time series of profits by period

# Countdown to target
GET /api/countdown/status?target=1000000
# Returns: Equity-based projection to R1M goal

# Query fills
GET /api/ledger/fills?bot_id=xxx&since=2025-01-01T00:00:00Z&limit=100

# Audit trail
GET /api/ledger/audit-trail?bot_id=xxx&limit=100
```

**Append-Only** (Safe for Phase 1):
```bash
# Record funding event
POST /api/ledger/funding
{
  "amount": 10000,
  "currency": "USDT",
  "description": "Initial capital"
}
```

#### Service API

```python
from services.ledger_service import get_ledger_service

ledger = get_ledger_service(db)

# Append fill (immutable)
fill_id = await ledger.append_fill(
    user_id="user_1",
    bot_id="bot_1",
    exchange="binance",
    symbol="BTC/USDT",
    side="buy",
    qty=0.01,
    price=50000,
    fee=0.5,
    fee_currency="USDT",
    timestamp=datetime.utcnow(),
    order_id="order_123"
)

# Compute metrics
equity = await ledger.compute_equity(user_id)
realized_pnl = await ledger.compute_realized_pnl(user_id)
fees_paid = await ledger.compute_fees_paid(user_id)
current_dd, max_dd = await ledger.compute_drawdown(user_id)
```

#### Testing

```bash
# Run ledger tests
cd backend
source venv/bin/activate
python -m pytest tests/test_ledger_phase1.py -v

# Tests cover:
# - Immutable fill appending
# - FIFO PnL calculation
# - Fee aggregation
# - Drawdown calculation
# - Profit series generation
# - API contract validation
```

#### Phase 1 Principles

1. **Immutable**: Fills never updated, only appended
2. **Parallel**: Works alongside existing `trades` collection
3. **Opt-in**: New code uses ledger, old code unaffected
4. **Read-only**: Endpoints are safe to deploy
5. **Deterministic**: Math is reproducible and testable

#### Ledger Integration Points

The following systems now use ledger as single source of truth:

1. **Autopilot Reinvestment**: Uses `compute_realized_pnl()` and `compute_fees_paid()` for accurate profit calculation
2. **Circuit Breaker**: Uses `compute_drawdown()` for real-time drawdown monitoring
3. **Daily Reports**: Uses ledger metrics for email reports with fallback
4. **Dashboard**: Portfolio summary endpoint sources from ledger
5. **AI Commands**: Portfolio display uses ledger data

## 🛡️ Order Pipeline & Execution Guardrails

### 4-Gate System

All orders pass through a unified pipeline with these gates:

1. **Idempotency Gate**
   - Prevents duplicate order submissions
   - Uses unique `idempotency_key` with database constraint
   - Returns existing order if key already exists

2. **Fee Coverage Gate**
   - Calculates total costs: maker/taker fees + spread + slippage + safety margin
   - Rejects orders where expected edge doesn't cover costs
   - Configurable via `MIN_EDGE_BPS`, `SAFETY_MARGIN_BPS`, `SLIPPAGE_BUFFER_BPS`

3. **Trade Limiter Gate**
   - Enforces daily limits per bot and per user
   - Burst protection (e.g., max 10 orders/10 seconds per exchange)
   - Configurable via environment variables

4. **Circuit Breaker Gate**
   - Monitors drawdown, daily loss, consecutive losses, error rate
   - Pauses or QUARANTINES bots when thresholds exceeded
   - QUARANTINED bots require manual reset

### Configuration

Set these environment variables in `.env`:

```bash
# Trade Limits
MAX_TRADES_PER_BOT_DAILY=50
MAX_TRADES_PER_USER_DAILY=500
BURST_LIMIT_ORDERS_PER_EXCHANGE=10
BURST_LIMIT_WINDOW_SECONDS=10

# Circuit Breaker Thresholds
MAX_DRAWDOWN_PERCENT=0.20  # 20%
MAX_DAILY_LOSS_PERCENT=0.10  # 10%
MAX_CONSECUTIVE_LOSSES=5
MAX_ERRORS_PER_HOUR=10

# Fee Coverage
MIN_EDGE_BPS=10  # Minimum 10 basis points edge
SAFETY_MARGIN_BPS=5
SLIPPAGE_BUFFER_BPS=10
```

### Limits Management Endpoints

Monitor and manage trading limits:

```bash
# View current configuration
GET /api/limits/config

# Check usage against limits
GET /api/limits/usage
GET /api/limits/usage?bot_id=xxx

# View quarantined bots
GET /api/limits/quarantined

# Reset quarantined bot (user action)
POST /api/limits/quarantine/reset/{bot_id}

# Check circuit breaker status
POST /api/limits/circuit-breaker/check
POST /api/limits/circuit-breaker/check?bot_id=xxx

# Get overall health
GET /api/limits/health
```

## 🤖 AI Command Router

Control your trading system via natural language chat:

### Available Commands

#### Bot Lifecycle
- `start bot <name>` - Start a bot
- `pause bot <name>` - Pause a bot
- `resume bot <name>` - Resume a paused bot
- `stop bot <name>` - Stop a bot permanently
- `pause all bots` - Pause all your bots
- `resume all bots` - Resume all paused bots

#### Emergency
- `emergency stop` - Halt all trading (requires confirmation)

#### Status & Info
- `show portfolio` - Display portfolio summary from ledger
- `show profits` - Display profit series
- `status of bot <name>` - Get bot status and metrics

#### Autopilot
- `reinvest` - Trigger reinvestment cycle (paper mode only, requires confirmation)

#### Admin (Admin-only)
- `send test report` - Send test email report

### Command Confirmation

Trading-related commands require confirmation:
1. Issue command (e.g., "emergency stop")
2. System asks for confirmation
3. Respond with "yes" or "confirm"
4. Command executes

### Real-time Feedback

Command results are sent via WebSocket with structured data:
- Success/failure status
- Human-readable message
- Structured data for UI display
- Command metadata

## 📧 Daily SMTP Reports

Automated daily email reports with:
- Yesterday's profit/loss (from ledger)
- Bot status breakdown
- Top errors and alerts
- Drawdown metrics
- Fee totals

### Configuration

```bash
# In .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
DAILY_REPORT_TIME=08:00  # 8 AM UTC
```

### Testing

```bash
# Send test report to yourself
POST /api/reports/daily/send-test

# Admin: Send to all users
POST /api/reports/daily/send-all
```

## 🔒 Paper vs Live Trading Gates

### Paper Trading Mode
- **Default mode** for new bots
- Simulates trades with real market data
- No financial risk
- Full feature access except live orders

### Live Trading Mode
- Requires 7-day paper training minimum
- Must meet promotion criteria:
  - Win rate ≥ 52%
  - Profit ≥ 3%
  - Trades ≥ 25
- API keys must be configured
- All guardrails active (limits, breaker, fee coverage)

### Promotion Process

1. Bot trades in paper mode for 7+ days
2. System checks criteria hourly
3. If eligible, bot can be promoted via:
   - `/api/bots/{id}/promote` endpoint
   - AI command: Not available (manual only for safety)
4. Bot switches to live mode with reset capital

## 🛡️ Circuit Breaker States

### Bot States

1. **Active** - Normal trading
2. **Paused** - Temporarily stopped, can resume
3. **QUARANTINED** - Critical breach, requires manual reset
4. **Stopped** - Permanently stopped

### Quarantine Triggers

Bots enter QUARANTINED state on:
- Drawdown > 20% (configurable)
- Consecutive losses ≥ 5 (configurable)

### Manual Reset

To reset a quarantined bot:
1. Investigate the cause
2. Call `POST /api/limits/quarantine/reset/{bot_id}`
3. Bot moves to PAUSED state
4. Manually resume when ready

#### Next: Phase 2 (Execution Guardrails)

Phase 2 will add:
- Order pipeline with 4 gates
- Idempotency protection
- Fee coverage checks
- Trade limiters
- Circuit breaker

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📝 License

[Your License Here]

## 🆘 Support

- **Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues**: GitHub Issues
- **Logs**: `sudo journalctl -u amarktai-api -n 100`

---

**Version**: 3.1.0 - Phase 1 (Ledger-First Accounting)  
**Last Updated**: December 2025
## 🚀 Quick Start (VPS Deployment)

This repository is production-ready with automated setup:

```bash
# 1. Clone repository
git clone YOUR_REPO_URL /var/amarktai/app
cd /var/amarktai/app

# 2. Run automated setup script
sudo bash deployment/vps-setup.sh

# 3. Configure environment variables
sudo nano /var/amarktai/app/backend/.env
# Set: OPENAI_API_KEY, JWT_SECRET, ADMIN_PASSWORD

# 4. Restart service
sudo systemctl restart amarktai-api

# 5. Access dashboard
# Open http://YOUR_SERVER_IP in browser
```

## 📋 Requirements

- **OS**: Ubuntu 24.04 LTS
- **RAM**: 2GB minimum (4GB recommended)
- **CPU**: 2 cores minimum
- **Disk**: 20GB minimum
- **Network**: Public IP address
- **Ports**: 80 (HTTP), 443 (HTTPS), 22 (SSH)

## 🏗️ Architecture

```
/var/amarktai/app/
├── backend/           # FastAPI backend (port 8000)
├── frontend/build/    # React frontend (served by nginx)
└── deployment/        # Config files
    ├── nginx/         # Nginx reverse proxy config
    └── systemd/       # Systemd service unit
```

### Path Layout

- **Backend**: `/var/amarktai/app/backend` (Python 3.11, FastAPI, MongoDB)
- **Frontend**: `/var/amarktai/app/frontend/build` (React, served by nginx)
- **MongoDB**: Docker container on `127.0.0.1:27017`
- **API**: Proxied by nginx at `/api/*`
- **WebSocket**: `/api/ws`
- **SSE (Real-time)**: `/api/realtime/*`

## 🔧 Configuration

### Environment Variables (.env)

Copy `.env.example` to `/var/amarktai/app/backend/.env` and configure:

```bash
# Database
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=amarktai

# Security (CHANGE THESE!)
JWT_SECRET=<generate with: openssl rand -hex 32>
ADMIN_PASSWORD=<generate with: openssl rand -base64 24>

# AI Features
OPENAI_API_KEY=<your OpenAI API key>

# Email (Optional)
SMTP_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=

# Trading Limits
MAX_BOTS=10
MAX_DAILY_LOSS_PERCENT=5

# Features
ENABLE_REALTIME=true
```

### Nginx Configuration

Nginx serves the frontend and proxies API requests:

- **Frontend**: Served from `/var/amarktai/app/frontend/build`
- **API**: Proxied to `http://127.0.0.1:8000/api/`
- **WebSocket**: Upgraded connections on `/api/ws`
- **SSE**: Long-polling disabled for `/api/realtime/`

Config location: `/etc/nginx/sites-available/amarktai`

### Systemd Service

Backend runs as a systemd service:

```bash
# Status
sudo systemctl status amarktai-api

# Logs
sudo journalctl -u amarktai-api -f

# Restart
sudo systemctl restart amarktai-api
```

## ✅ Verification

After setup, verify installation:

```bash
# 1. Check service is running
systemctl status amarktai-api

# 2. Check backend is listening
ss -lntp | grep :8000

# 3. Test health endpoint
curl -i http://127.0.0.1:8000/api/health/ping

# 4. Check API routes
curl http://127.0.0.1:8000/openapi.json | jq '.paths | keys[]'

# 5. Test SSE streaming
curl -N http://127.0.0.1:8000/api/realtime/events

# 6. Run smoke tests
cd /var/amarktai/app/deployment
bash smoke_test.sh
```

## 🔐 Security

### Production Checklist

- [ ] Change `JWT_SECRET` (use `openssl rand -hex 32`)
- [ ] Change `ADMIN_PASSWORD` (use `openssl rand -base64 24`)
- [ ] Set up SSL/TLS with certbot
- [ ] Configure firewall (UFW)
- [ ] Restrict MongoDB to localhost only
- [ ] Review CORS settings in backend
- [ ] Enable rate limiting (optional)
- [ ] Set up automated backups

### SSL Setup (Optional but Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 🎯 Features

### Trading Modes

- **Paper Trading**: Safe simulation with virtual funds
- **Live Trading**: Real trading with exchange APIs (requires 7-day paper training)
- **Autopilot**: Automated bot management and capital allocation

### AI Features

- **ChatOps**: Natural language dashboard control
- **Risk Management**: Automated stop-loss, take-profit, trailing stops
- **Self-Learning**: Performance analysis and strategy optimization
- **Market Intelligence**: Real-time market analysis and sentiment

### Supported Exchanges

- Luno (ZAR pairs)
- Binance
- KuCoin
- Kraken
- VALR

## 🛠️ Maintenance

### Updating

```bash
cd /var/amarktai/app
git pull
sudo systemctl restart amarktai-api
```

### Backup Database

```bash
docker exec amarktai-mongo mongodump --out /data/backup
docker cp amarktai-mongo:/data/backup ./mongo-backup-$(date +%Y%m%d)
```

### Logs

```bash
# Backend logs
sudo journalctl -u amarktai-api -n 100

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# MongoDB logs
docker logs amarktai-mongo
```

## 📚 API Documentation

Once running, access interactive API docs:

- **Swagger UI**: `http://YOUR_SERVER_IP/docs`
- **ReDoc**: `http://YOUR_SERVER_IP/redoc`
- **OpenAPI JSON**: `http://YOUR_SERVER_IP/openapi.json`

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u amarktai-api -n 50

# Check MongoDB
docker ps | grep amarktai-mongo

# Check .env file
cat /var/amarktai/app/backend/.env
```

### Frontend Not Loading

```bash
# Check nginx
sudo nginx -t
sudo systemctl status nginx

# Check build exists
ls -la /var/amarktai/app/frontend/build
```

### Database Connection Error

```bash
# Check MongoDB is running
docker ps | grep amarktai-mongo

# Test connection
docker exec amarktai-mongo mongosh --eval "db.adminCommand('ping')"
```

## 📞 Support

For issues and questions:

1. Check logs: `journalctl -u amarktai-api -f`
2. Review configuration: `.env` and nginx config
3. Run smoke tests: `bash deployment/smoke_test.sh`

## 📄 License

All rights reserved.
