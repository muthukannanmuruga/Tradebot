# Upstox Integration Guide

## Overview

The Upstox integration adds support for **Indian stock market** trading alongside the existing Binance crypto trading. Both systems run independently and share the same DeepSeek AI engine, technical indicator calculations, and database.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                     main.py (FastAPI)                   │
│  /bot/*  → TradingBot (Binance)                        │
│  /upstox/* → UpstoxTradingBot (Upstox)                │
├────────────────────┬───────────────────────────────────┤
│  binance_client.py │  upstox_client.py                │
│  (Crypto markets)  │  (NSE/BSE/MCX Indian markets)    │
├────────────────────┴───────────────────────────────────┤
│            Shared: indicators.py, deepseek_ai.py       │
│            Shared: database.py (trades, portfolio)     │
└────────────────────────────────────────────────────────┘
```

## Setup

### 1. Create Upstox App

1. Go to [Upstox Developer Portal](https://account.upstox.com/developer/apps)
2. Create a new app
3. Note down **API Key**, **API Secret**, and set **Redirect URI** to `http://localhost:8000/upstox/callback`

### 2. Configure `.env`

```env
UPSTOX_ENABLED=True
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_REDIRECT_URI=http://localhost:8000/upstox/callback
UPSTOX_ACCESS_TOKEN=        # Filled automatically after successful auth flow (or paste manually)
UPSTOX_SANDBOX=False

# Trading pairs - instrument tokens (comma-separated)
UPSTOX_TRADING_PAIRS=NSE_EQ|INE848E01016,NSE_EQ|INE002A01018

# Trade amount in INR
UPSTOX_TRADING_AMOUNT=1000

# I = Intraday, D = Delivery, MTF = Margin Trading Facility
UPSTOX_PRODUCT_TYPE=I
```

### 3. Get Access Token

Upstox uses OAuth2 – you need a daily access token:

**Option A: Via API (recommended for bots)**

1. Start the server: `python main.py`
2. Visit: `GET /upstox/auth-url` → Get the login URL
3. Open the URL in browser, log in with Upstox credentials
4. After login, you'll be redirected to `/upstox/callback?code=...`
5. The callback returns your access token
6. Save it in `.env` as `UPSTOX_ACCESS_TOKEN`

**Option B: Manual token (quick testing)**

1. Go to [Upstox Developer Apps](https://account.upstox.com/developer/apps)
2. Click your app → Generate token
3. Copy and paste into `.env`

> ⚠️ Upstox tokens expire daily. You need to regenerate them each trading day.

### 4. Find Instrument Tokens

Download the instruments master from:
```
GET https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz
```

Common tokens:
| Stock     | Instrument Token            |
|-----------|-----------------------------|
| Reliance  | `NSE_EQ\|INE002A01018`       |
| TCS       | `NSE_EQ\|INE467B01029`       |
| HDFC Bank | `NSE_EQ\|INE040A01034`       |
| Infosys   | `NSE_EQ\|INE009A01021`       |
| SBIN      | `NSE_EQ\|INE062A01020`       |

## API Endpoints

### Bot Control
| Method | Endpoint             | Description               |
|--------|----------------------|---------------------------|
| POST   | `/upstox/start`      | Start Upstox trading bot  |
| POST   | `/upstox/stop`       | Stop Upstox trading bot   |
| GET    | `/upstox/status`     | Get bot status            |

### Trading
| Method | Endpoint                        | Description              |
|--------|---------------------------------|--------------------------|
| POST   | `/upstox/trade/manual`          | Manual trade             |
| GET    | `/upstox/portfolio`             | Get Upstox portfolio     |
| GET    | `/upstox/market-data/{token}`   | Get market data          |

### Auth
| Method | Endpoint              | Description               |
|--------|-----------------------|---------------------------|
| GET    | `/upstox/auth-url`    | Get OAuth2 login URL      |
| GET    | `/upstox/callback`    | OAuth2 callback handler   |

| POST   | `/upstox/request-rotation` | Best-effort token request (server-side) |
| POST   | `/upstox/webhook`     | (Optional) Postback URL for order updates |

## How It Works

1. **Data Fetching**: `UpstoxClient` fetches OHLCV candles from Upstox V3 Historical Candle API across 4 timeframes (5m, 1h, 4h, 1d)
2. **Indicator Calculation**: Same `TechnicalIndicators` class computes EMA, MACD, RSI, Bollinger Bands, ATR
3. **AI Decision**: `DeepSeekAI` analyzes multi-timeframe indicators and decides BUY/SELL/HOLD
4. **Order Execution**: `UpstoxClient.place_market_order()` sends order via Upstox V3 Order API
5. **Portfolio Tracking**: Trades logged in same PostgreSQL database

## Differences from Binance

| Feature          | Binance              | Upstox               |
|------------------|----------------------|-----------------------|
| Market           | Crypto               | Indian stocks/F&O     |
| Quantity          | Float (0.001 BTC)   | Integer (whole shares)|
| Currency          | USDT                | INR                   |
| Auth             | API key/secret       | OAuth2 + daily token  |
| Trading hours     | 24/7                | 9:15 AM – 3:30 PM IST|
| Product types     | Spot                | Intraday/Delivery/MTF |
| Instrument ID     | BTCUSDT             | NSE_EQ\|INE...        |

## Running Both Bots

You can run Binance and Upstox bots simultaneously:

```bash
# Start server
python main.py

# In separate terminals or via API:
# Start Binance bot
curl -X POST http://localhost:8000/binance/start

# Start Upstox bot
curl -X POST http://localhost:8000/upstox/start
```

## Testing

```bash
pytest tests/test_upstox_client.py -v
```

## File Structure

```
app/
  upstox_client.py       # Upstox API wrapper (REST calls)
  upstox_trading_bot.py  # Trading bot logic for Upstox
  config.py              # Updated with Upstox settings
  # Unchanged files:
  binance_client.py      # Existing Binance client
  trading_bot.py         # Existing Binance bot
  deepseek_ai.py         # Shared AI engine
  indicators.py          # Shared technical indicators
  database.py            # Shared database models
tests/
  test_upstox_client.py  # Upstox-specific tests
```
