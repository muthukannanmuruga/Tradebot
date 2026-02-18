# 🚀 Quick Start Guide

Get your AI trading bot up and running in 5 minutes!

## ⚡ Fast Setup (Linux/Mac)

```bash
# 1. Make run script executable
chmod +x run.sh

# 2. Edit .env with your API keys
nano .env

# 3. Run the bot!
./run.sh
```

## 📝 Step-by-Step Setup

### Step 1: Get API Keys

#### Binance API (for trading)
1. Go to [Binance Testnet](https://testnet.binance.vision/)
2. Create account and login
3. Generate API Key and Secret
4. Copy them - you'll need these!

**For real trading** (NOT recommended for beginners):
- Go to [Binance](https://www.binance.com/)
- Account → API Management
- Create API Key (enable "Enable Trading")

#### DeepSeek API (for AI decisions)
1. Go to [DeepSeek Platform](https://platform.deepseek.com/)
2. Sign up / Login
3. Go to API Keys section
4. Create new API key
5. Copy the key

### Step 2: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your keys
nano .env
```

Add your keys:
```env
BINANCE_API_KEY=paste_your_binance_key_here
BINANCE_API_SECRET=paste_your_binance_secret_here
BINANCE_TESTNET=True  # Keep this True for testing!

DEEPSEEK_API_KEY=paste_your_deepseek_key_here
```

### Step 3: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt
```

### Step 4: Test Configuration

```bash
python test_setup.py
```

If you see ✅ all green checks, you're ready!

### Step 5: Start the Bot

```bash
python main.py
```

You should see:
```
🚀 Trading bot started!
📊 Trading pair: BTCUSDT
⏰ Check interval: 60s
```

## 🎯 Using the Bot

### Access the API

Open your browser: http://localhost:8000/docs

You'll see interactive API documentation!

### Start Automatic Trading

**Using API:**
```bash
curl -X POST http://localhost:8000/bot/start
```

**Using Python:**
```python
import requests
response = requests.post("http://localhost:8000/bot/start")
print(response.json())
```

**Using the web UI:**
1. Go to http://localhost:8000/docs
2. Click on `/bot/start`
3. Click "Try it out"
4. Click "Execute"

### Check Bot Status

```bash
curl http://localhost:8000/bot/status
```

### View Recent Trades

```bash
curl http://localhost:8000/trades
```

### Get Market Analysis

```bash
curl http://localhost:8000/market-data/BTCUSDT
```

### Stop the Bot

```bash
curl -X POST http://localhost:8000/bot/stop
```

## 📊 What Happens When Running?

1. **Every 60 seconds** (configurable), the bot:
   - Fetches latest price data from Binance
   - Calculates technical indicators (MACD, RSI, EMA, etc.)
   - Sends data to DeepSeek AI
   - Gets trading decision (BUY/SELL/HOLD)
   - Executes trade if confidence > 60%
   - Logs everything to database

2. **Console Output** looks like:
```
============================================================
⏰ 2024-01-15 10:30:00 UTC
💰 Price: $43,521.50
📊 MACD: 45.23 | Signal: 38.91
📈 RSI: 58.42 (neutral)
🤖 AI Decision: BUY (Confidence: 75.00%)
💭 Reasoning: Strong bullish MACD crossover detected...
============================================================

✅ Trade executed: BUY 0.001 BTCUSDT @ $43521.50
📝 Order ID: 12345678
```

## 🛡️ Safety Tips

### Start with Testnet!
- **Always** use testnet first (BINANCE_TESTNET=True)
- Testnet gives you fake money to practice
- Learn how the bot behaves before risking real money

### Conservative Settings
```env
TRADING_QUANTITY=0.001        # Very small amount
MAX_DAILY_TRADES=5            # Limit daily trades
CHECK_INTERVAL_SECONDS=300    # Check every 5 minutes (not every minute)
```

### Monitor Regularly
- Check console output
- Review trades in database
- Watch for unusual behavior

## 🔧 Common Issues

### "BINANCE_API_KEY is not set"
- Make sure you copied .env.example to .env
- Make sure you edited .env with your keys
- Check there are no extra spaces

### "Connection failed"
- Check your internet connection
- Verify API keys are correct
- For Binance, make sure testnet keys are for testnet

### "DeepSeek connection failed"
- Verify your DeepSeek API key is correct
- Check you have API credits
- Try again in a minute (could be rate limit)

### Bot not making trades
- Check confidence threshold (default is 60%)
- Market might be sideways (no clear signals)
- Check console for AI reasoning
- Verify you started the bot: POST /bot/start

## 📈 Next Steps

### Customize Trading Strategy

Edit `app/deepseek_ai.py` to modify the AI prompt:
- Add more indicators
- Change decision criteria
- Adjust confidence thresholds

### Add Notifications

Add Telegram bot integration to get notified of trades:
```python
# TODO: Add telegram notification code
```

### Backtest Your Strategy

Before real trading:
1. Download historical data
2. Run bot in simulation mode
3. Analyze results
4. Refine strategy

### Scale Up (Carefully!)

When ready for real trading:
1. Set `BINANCE_TESTNET=False`
2. Use real Binance API keys
3. Start with very small amounts
4. Monitor closely for first week
5. Gradually increase if performing well

## 🆘 Need Help?

1. Check console logs for errors
2. Run `python test_setup.py` to diagnose
3. Review README.md for detailed info
4. Check API documentation at /docs

## 🎓 Learning Resources

- [Binance API Docs](https://binance-docs.github.io/apidocs/)
- [Technical Analysis Basics](https://www.investopedia.com/technical-analysis-4427894)
- [MACD Explained](https://www.investopedia.com/terms/m/macd.asp)
- [RSI Explained](https://www.investopedia.com/terms/r/rsi.asp)

---

**Remember: Start small, test thoroughly, never invest more than you can afford to lose! 🚀**
