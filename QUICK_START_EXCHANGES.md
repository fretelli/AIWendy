# Quick Start: Exchange Connections

Get your exchange connected in 5 minutes!

## 🚀 Quick Setup

### 1. Run Database Migration

```bash
cd keeltrader
alembic upgrade head

# Or with Docker (automatic)
docker-compose down && docker-compose up --build
```

### 2. Start the Application

```bash
# Backend
cd keeltrader/apps/api
python main.py

# Frontend (in another terminal)
cd keeltrader/apps/web
npm run dev
```

### 3. Access Exchange Settings

1. Open http://localhost:3000
2. Log in to your account
3. Click **Profile → Settings**
4. Go to **Exchanges** tab

## 🔑 Get Your API Keys

### OKX (1 minute)

1. Go to https://www.okx.com/account/my-api
2. Create V5 API → Select **Read** permission
3. Set a **Passphrase** (remember it!)
4. Copy **API Key**, **Secret Key**, and **Passphrase**

### Bybit (30 seconds)

1. Go to https://www.bybit.com/app/user/api-management
2. Create API → Select **Read-Only** permissions
3. Copy **API Key** and **Secret Key**

## ➕ Add Connection in KeelTrader

1. Click **"Add Exchange"** button
2. Fill in the form:
   ```
   Exchange: OKX (or your choice)
   Name: My Trading Account (optional)
   API Key: [paste your key]
   API Secret: [paste your secret]
   Passphrase: [only for OKX]
   ```
3. Click **"Add Connection"**
4. Click **"Test"** to verify ✅

## ✅ Done!

You should see:
- ✅ Connection status: Active
- ✅ Last sync: Just now
- ✅ Test result: "Connection successful"

## 🎯 What's Next?

Now KeelTrader can:
- Read your trading history
- Analyze your positions
- Track your performance
- Give you personalized insights

## 🛟 Need Help?

- **Connection failed?** → See [Troubleshooting](#troubleshooting-quick-fixes)
- **Security questions?** → Read [EXCHANGE_SETTINGS_GUIDE.md](./EXCHANGE_SETTINGS_GUIDE.md)
- **Technical details?** → Check [MARKET_DATA_INTEGRATION.md](./MARKET_DATA_INTEGRATION.md)

## 🔧 Troubleshooting Quick Fixes

### "Invalid API key"
→ Copy the entire key (no spaces), make sure it's active on the exchange

### "Permission denied"
→ Enable "Read" or "Reading" permission on the exchange

### "IP not whitelisted"
→ Disable IP whitelist on your exchange API settings (or add KeelTrader's IP)

### "Invalid signature" (OKX)
→ Check your passphrase is correct

### Page not loading?
→ Make sure both backend (port 8000) and frontend (port 3000) are running

---

**That's it! 🎉 Happy trading!**
