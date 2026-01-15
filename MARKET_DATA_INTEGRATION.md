# Market Data & Exchange Integration Guide

This guide explains how to configure and use the market data and exchange integration features in KeelTrader.

## Table of Contents

- [Features](#features)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [WebSocket Integration](#websocket-integration)
- [Frontend Usage](#frontend-usage)
- [Troubleshooting](#troubleshooting)

## Features

KeelTrader now supports three types of market data integration:

1. **Real-time Market Data** - Stock and crypto price data via Twelve Data API
2. **WebSocket Streaming** - Real-time price updates via WebSocket
3. **Exchange Integration** - Connect to crypto exchanges (Binance, OKX, Bybit) to read positions and balances

## Configuration

### 1. Twelve Data API (Stock Market Data)

[Twelve Data](https://twelvedata.com/) provides real-time and historical stock market data with a free tier.

**Get an API Key:**
1. Sign up at https://twelvedata.com/
2. Navigate to your dashboard to get your API key
3. Free tier includes 800 API calls/day

**Configure:**
```bash
# In your .env file
TWELVE_DATA_API_KEY=your_api_key_here
```

**Supported Features:**
- Historical OHLCV data (Open, High, Low, Close, Volume)
- Real-time price quotes
- Technical indicators (SMA, EMA, RSI)
- Multiple time intervals (1min to 1month)
- Stock, ETF, Forex, and Crypto symbols

**Usage:**
```bash
# Get historical data
GET /api/market-data/historical/AAPL?interval=1day&outputsize=60

# Get real-time price
GET /api/market-data/real-time/AAPL

# Get technical indicators
GET /api/market-data/indicators/AAPL/sma?period=20
```

**Note:** If no API key is configured, the system will fall back to mock data for development/testing.

### 2. WebSocket Streaming

Real-time price updates via WebSocket connection.

**WebSocket Endpoint:**
```
ws://localhost:8000/api/market-data/ws/{symbol}
```

**Example:**
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/market-data/ws/AAPL');

ws.onopen = () => {
  console.log('Connected to market data stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Price update:', data);
  // { type: 'price_update', symbol: 'AAPL', price: 180.25, timestamp: '...' }
};

// Subscribe to additional symbols
ws.send(JSON.stringify({
  action: 'subscribe',
  symbol: 'TSLA'
}));

// Unsubscribe
ws.send(JSON.stringify({
  action: 'unsubscribe',
  symbol: 'AAPL'
}));
```

**Features:**
- Real-time price updates (with Twelve Data API) or mock data stream (every 2 seconds)
- Multiple symbol subscriptions per connection
- Automatic reconnection on disconnect
- Graceful fallback to mock data if API is unavailable

### 3. Exchange Integration (CCXT)

Connect to cryptocurrency exchanges to read account data, positions, and trade history.

#### Supported Exchanges

- **Binance** - World's largest crypto exchange
- **OKX** - Major derivatives exchange
- **Bybit** - Popular futures exchange

#### Get API Keys

**Binance:**
1. Log in to https://www.binance.com/
2. Go to Profile → API Management
3. Create API Key with **read-only** permissions
4. Save API Key and Secret Key

**OKX:**
1. Log in to https://www.okx.com/
2. Go to Profile → API
3. Create API Key with **read** permissions
4. Save API Key, Secret Key, and Passphrase

**Bybit:**
1. Log in to https://www.bybit.com/
2. Go to Account → API Management
3. Create API Key with **read-only** permissions
4. Save API Key and Secret Key

#### Configure

**KeelTrader supports TWO configuration modes:**

##### Option 1: User-Level Configuration (Recommended for Multi-User/SaaS)

Each user configures their own exchange API keys through the frontend settings page.

**Advantages:**
- ✅ Each user has their own exchange connections
- ✅ Keys are encrypted in the database
- ✅ Users can manage multiple exchange accounts
- ✅ Perfect for multi-tenant/SaaS deployments

**How to use:**
1. Users log in to KeelTrader
2. Go to Settings → Exchange Connections
3. Click "Add Exchange"
4. Enter API credentials (encrypted automatically)
5. Test connection

**API Endpoints:**
- `GET /api/v1/user/exchanges` - List user's connections
- `POST /api/v1/user/exchanges` - Add new connection
- `PUT /api/v1/user/exchanges/{id}` - Update connection
- `DELETE /api/v1/user/exchanges/{id}` - Remove connection
- `POST /api/v1/user/exchanges/{id}/test` - Test connection

##### Option 2: Server-Level Configuration (Admin-Only)

Configure exchange API keys in the server's .env file (requires server restart).

**Use case:** Single-user self-hosted deployments

```bash
# In your .env file

# Binance
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# OKX
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase

# Bybit
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
```

**Note:** Server-level keys work for the old `/api/exchanges` endpoints.

---

**Security Best Practices:**
- ⚠️ **IMPORTANT:** Only use **READ-ONLY** API keys
- Never commit API keys to version control
- Use IP whitelisting on exchange API settings
- User-level keys are encrypted automatically
- Server-level keys should be in `.env` file (which is gitignored)
- Rotate keys regularly

## API Endpoints

### Market Data

#### Get Historical Data
```
GET /api/market-data/historical/{symbol}
```

**Parameters:**
- `symbol` (required): Stock/crypto symbol (e.g., "AAPL", "BTC")
- `interval`: Time interval (1min, 5min, 15min, 30min, 1h, 1day, 1week, 1month)
- `outputsize`: Number of data points (default: 60, max: 500)
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response:**
```json
[
  {
    "time": "2024-01-01T00:00:00",
    "open": 180.25,
    "high": 182.50,
    "low": 179.80,
    "close": 181.75,
    "volume": 5234567
  }
]
```

#### Get Real-time Price
```
GET /api/market-data/real-time/{symbol}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 180.25,
  "change": 2.50,
  "change_percent": 1.41,
  "timestamp": "2024-01-01T12:00:00",
  "volume": 5234567
}
```

#### Get Technical Indicators
```
GET /api/market-data/indicators/{symbol}/{indicator}
```

**Parameters:**
- `symbol` (required): Stock/crypto symbol
- `indicator` (required): Indicator type (sma, ema, rsi)
- `interval`: Time interval
- `period`: Period for the indicator (default: 20)

**Response:**
```json
[
  {
    "time": "2024-01-01T00:00:00",
    "value": 178.50
  }
]
```

### Exchange APIs

#### Get Available Exchanges
```
GET /api/exchanges/
```

**Response:**
```json
[
  { "name": "binance" },
  { "name": "okx" },
  { "name": "bybit" }
]
```

#### Get Account Balance
```
GET /api/exchanges/{exchange_name}/balance
```

**Response:**
```json
{
  "exchange": "binance",
  "timestamp": "2024-01-01T12:00:00",
  "total": {
    "BTC": 0.5,
    "USDT": 10000.0,
    "ETH": 2.5
  },
  "free": {
    "BTC": 0.3,
    "USDT": 8000.0,
    "ETH": 2.0
  },
  "used": {
    "BTC": 0.2,
    "USDT": 2000.0,
    "ETH": 0.5
  }
}
```

#### Get Open Positions
```
GET /api/exchanges/{exchange_name}/positions
```

**Response:**
```json
[
  {
    "symbol": "BTC/USDT",
    "side": "long",
    "contracts": 0.1,
    "notional": 4300.0,
    "leverage": 10,
    "entry_price": 43000.0,
    "mark_price": 43500.0,
    "liquidation_price": 39000.0,
    "unrealized_pnl": 50.0,
    "percentage": 1.16,
    "timestamp": 1704110400000
  }
]
```

#### Get Open Orders
```
GET /api/exchanges/{exchange_name}/orders?symbol=BTC/USDT
```

**Response:**
```json
[
  {
    "id": "123456789",
    "symbol": "BTC/USDT",
    "type": "limit",
    "side": "buy",
    "price": 42000.0,
    "amount": 0.1,
    "filled": 0.0,
    "remaining": 0.1,
    "status": "open",
    "timestamp": 1704110400000,
    "datetime": "2024-01-01T12:00:00Z"
  }
]
```

#### Get Trade History
```
GET /api/exchanges/{exchange_name}/trades?symbol=BTC/USDT&limit=100
```

**Parameters:**
- `symbol` (optional): Filter by symbol
- `since` (optional): Timestamp in milliseconds
- `limit` (optional): Max number of trades (default: 100, max: 1000)

**Response:**
```json
[
  {
    "id": "987654321",
    "order_id": "123456789",
    "symbol": "BTC/USDT",
    "type": "limit",
    "side": "buy",
    "price": 43000.0,
    "amount": 0.1,
    "cost": 4300.0,
    "fee": {
      "cost": 4.3,
      "currency": "USDT"
    },
    "timestamp": 1704110400000,
    "datetime": "2024-01-01T12:00:00Z"
  }
]
```

#### Get Markets
```
GET /api/exchanges/{exchange_name}/markets
```

**Response:**
```json
[
  {
    "symbol": "BTC/USDT",
    "base": "BTC",
    "quote": "USDT",
    "active": true,
    "type": "spot",
    "spot": true,
    "future": false,
    "swap": false
  }
]
```

## WebSocket Integration

### Connection Lifecycle

```javascript
class MarketDataWS {
  constructor(symbol) {
    this.symbol = symbol;
    this.ws = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
  }

  connect() {
    const url = `ws://localhost:8000/api/market-data/ws/${this.symbol}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log(`Connected to ${this.symbol} stream`);
      this.reconnectDelay = 1000; // Reset delay on successful connection
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handlePriceUpdate(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(() => this.connect(), this.reconnectDelay);

      // Exponential backoff
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
    };
  }

  handlePriceUpdate(data) {
    if (data.type === 'price_update') {
      console.log(`${data.symbol}: $${data.price} at ${data.timestamp}`);
      // Update your UI here
    }
  }

  subscribe(newSymbol) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        symbol: newSymbol
      }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage
const btcWS = new MarketDataWS('BTC');
btcWS.connect();

// Subscribe to additional symbols
btcWS.subscribe('ETH');
btcWS.subscribe('AAPL');
```

## Frontend Usage

### React Example

```typescript
// hooks/useMarketData.ts
import { useState, useEffect } from 'react';

interface PriceData {
  symbol: string;
  price: number;
  timestamp: string;
}

export function useMarketDataWS(symbol: string) {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/api/market-data/ws/${symbol}`
    );

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'price_update') {
        setPrice(data);
      }
    };

    return () => ws.close();
  }, [symbol]);

  return { price, isConnected };
}

