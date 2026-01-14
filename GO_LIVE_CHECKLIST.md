# GO-LIVE CHECKLIST

**Date:** _____________
**Deployed By:** _____________
**Environment:** Production

---

## PRE-DEPLOYMENT CHECKS

### 1. Assets ✓
- [ ] All assets exist in `frontend/public/assets/`
- [ ] Run `npm run check:assets` passes
- [ ] logo.png, poster.jpg, background.mp4 all non-empty
- [ ] Assets accessible at `/assets/*` URLs

### 2. Build & Dependencies ✓
- [ ] `npm install` completes without errors
- [ ] `npm run build` succeeds
- [ ] Build output in `frontend/build/`
- [ ] No console errors in build output
- [ ] Build size reasonable (<10MB)

### 3. Environment Variables ✓
- [ ] Backend `.env` configured:
  - `MONGODB_URI`
  - `JWT_SECRET`
  - `ENABLE_TRADING=1` (for production)
  - `ENABLE_SCHEDULERS=1`
  - Exchange API keys configured
- [ ] Frontend environment (if using):
  - `REACT_APP_API_BASE=/api` (or appropriate)

---

## BACKEND VALIDATION

### 4. Database & Connectivity ✓
- [ ] MongoDB accessible
- [ ] Run: `curl http://localhost:8000/api/health/ping`
  - Expect: `{"status":"healthy","db":"connected"}`
- [ ] Collections created: users, bots, trades, api_keys, etc.

### 5. Critical Endpoints ✓
Test all critical endpoints with authenticated token:

```bash
TOKEN="<your-jwt-token>"
API="http://localhost:8000/api"

# Health
curl -H "Authorization: Bearer $TOKEN" $API/health/ping

# Platforms (must return 5)
curl -H "Authorization: Bearer $TOKEN" $API/system/platforms

# User
curl -H "Authorization: Bearer $TOKEN" $API/auth/me

# Bots
curl -H "Authorization: Bearer $TOKEN" $API/bots

# Trades
curl -H "Authorization: Bearer $TOKEN" $API/trades/recent?limit=10

# Wallet
curl -H "Authorization: Bearer $TOKEN" $API/wallet/balances

# Metrics
curl -H "Authorization: Bearer $TOKEN" $API/portfolio/summary

# System Health
curl -H "Authorization: Bearer $TOKEN" $API/system/health
```

- [ ] All endpoints return 200 or expected status
- [ ] No 500 errors
- [ ] All return valid JSON

### 6. WebSocket ✓
- [ ] WebSocket endpoint accessible: `ws://localhost:8000/api/ws?token=$TOKEN`
- [ ] Connection accepts and sends ping/pong
- [ ] Connection survives 60+ seconds
- [ ] Test with tool: `websocat ws://localhost:8000/api/ws?token=$TOKEN`

---

## FRONTEND VALIDATION

### 7. Login & Authentication ✓
- [ ] Navigate to `/login`
- [ ] Login form renders correctly
- [ ] Can login with valid credentials
- [ ] JWT token stored in localStorage
- [ ] Redirected to dashboard on success
- [ ] Invalid credentials show error

### 8. Dashboard Sections ✓
Test all main sections load without errors:

- [ ] **Welcome/Overview**: Metrics display
- [ ] **Bot Management**: Bots list, can create bot
- [ ] **Live Trades**: Trades stream visible
- [ ] **Wallet Hub**: Balances load, no "Not Found"
- [ ] **Intelligence > Whale Flow**: Component loads
- [ ] **Intelligence > Decision Trace**: Component loads
- [ ] **Intelligence > Metrics**: Prometheus metrics load
- [ ] **API Setup**: Keys management works
- [ ] **Settings**: Profile update works

### 9. Platform Selector ✓
- [ ] Platform selector shows all 5 platforms:
  - 🌙 Luno
  - 🔶 Binance  
  - 🔷 KuCoin
  - 🐙 Kraken
  - 💎 VALR
- [ ] "All Platforms" option present
- [ ] Selecting platform filters views

### 10. Real-Time Updates ✓
- [ ] Open browser DevTools → Console
- [ ] Look for: `✅ WebSocket connected`
- [ ] Connection status shows "Connected (WS)" or "Connected (Polling)"
- [ ] Last update timestamps visible
- [ ] Ping/pong messages in console (every 30s)
- [ ] Create a test trade → see it appear in dashboard

### 11. Assets Loading ✓
- [ ] Logo displays correctly
- [ ] Background video plays (if applicable)
- [ ] No broken image icons
- [ ] Check browser DevTools → Network → no 404s for assets

---

## DEPLOYMENT VALIDATION

