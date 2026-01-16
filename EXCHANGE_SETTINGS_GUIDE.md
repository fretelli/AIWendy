# Exchange Settings User Guide

This guide explains how to use the new Exchange Connections feature in KeelTrader.

## What is Exchange Connections?

The Exchange Connections feature allows you to securely connect your cryptocurrency exchange accounts to KeelTrader. This enables automatic import of your trading data, real-time portfolio tracking, and personalized trading insights.

## Supported Exchanges

- 🟡 **Binance** - World's largest crypto exchange
- ⚫ **OKX** - Major derivatives exchange
- 🟠 **Bybit** - Popular futures exchange
- 🔵 **Coinbase** - Leading US exchange
- 🟣 **Kraken** - Trusted since 2011

## How to Add an Exchange Connection

### Step 1: Get API Keys from Your Exchange

You need to create **READ-ONLY** API keys from your exchange:

#### Binance
1. Log in to [Binance](https://www.binance.com/)
2. Go to **Profile → API Management**
3. Click **Create API**
4. Enable **only** "Enable Reading" permission
5. Copy your API Key and Secret Key

#### OKX
1. Log in to [OKX](https://www.okx.com/)
2. Go to **Profile → API**
3. Click **Create API Key**
4. Select **Read** permission only
5. Set a passphrase (you'll need this later)
6. Copy API Key, Secret Key, and Passphrase

#### Bybit
1. Log in to [Bybit](https://www.bybit.com/)
2. Go to **Account → API Management**
3. Create **Unified Trading** API Key
4. Select **Read-Only** permissions
5. Copy API Key and Secret Key

⚠️ **IMPORTANT SECURITY RULES:**
- ✅ **DO:** Use read-only API keys
- ✅ **DO:** Enable IP whitelist (optional but recommended)
- ❌ **DON'T:** Give trading or withdrawal permissions
- ❌ **DON'T:** Share your API keys with anyone
- ❌ **DON'T:** Use API keys with fund transfer permissions

### Step 2: Add Connection in KeelTrader

1. **Navigate to Settings**
   - Click on your profile icon
   - Select "Settings"
   - Go to the "Exchanges" tab

2. **Click "Add Exchange"**

3. **Fill in the Form:**
   - **Exchange**: Select your exchange (Binance, OKX, etc.)
   - **Name**: Give it a friendly name like "My Main Binance Account" (optional)
   - **API Key**: Paste your API key
   - **API Secret**: Paste your API secret
   - **Passphrase**: (Only for OKX) Enter your API passphrase
   - **Use Testnet**: Check this if you're using testnet keys

4. **Click "Add Connection"**

5. **Test the Connection:**
   - After adding, click the "Test" button
   - ✅ Success: You'll see "Connection Successful" with your account details
   - ❌ Failed: Check your API keys and make sure they're active

## Managing Your Connections

### View All Connections

The Exchange Connections page shows all your connected exchanges with:
- Exchange name and custom label
- Masked API key (e.g., "abc1234...xyz9")
- Connection status (Active/Inactive)
- Last sync time
- Any error messages

### Test a Connection

Click the **Test** button on any connection to verify it's working. This will:
- Connect to the exchange API
- Fetch your account balance
- Display the number of currencies in your account
- Update the "Last Sync" timestamp

### Edit a Connection

Click the **Edit** button to:
- Change the connection name
- Update API credentials
- Update passphrase (for OKX)

**Note:** Leave fields empty to keep current values.

### Enable/Disable a Connection

Use the toggle switch to temporarily disable a connection without deleting it. Disabled connections won't be used for data sync.

### Delete a Connection

Click the **Delete** button to permanently remove a connection. You'll need to confirm this action.

⚠️ **Warning:** This will delete all credentials. You'll need to re-add the connection if you want to use it again.

## Security & Privacy

### How Are My Keys Stored?

- **Encrypted**: All API keys are encrypted using Fernet encryption before storing in the database
- **Secure**: Only you can access your connections (user-level isolation)
- **Masked**: Keys are masked when displayed (e.g., "abc1234...xyz9")
- **Never Shared**: Your keys are never sent to third parties

### What Permissions Do You Need?

KeelTrader only needs **READ-ONLY** permissions to:
- Fetch your account balance
- Read trade history
- View open positions
- Get market data

We **NEVER** need or request:
- ❌ Trading permissions
- ❌ Withdrawal permissions
- ❌ Transfer permissions

### Best Practices

1. **Use Read-Only Keys:** Only create API keys with read permissions
2. **Enable IP Whitelist:** Restrict API access to specific IPs (optional)
3. **Rotate Keys Regularly:** Update your API keys every few months
4. **Monitor Usage:** Check your exchange's API logs for unusual activity
5. **Delete Unused Connections:** Remove connections you no longer use

## Troubleshooting

### Connection Test Failed

**Error: "Invalid API key"**
- Double-check your API key is correct
- Make sure you copied the entire key (no extra spaces)
- Verify the API key is active on the exchange

**Error: "Permission denied"**
- Ensure the API key has read permissions
- For Binance: Enable "Enable Reading"
- For OKX: Enable "Read" permission
- For Bybit: Enable "Read-Only" unified trading

**Error: "Invalid signature"**
- Check your API secret is correct
- For OKX: Verify your passphrase is correct
- Try creating a new API key

**Error: "IP not whitelisted"**
- If you enabled IP whitelist on the exchange, add KeelTrader's server IP
- Or temporarily disable IP whitelist for testing

### Connection Works But No Data

- Wait a few minutes and try testing again
- Check if the exchange API is experiencing downtime
- Verify your account has trading history on the exchange

### "Failed to load exchange connections"

- Check your internet connection
- Try refreshing the page
- Log out and log back in
- Contact support if the issue persists

## FAQs

### Q: Is it safe to connect my exchange account?

**A:** Yes! We use:
- Industry-standard encryption (Fernet)
- Read-only API keys (no trading access)
- User-level isolation (only you can access your connections)
- Secure HTTPS connections

### Q: Can KeelTrader trade for me?

**A:** No. KeelTrader only reads your data. We cannot execute trades, transfer funds, or modify your account.

### Q: How often is my data synced?

**A:** Data is synced when you click "Test" or when KeelTrader fetches trading data for analysis. Real-time sync is coming soon.

### Q: Can I connect multiple accounts from the same exchange?

**A:** Yes! You can add multiple connections. Give each a unique name like "Binance Main" and "Binance Trading".

### Q: What if I change my API keys on the exchange?

**A:** Use the "Edit" button to update your API credentials in KeelTrader.

### Q: Can I use testnet keys?

**A:** Yes! Enable "Use Testnet" when adding the connection. Perfect for testing without risking real funds.

### Q: What happens if I delete a connection?

**A:** The connection and all encrypted credentials are permanently deleted from our database. You can re-add it anytime.

## Getting Help

If you encounter any issues:

1. Check this guide first
2. Review the [MARKET_DATA_INTEGRATION.md](./MARKET_DATA_INTEGRATION.md) for technical details
3. Open an issue on [GitHub](https://github.com/fretelli/keeltrader/issues)
4. Contact support

---

**Last Updated:** 2026-01-15
**Version:** 1.0.0

🎉 **Enjoy secure trading with KeelTrader!**