// Component usage
function PriceDisplay({ symbol }: { symbol: string }) {
  const { price, isConnected } = useMarketDataWS(symbol);

  return (
    <div>
      <span>{isConnected ? '🟢' : '🔴'}</span>
      <h2>{symbol}</h2>
      {price && (
        <div>
          <p>Price: ${price.price}</p>
          <p>Updated: {new Date(price.timestamp).toLocaleString()}</p>
        </div>
      )}
    </div>
  );
}
```

### User Exchange Management (Recommended)

```typescript
import { userExchangeApi } from '@/lib/api/user-exchanges'

// List all user exchange connections
async function loadConnections() {
  const connections = await userExchangeApi.getConnections()
  console.log('My exchanges:', connections)
}

// Add a new exchange connection
async function addBinance() {
  const connection = await userExchangeApi.createConnection({
    exchange_type: 'binance',
    name: 'My Main Binance Account',
    api_key: 'your_api_key',
    api_secret: 'your_api_secret',
    is_testnet: false,
  })
  console.log('Connected:', connection)
}

// Test connection
async function testConnection(connectionId: string) {
  const result = await userExchangeApi.testConnection(connectionId)
  if (result.success) {
    console.log('✅ Connection working!', result.data)
  } else {
    console.error('❌ Connection failed:', result.message)
  }
}