### 12. Nginx Configuration ✓
- [ ] Nginx config includes proxy_pass to backend
- [ ] WebSocket upgrade headers configured:
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```
- [ ] Static files served from `/var/amarktai/app/frontend/build`
- [ ] `/api/*` proxied to backend
- [ ] SSL certificate valid (if HTTPS)
- [ ] Test: `curl https://your-domain.com/api/health/ping`

### 13. Systemd Services ✓
- [ ] Backend service running: `systemctl status amarktai-backend`
- [ ] Service set to auto-start: `systemctl is-enabled amarktai-backend`
- [ ] Check logs: `journalctl -u amarktai-backend -f`
- [ ] No critical errors in logs

### 14. Firewall & Security ✓
- [ ] Firewall allows HTTP/HTTPS (ports 80, 443)
- [ ] Backend port (8000) not exposed externally
- [ ] SSH access restricted (if applicable)
- [ ] Rate limiting configured in Nginx (if applicable)

---

## FUNCTIONAL TESTING

### 15. Create Bot Flow ✓
- [ ] Navigate to Bot Management
- [ ] Click "Create Bot"
- [ ] Select platform (e.g., Luno)
- [ ] Configure symbol, capital, risk
- [ ] Submit → bot appears in list
- [ ] Bot shows correct status

### 16. Live Trading Toggle ✓
- [ ] Paper trading mode works
- [ ] Can promote bot to live (if conditions met)
- [ ] Confirmation dialog appears
- [ ] Live trading requires explicit enable

### 17. AI Tools ✓
Test AI tool buttons (if configured):
- [ ] AI Bodyguard → runs system check
- [ ] Learning System → triggers learning
- [ ] Evolve Bots → shows result
- [ ] Insights → fetches insights
- [ ] Predict → shows prediction
- [ ] Reinvest Profits → confirms action
- [ ] If not configured → shows "not configured" message (no crash)

### 18. Admin Panel ✓
- [ ] Type "show admin" in chat
- [ ] Prompted for admin password
- [ ] Enter correct password → admin panel appears
- [ ] Admin panel shows users, stats
- [ ] Type "hide admin" → panel hides
- [ ] Refresh page → admin panel stays hidden (not persisted)

---

## PERFORMANCE & MONITORING

### 19. Performance ✓
- [ ] Dashboard loads in <3 seconds
- [ ] No memory leaks (check DevTools → Memory)
- [ ] WebSocket reconnects after disconnect
- [ ] Page responsive on mobile

### 20. Error Handling ✓
- [ ] Disconnect internet → see "Disconnected" status
- [ ] Reconnect → see "Connected" status
- [ ] Invalid API calls → show error toast, don't crash
- [ ] Empty states render (no bots, no trades, etc.)

### 21. Monitoring Setup ✓
- [ ] Prometheus metrics accessible: `/api/metrics`
- [ ] System health endpoint: `/api/system/health`
- [ ] Logs aggregated (e.g., journalctl, file logs)
- [ ] Alert mechanisms configured (email, etc.)

---

## FINAL SIGN-OFF

### 22. Documentation ✓
- [ ] README.md updated with setup instructions
- [ ] ENDPOINTS.md lists all endpoints
- [ ] Deployment guide complete
- [ ] Known issues documented (if any)

### 23. Backup & Recovery ✓
- [ ] Database backup created
- [ ] Backup restoration tested
- [ ] Config files backed up
- [ ] Rollback plan documented

### 24. Handoff ✓
- [ ] Stakeholders notified
- [ ] Support contacts documented
- [ ] Emergency procedures documented
- [ ] Go-live announcement prepared

---

## POST-DEPLOYMENT MONITORING

### First Hour ✓
- [ ] Monitor CPU/RAM usage
- [ ] Watch logs for errors
- [ ] Test all critical flows
- [ ] Verify real-time updates working

### First 24 Hours ✓
- [ ] Check error rates
- [ ] Monitor WebSocket stability
- [ ] Verify no data loss
- [ ] User feedback collected

### First Week ✓
- [ ] Performance metrics reviewed
- [ ] No critical bugs reported
- [ ] System stable under load
- [ ] Backup schedule working

---

**SIGN-OFF**

- [ ] All checks completed
- [ ] System ready for production
- [ ] Stakeholders approved

**Signed:** _____________  
**Date:** _____________  
**Status:** [ ] APPROVED [ ] PENDING [ ] FAILED

---

## Emergency Contacts

- **Backend Issues:** _____________
- **Frontend Issues:** _____________
- **Database Issues:** _____________
- **Infrastructure:** _____________

## Rollback Procedure

If critical issues occur:

1. Stop nginx: `sudo systemctl stop nginx`
2. Stop backend: `sudo systemctl stop amarktai-backend`
3. Restore previous build: `mv build.backup build`
4. Restore database: (restore from backup)
5. Start services
6. Notify stakeholders
