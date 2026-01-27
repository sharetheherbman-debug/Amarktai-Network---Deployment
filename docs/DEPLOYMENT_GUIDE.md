# Deployment Guide - Go-Live Ready

**Version**: 1.0  
**Date**: 2026-01-27  
**Status**: ✅ PRODUCTION READY

## Overview

This guide provides step-by-step instructions for deploying the Amarktai Network trading platform to production. All go-live requirements have been met and verified.

---

## ✅ Go-Live Checklist

### API Contract ✅
- [x] `GET /api/auth/profile` - Get user profile (backward-compatible alias)
- [x] `PUT /api/auth/profile` - Update user profile
- [x] `POST /api/auth/login` - User authentication
- [x] `POST /api/auth/register` - User registration with invite code support
- [x] `GET /api/realtime/events` - SSE endpoint for real-time updates
- [x] Bot CRUD: `POST /api/bots` (create), `GET /api/bots` (list), `DELETE /api/bots/{id}` (delete)

### Frontend ✅
- [x] Build succeeds via `cd frontend && npm ci && npm run build`
- [x] Build output is deployable as static files (no dev server needed)
- [x] No console errors on load
- [x] SSE connection working

### Realtime ✅
- [x] SSE endpoint: `GET /api/realtime/events` (auth required)
- [x] Correct headers set (Cache-Control, X-Accel-Buffering)
- [x] Heartbeat events every 5 seconds
- [x] Reconnection handling
- [x] Nginx proxy compatible

### Trading Gates ✅
- [x] System doesn't trade unless `PAPER_TRADING=1` OR `LIVE_TRADING=1`
- [x] Autopilot respects gates (`AUTOPILOT_ENABLED` flag)
- [x] Paper trading includes realistic modeling (fees, slippage, spread)
- [x] Precision clamping
- [x] Funding checks prevent bots without funds

---

## 🚀 Quick Deployment

### Prerequisites
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- Node.js 20+
- MongoDB 5.0+
- Nginx (for serving frontend + reverse proxy)

### 1. Clone Repository

```bash
git clone https://github.com/sharetheherbman-debug/Amarktai-Network---Deployment.git
cd Amarktai-Network---Deployment
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Required variables:
# - JWT_SECRET (generate with: openssl rand -hex 32)
# - MONGO_URL (your MongoDB connection string)
# - DB_NAME (database name)
# - PAPER_TRADING=1 (enable paper trading)
# - LIVE_TRADING=0 (disable live trading initially)
# - AUTOPILOT_ENABLED=0 (disable autopilot initially)
```

### 3. Backend Deployment

```bash
# Install backend dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set up as systemd service (recommended)
sudo cp ../deployment/amarktai-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable amarktai-api
sudo systemctl start amarktai-api

# Check status
sudo systemctl status amarktai-api
```

### 4. Frontend Deployment

```bash
# Build frontend
cd ../frontend
npm ci
npm run build

# Deploy to web root
sudo mkdir -p /var/www/html/amarktai
sudo rsync -av build/ /var/www/html/amarktai/

# Configure Nginx (use provided config)
sudo cp ../deployment/nginx-amarktai.conf /etc/nginx/sites-available/amarktai
sudo ln -s /etc/nginx/sites-available/amarktai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Verification

```bash
# Run verification script
cd ../scripts
./verify_go_live.sh

# Test SSE endpoint
./test_sse.sh

# Test bot CRUD
./test_bots.sh
```

---

## 🔒 Security Configuration

### Required Secrets

1. **JWT_SECRET** - Generate securely:
   ```bash
   openssl rand -hex 32
   ```

2. **ENCRYPTION_KEY** (for API keys):
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **INVITE_CODE** (optional, for registration control):
   ```bash
   INVITE_CODE=YOUR_SECRET_CODE
   ```

### Database Security

```bash
# Create MongoDB user with appropriate permissions
mongo
use amarktai_trading
db.createUser({
  user: "amarktai_user",
  pwd: "STRONG_PASSWORD_HERE",
  roles: [{ role: "readWrite", db: "amarktai_trading" }]
})
```

---

## 📊 Monitoring & Health Checks

### API Health Endpoint

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-27T19:42:00Z",
  "version": "1.0.0"
}
```

### SSE Connection Test

```bash
# Test SSE endpoint (requires authentication)
./scripts/test_sse.sh
```

### Bot Operations Test

```bash
# Test bot CRUD operations
./scripts/test_bots.sh
```

### Logs

