# Amarktai Network - Autonomous Trading Platform

**Production-ready trading platform** for cryptocurrency arbitrage and autonomous bot management.

---

## 📖 **Complete Documentation**

**→ [Single Source of Truth - Full Documentation](docs/AMARKTAI_SINGLE_SOURCE_OF_TRUTH.md)**

This comprehensive guide contains:
- Architecture overview
- Complete environment variable reference  
- Step-by-step deployment instructions
- Verification procedures
- Operational runbook
- Troubleshooting guide
- Safety constraints & security

---

## 🚀 Quick Start (Ubuntu 24.04)

### Prerequisites
- Ubuntu 24.04 LTS VPS
- Root or sudo access
- 2GB RAM, 20GB disk minimum

### Installation (5 minutes)

```bash
# 1. Clone repository to canonical location
sudo mkdir -p /var/amarktai
cd /var/amarktai
sudo git clone <repository-url> app

# 2. Run installation script
cd app/deployment
sudo ./install.sh

# 3. Configure environment
sudo nano /var/amarktai/app/backend/.env
# Edit: JWT_SECRET, ENCRYPTION_KEY, trading mode flags

# 4. Verify installation
sudo ./verify.sh
```

**That's it!** Service is now running on `http://127.0.0.1:8000`

### Verify Deployment

```bash
# Check service status
sudo systemctl status amarktai-api.service

# Test health endpoint
curl http://127.0.0.1:8000/api/health/ping

# Run comprehensive verification
cd /var/amarktai/app/deployment && sudo ./verify.sh
```

---

## 🎯 Key Features

- ✅ **Autonomous Trading**: AI-powered bots with autopilot mode
- ✅ **Multi-Exchange**: Luno, Binance, KuCoin support
- ✅ **Safety First**: Paper trading, emergency stop, ledger-based accounting
- ✅ **Production Ready**: Systemd service, Nginx config, health monitoring
- ✅ **Single Source of Truth**: Unified autopilot, no duplicate engines

---

## 🔒 Safety Constraints

- ❌ **No automatic fund transfers** between exchanges (hard-blocked)
- ✅ **Paper mode**: Allocation ledger (no real funds moved)
- ✅ **Live mode**: Balance checks only (no transfers)
- ✅ **Bot spawning**: Requires verified profit >= 1000 ZAR
- ✅ **Emergency stop**: Halts all trading immediately

---

## 📚 Documentation

- **[Complete Deployment Guide](docs/AMARKTAI_SINGLE_SOURCE_OF_TRUTH.md)** ← START HERE
- [Quick Start](QUICK_START.md) - Basic getting started
- [Environment Variables](.env.example) - All configuration options
- [API Documentation](http://127.0.0.1:8000/docs) - Interactive API docs (after deployment)

**Archived docs:** See `docs/archive/` for historical reference

---

## 🛠️ System Requirements

- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.12+
- **Node.js**: 18+ (for frontend)
- **Database**: MongoDB 7.0 (Docker)
- **Cache**: Redis (optional)
- **Web Server**: Nginx (reverse proxy)

---

## 📦 Architecture

```
Nginx (80/443) → FastAPI (127.0.0.1:8000) → MongoDB (127.0.0.1:27017)
                                          → Redis (127.0.0.1:6379)
```

**Canonical VPS Layout:**
```
/var/amarktai/app/          # Repository root
├── backend/                # FastAPI application
│   ├── .venv/              # Python virtual environment
│   └── .env                # Environment config
├── frontend/               # React application  
└── deployment/             # Deployment scripts
    ├── install.sh          # Main installer
    ├── verify.sh           # Verification script
    ├── amarktai-api.service  # Systemd service
    └── nginx-amarktai.conf   # Nginx config
```

---

## 🚦 Trading Modes

**Paper Trading** (safe for testing):
```bash
PAPER_TRADING=1
LIVE_TRADING=0
AUTOPILOT_ENABLED=0  # Optional
```

**Live Trading** (requires API keys):
```bash
PAPER_TRADING=0
LIVE_TRADING=1
AUTOPILOT_ENABLED=0  # Optional
```

**Autopilot** (autonomous bot management):
```bash
AUTOPILOT_ENABLED=1
# Plus either PAPER_TRADING=1 or LIVE_TRADING=1
```

---

## 📞 Support

For detailed troubleshooting and operational procedures:
- **[Complete Documentation](docs/AMARKTAI_SINGLE_SOURCE_OF_TRUTH.md)**
- Check service logs: `sudo journalctl -u amarktai-api.service -f`
- Run verification: `cd deployment && sudo ./verify.sh`

---

## ⚖️ License

See LICENSE file for details.

---

**Quick Links:**
- [📖 Full Documentation](docs/AMARKTAI_SINGLE_SOURCE_OF_TRUTH.md)
- [🔧 Installation Script](deployment/install.sh)
- [✅ Verification Script](deployment/verify.sh)
- [🌐 Nginx Config](deployment/nginx-amarktai.conf)
- [⚙️ Systemd Service](deployment/amarktai-api.service)
