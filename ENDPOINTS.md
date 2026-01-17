# Frontend API Endpoints - Final List

**Last Updated:** 2026-01-17  
**Status:** ✅ Production Ready

This document lists all API endpoints used by the frontend and their implementation status.

---

## Production Compatibility Endpoints (Added 2026-01-17)

These endpoints ensure dashboard compatibility and prevent 404 errors:

| Endpoint | Method | Auth | Status | Description |
|----------|--------|------|--------|-------------|
| `/api/wallet/requirements` | GET | ✅ | ✅ | Get wallet requirements per exchange with deposit info |
| `/api/system/emergency-stop` | POST | ✅ | ✅ | Activate emergency stop (admin/user gated) |
| `/api/system/emergency-stop/status` | GET | ✅ | ✅ | Get emergency stop status |
| `/api/system/emergency-stop/disable` | POST | ✅ | ✅ | Deactivate emergency stop |
| `/api/ai/insights` | GET | ✅ | ✅ | Get AI-powered system insights |
| `/api/ml/predict` | GET | ✅ | ✅ | ML prediction with query params (symbol, platform, timeframe) |
| `/api/profits/reinvest` | POST | ✅ | ✅ | Trigger profit reinvestment |
| `/api/advanced/decisions/recent` | GET | ✅ | ✅ | Get recent trading decisions |
| `/api/keys/test` | POST | ✅ | ✅ | Test API key (supports OpenAI, exchanges) |
| `/api/system/mode` | GET | ✅ | ✅ | Get current system mode |

---

## Authentication Endpoints

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/auth/register` | POST | ✅ | Register.js |
| `/api/auth/login` | POST | ✅ | Login.js |
| `/api/auth/me` | GET | ✅ | Dashboard.js (auth check) |
| `/api/auth/profile` | PUT | ✅ | Dashboard.js (profile update) |

---

## Dashboard & Metrics

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/overview` | GET | ✅ | Dashboard.js (main metrics) |
| `/api/overview/mode-stats` | GET | ✅ | Dashboard.js (mode status) |
| `/api/metrics` | GET | ✅ | Dashboard.js (real-time metrics) |
| `/api/analytics/profit-history` | GET | ✅ | Dashboard.js (profit graphs) |
| `/api/analytics/countdown-to-million` | GET | ✅ | Dashboard.js (countdown widget) |

---

## Bot Management

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/bots` | GET | ✅ | Dashboard.js (list bots) |
| `/api/bots` | POST | ✅ | Dashboard.js (create bot) |
| `/api/bots/{bot_id}` | PUT | ✅ | Dashboard.js (update bot) |
| `/api/bots/{bot_id}` | DELETE | ✅ | Dashboard.js (delete bot) |
| `/api/bots/{bot_id}/pause` | POST/PUT | ✅ | Dashboard.js (pause bot) |
| `/api/bots/{bot_id}/resume` | POST/PUT | ✅ | Dashboard.js (resume bot) |
| `/api/bots/{bot_id}/trading-enabled` | POST/PUT | ✅ | Dashboard.js (toggle trading) |
| `/api/bots/{bot_id}/promote` | POST | ✅ | Dashboard.js (promote to live) |
| `/api/bots/eligible-for-promotion` | GET | ✅ | Dashboard.js (eligible bots) |
| `/api/bots/confirm-live-switch` | POST | ✅ | Dashboard.js (confirm live) |

---

## Trading & Orders

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/trading/paper/start` | POST | ✅ | Dashboard.js (start paper) |
| `/api/trading/live/start` | POST | ✅ | Dashboard.js (start live) |
| `/api/system/mode` | GET | ✅ | Dashboard.js (get mode) |
| `/api/system/mode` | PUT | ✅ | Dashboard.js (set mode) |
| `/api/trades/recent` | GET | ✅ | Dashboard.js (recent trades) |

---