```bash
# Backend logs (systemd)
sudo journalctl -u amarktai-api -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 🔧 Configuration Reference

### Critical Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | ✅ | - | Secret key for JWT token signing |
| `MONGO_URL` | ✅ | - | MongoDB connection string |
| `DB_NAME` | ✅ | `amarktai_trading` | Database name |
| `PAPER_TRADING` | ✅ | `0` | Enable paper trading (1=enabled) |
| `LIVE_TRADING` | ✅ | `0` | Enable live trading (1=enabled) |
| `AUTOPILOT_ENABLED` | ✅ | `0` | Enable autopilot (1=enabled) |
| `INVITE_CODE` | ❌ | - | Registration invite code (optional) |
| `ENCRYPTION_KEY` | ⚠️  | - | For encrypting API keys (required if using API keys) |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for AI features |
| `SMTP_HOST` | - | SMTP server for email alerts |
| `ENABLE_REALTIME` | `true` | Enable SSE real-time events |
| `ENABLE_SCHEDULERS` | `false` | Enable background jobs |
| `MAX_BOTS` | `10` | Maximum bots per user |

---

## 🎯 Trading Mode Configuration

### Safe Deployment Path

1. **Testing Phase** (Week 1):
   ```bash
   PAPER_TRADING=1
   LIVE_TRADING=0
   AUTOPILOT_ENABLED=0
   ```

2. **Paper Trading** (Weeks 2-3):
   ```bash
   PAPER_TRADING=1
   LIVE_TRADING=0
   AUTOPILOT_ENABLED=1  # Optional: enable autopilot in paper mode
   ```

3. **Live Trading** (After successful paper trading):
   ```bash
   PAPER_TRADING=1  # Keep paper trading available
   LIVE_TRADING=1   # Enable live trading
   AUTOPILOT_ENABLED=1  # Enable autopilot with live funds
   ```

### Trading Gates Verification

The system enforces strict trading gates:

- ✅ No trading unless `PAPER_TRADING=1` OR `LIVE_TRADING=1`
- ✅ Autopilot only works if enabled AND a trading mode is active
- ✅ Paper mode uses realistic simulation (fees, slippage, spread)
- ✅ Live mode requires API keys and funding validation
- ✅ Bots cannot be created without sufficient funds (or funding plan)

---

## 🧪 Testing & Verification

### Pre-Deployment Tests

```bash
# 1. Backend syntax check
cd backend
python -m py_compile server.py
python -m py_compile routes/auth.py
python -m py_compile routes/realtime.py

# 2. Frontend build test
cd ../frontend
npm ci
npm run build

# 3. Run comprehensive verification
cd ../scripts
./verify_go_live.sh
```

### Post-Deployment Tests

```bash
# 1. Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# 2. Test SSE endpoint
./scripts/test_sse.sh

# 3. Test bot CRUD
./scripts/test_bots.sh

# 4. Test profile endpoints
TOKEN="your_jwt_token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/profile
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me
```

---

## 📝 API Endpoints Reference

### Authentication
- `POST /api/auth/register` - Register new user (requires invite code if set)
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user profile
- `GET /api/auth/profile` - Get current user profile (backward-compatible alias)
- `PUT /api/auth/profile` - Update user profile

### Bots
- `GET /api/bots` - List user's bots
- `POST /api/bots` - Create new bot (with funding validation)
- `DELETE /api/bots/{id}` - Delete bot
- `POST /api/bots/{id}/start` - Start bot
- `POST /api/bots/{id}/stop` - Stop bot

### Real-Time
- `GET /api/realtime/events` - SSE endpoint (auth required)

### System
- `GET /api/health` - Health check endpoint
- `GET /api/system/status` - System status and configuration

---

## 🔄 CI/CD Pipeline

GitHub Actions workflow automatically runs on every push:

1. **Backend Validation**
   - Python syntax check
   - Import sanity tests
   - Endpoint existence verification

2. **Frontend Build**
   - Dependency installation
   - Production build
   - Artifact verification

3. **API Contract Tests**
   - Auth endpoints
   - Bot CRUD endpoints
   - SSE endpoint

4. **Deployment Readiness**
   - Environment file checks
   - Script availability
   - Documentation completeness

---

## 📚 Architecture Documentation

See [docs/ARCHITECTURE_MAP.md](docs/ARCHITECTURE_MAP.md) for:
- Canonical module locations
- Deprecated files
- API endpoint structure
- Service layer organization
- Migration guides

---

## 🐛 Troubleshooting

### Backend Won't Start

1. **Check logs**:
   ```bash
   sudo journalctl -u amarktai-api -n 50
   ```

2. **Verify environment**:
   ```bash
   # Check if .env exists
   ls -la backend/.env
   
   # Verify MongoDB connection
   mongo $MONGO_URL
   ```

3. **Test import**:
   ```bash
   cd backend
   source .venv/bin/activate
   python -c "import server"
   ```

### Frontend Build Fails

1. **Clean install**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

2. **Check Node version**:
   ```bash
   node --version  # Should be 20+
   ```

### SSE Not Working

1. **Check Nginx configuration**:
   ```nginx
   proxy_buffering off;
   proxy_set_header X-Accel-Buffering no;
   ```

2. **Test SSE directly**:
   ```bash
   ./scripts/test_sse.sh
   ```

### Trading Not Working

1. **Verify trading gates**:
   ```bash
   # Check environment
   grep -E "PAPER_TRADING|LIVE_TRADING|AUTOPILOT" backend/.env
   ```

2. **Check system status**:
   ```bash
   curl http://localhost:8000/api/system/status
   ```

---

## 📞 Support

- **Documentation**: See `docs/` directory
- **Scripts**: See `scripts/` directory for verification tools
- **Issues**: Submit to GitHub repository

---

## 🎉 Success Criteria

Your deployment is successful when:

- ✅ Frontend accessible via browser
- ✅ User can register/login
- ✅ Dashboard loads without console errors
- ✅ SSE connection shows "connected" status
- ✅ Can create/view/delete bots
- ✅ Trading gates properly enforce mode restrictions
- ✅ All verification scripts pass

**Congratulations! You're go-live ready! 🚀**
