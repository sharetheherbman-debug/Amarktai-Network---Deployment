# Amarktai Network - Production Trading Platform

**Production-grade, plug-and-play deployment** for Ubuntu 24.04 with systemd + nginx. After `git pull`, `.env` setup, and restart, everything works in real-time.

## ⚡ Quick Start (Ubuntu 24.04)

### One-Command Setup

```bash
# Run as root or with sudo
sudo ./deployment/vps-setup.sh
```

This idempotent script will:
- ✅ Install Python 3.12 (Ubuntu 24.04 default), Node.js 20.x, MongoDB
- ✅ Setup Python virtual environment with all dependencies
- ✅ Configure systemd service for auto-restart
- ✅ Setup nginx reverse proxy with CORS
- ✅ Create necessary directories and permissions

### Manual Configuration

After running the setup script:

1. **Edit `.env` file** with your configuration:
   ```bash
   sudo nano /var/amarktai/backend/.env
   ```
   
   **Required**:
   - `JWT_SECRET` - Generate with: `openssl rand -hex 32`
   - `MONGO_URL` - MongoDB connection string
   - `OPENAI_API_KEY` - For AI trading decisions
   
   **Optional (for SMTP reports)**:
   - `SMTP_USER` - Gmail address or SMTP username
   - `SMTP_PASSWORD` - App-specific password (not your Gmail password)
   - `DAILY_REPORT_TIME` - Time to send reports (e.g., "08:00" for 8 AM UTC)

2. **Restart services**:
   ```bash
   sudo systemctl restart amarktai-api
   sudo systemctl reload nginx
   ```

3. **Verify deployment**:
   ```bash
   cd /var/amarktai
   ./deployment/smoke_test.sh
   ```

### Access Your Platform

- **Web UI**: `http://YOUR_SERVER_IP`
- **API**: `http://YOUR_SERVER_IP/api`
- **Health Check**: `curl http://YOUR_SERVER_IP/api/health/ping`

### Optional: SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 🏗️ Architecture

This repository is **production-wired for same-origin deployment** behind Nginx:

- **Frontend**: Served by Nginx at `/`
- **Backend API**: Reverse-proxied under `/api`
- **WebSocket**: Real-time updates at `/api/ws`
- **SSE**: Server-sent events at `/api/realtime/events`
- **Static Assets**: Served from `frontend/public/assets/` as `/assets/...`

```
Client → Nginx (80/443) → FastAPI Backend (8000)
                       ↓
                   MongoDB (27017)
```

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

**Version**: 3.0.0  
**Last Updated**: December 2025
