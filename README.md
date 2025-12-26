# Amarktai Network (Production-Ready)

Autonomous AI cryptocurrency trading system designed for **plug-and-play deployment** to Ubuntu 24.04 VPS.

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