// Component usage
function ExchangeSettings() {
  const [connections, setConnections] = useState([])

  useEffect(() => {
    userExchangeApi.getConnections().then(setConnections)
  }, [])

  const handleAddExchange = async (data) => {
    const newConnection = await userExchangeApi.createConnection(data)
    setConnections([...connections, newConnection])
  }

  const handleDeleteExchange = async (id) => {
    await userExchangeApi.deleteConnection(id)
    setConnections(connections.filter(c => c.id !== id))
  }

  return (
    <div>
      <h2>My Exchange Connections</h2>
      {connections.map((conn) => (
        <div key={conn.id}>
          <h3>{conn.name}</h3>
          <p>Exchange: {conn.exchange_type}</p>
          <p>API Key: {conn.api_key_masked}</p>
          <p>Status: {conn.is_active ? '✅ Active' : '❌ Inactive'}</p>
          <button onClick={() => handleDeleteExchange(conn.id)}>
            Delete
          </button>
        </div>
      ))}
      <button onClick={() => setShowAddForm(true)}>
        Add Exchange
      </button>
    </div>
  )
}
```

### Server-Level Exchange Data (Old API)

```typescript
// api/exchanges.ts
export async function getBalance(exchange: string) {
  const response = await fetch(`/api/exchanges/${exchange}/balance`);
  return response.json();
}