## Wallet Management

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/wallet/balances` | GET | ✅ | WalletHub.js, WalletOverview.js |
| `/api/wallet/requirements` | GET | ✅ | WalletHub.js, WalletOverview.js |
| `/api/wallet/funding-plans` | GET | ✅ | WalletHub.js (list plans) |
| `/api/wallet/funding-plans/{id}` | GET | ✅ | WalletHub.js (get plan) |
| `/api/wallet/funding-plans/{id}/cancel` | POST | ✅ | WalletHub.js (cancel plan) |

---

## API Keys Management

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/api-keys` | GET | ✅ | APIKeySettings.js (list keys) |
| `/api/api-keys` | POST | ✅ | APIKeySettings.js (save key) |
| `/api/api-keys/{provider}` | DELETE | ✅ | APIKeySettings.js (delete key) |
| `/api/api-keys/{provider}/test` | POST | ✅ | APIKeySettings.js (test key) |

---

## Autonomous Systems

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/autonomous/learning/trigger` | POST | ✅ | Dashboard.js (manual trigger) |
| `/api/autonomous/bodyguard/system-check` | POST | ✅ | Dashboard.js (system check) |
| `/api/autonomous/performance-rankings` | GET | ✅ | Dashboard.js (bot rankings) |
| `/api/autonomous/market-regime` | GET | ✅ | Dashboard.js (market regime) |
| `/api/autopilot/enable` | POST | ✅ | Dashboard.js (enable autopilot) |
| `/api/autopilot/disable` | POST | ✅ | Dashboard.js (disable autopilot) |
| `/api/autopilot/settings` | GET | ✅ | Dashboard.js (get settings) |

---

## Admin Endpoints

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/admin/storage` | GET | ✅ | Dashboard.js (storage usage) |
| `/api/admin/bodyguard-status` | GET | ✅ | Dashboard.js (bodyguard status) |
| `/api/admin/ai-learning-status` | GET | ✅ | Dashboard.js (AI learning status) |
| `/api/admin/users` | GET | ✅ | Dashboard.js (list users) |

---

## Advanced Trading (Intelligence)

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/advanced/whale/summary` | GET | ✅ | WhaleFlowHeatmap.js (whale flow) |

---

## System & Health

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/system/ping` | GET | ✅ | Dashboard.js (health check) |
| `/api/system/platforms` | GET | ✅ | PlatformSelector.js (platform list) |
| `/api/health/ping` | GET | ✅ | Dashboard.js (health check) |

---

## Real-Time Updates

| Endpoint | Protocol | Status | Frontend Usage |
|----------|----------|--------|----------------|
| `/api/ws` | WebSocket | ✅ | Dashboard.js (real-time updates) |
| `/ws/decisions` | WebSocket | ✅ | DecisionTrace.js (decision stream) |
| `/api/realtime/events` | SSE | ✅ | Available (not yet used) |

---

## AI Chat

| Endpoint | Method | Status | Frontend Usage |
|----------|--------|--------|----------------|
| `/api/chat` | POST | ✅ | Dashboard.js (send message) |
| `/api/chat/history` | GET | ✅ | Dashboard.js (chat history) |

---

## Summary

**Total Endpoints:** 50+  
**All Verified:** ✅ Yes  
**Missing Endpoints:** 0  
**Frontend Build:** ✅ Success  
**Backend Compatible:** ✅ Yes

---

## Platform Support

All endpoints support filtering by platform where applicable:

- **Luno** 🌙
- **Binance** 🔶
- **KuCoin** 🔷
- **Kraken** 🐙
- **VALR** 💎

Platform filtering is available via:
1. `/api/system/platforms` - Get all enabled platforms
2. `platformFilter` query parameter on relevant endpoints
3. Frontend PlatformSelector component for UI

---

## Authentication

All endpoints (except `/api/auth/login` and `/api/auth/register`) require:

```
Authorization: Bearer <JWT_TOKEN>
```

Token is obtained from login and stored in `localStorage`.

---

## Error Handling

All endpoints return consistent error format:

```json
{
  "detail": "Error message here"
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

---

## Rate Limiting

API endpoints are rate-limited via Nginx:
- General API: 10 requests/second (burst 20)
- WebSocket: 5 connections/second (burst 5)

---

**Last Verified:** 2026-01-14 15:00 UTC