export async function getPositions(exchange: string) {
  const response = await fetch(`/api/exchanges/${exchange}/positions`);
  return response.json();
}

// Component usage
function ExchangeBalance({ exchange }: { exchange: string }) {
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    getBalance(exchange).then(setBalance);
  }, [exchange]);

  return (
    <div>
      <h2>{exchange} Balance</h2>
      {balance && (
        <ul>
          {Object.entries(balance.total).map(([currency, amount]) => (
            <li key={currency}>
              {currency}: {amount}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Troubleshooting

### Mock Data Instead of Real Data

**Problem:** The API returns mock/random data instead of real market data.

**Solution:**
1. Check if `TWELVE_DATA_API_KEY` is set in your `.env` file
2. Verify the API key is valid by testing at https://twelvedata.com/
3. Check API quota: Free tier has 800 calls/day
4. Look at server logs for error messages

### Exchange API Not Working

**Problem:** Exchange endpoints return 404 or "not configured" errors.

**Solution:**
1. Verify API keys are set in `.env` file
2. Check API key permissions are set to **read-only**
3. Test API keys directly on the exchange website
4. Check if IP whitelisting is enabled on the exchange
5. Look at server logs: `docker-compose logs api`

### WebSocket Connection Fails

**Problem:** WebSocket connection closes immediately or won't connect.

**Solution:**
1. Check if the backend server is running
2. Verify the WebSocket URL is correct (ws:// not wss:// for local dev)
3. Check browser console for CORS errors
4. Ensure firewall allows WebSocket connections
5. Test with a simple WebSocket client first

### Rate Limiting

**Problem:** Getting rate limit errors from Twelve Data or exchanges.

**Solution:**
1. **Twelve Data:** Free tier = 800 calls/day. Consider upgrade or caching.
2. **Exchanges:** CCXT handles rate limiting automatically. If errors persist, increase delays.
3. Implement caching on the frontend to reduce API calls.
4. Use WebSocket for real-time data instead of polling.

### Import Dependencies

**Problem:** `ModuleNotFoundError: No module named 'ccxt'` or `websockets`.

**Solution:**
```bash
# Install dependencies
cd aiwendy/apps/api
pip install -r requirements.txt

# Or with Docker
docker-compose down
docker-compose up --build
```

## Next Steps

- Integrate the APIs into your KeelTrader frontend
- Add charts using the historical data endpoints
- Display real-time prices using WebSocket
- Show exchange balances and positions in the dashboard
- Import exchange trade history into your trading journal

## Support

For issues or questions:
- Check the [GitHub Issues](https://github.com/fretelli/keeltrader/issues)
- Read the [main README](./README.md)
- Review the API documentation at `/api/docs` (when debug=true)

---

**Security Reminder:** Always use READ-ONLY API keys and never commit them to version control!
