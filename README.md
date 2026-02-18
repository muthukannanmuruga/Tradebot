# AI-Powered Cryptocurrency Trading Bot

An automated cryptocurrency trading bot that uses **DeepSeek AI** to make intelligent trading decisions based on technical indicators and market analysis. Built with **FastAPI** and **Binance API**.

## 🌟 Features

- **AI-Powered Trading**: Uses DeepSeek AI to analyze market conditions and make trading decisions
- **Technical Analysis**: Implements multiple indicators (MACD, RSI, EMA, Bollinger Bands, ATR)
- **Real-time Trading**: Automated trading on Binance with configurable intervals
- **Risk Management**: Built-in stop-loss, take-profit, and daily trade limits
- **RESTful API**: Full FastAPI implementation for monitoring and control
- **Database Tracking**: SQLite database for trade history and portfolio tracking
- **Testnet Support**: Test strategies safely on Binance Testnet

## 📊 Technical Indicators

The bot analyzes the following indicators before making decisions:

1. **MACD (Moving Average Convergence Divergence)**
   - Identifies trend changes and momentum
   - Detects bullish/bearish crossovers

2. **RSI (Relative Strength Index)**
   - Identifies overbought (>70) and oversold (<30) conditions
   - Momentum indicator

3. **EMA (Exponential Moving Average)**
   - 12-period and 26-period EMAs
   - Trend direction analysis

4. **Bollinger Bands**
   - Volatility indicator
   - Price position analysis

5. **ATR (Average True Range)**
   - Volatility measurement

## 🛠️ Installation

### Prerequisites

- Python 3.9 or higher
- Binance account with API access
- DeepSeek API key

### Step 1: Clone or Download

```bash
# Create project directory
mkdir ai-trading-bot
cd ai-trading-bot

# Copy all files to this directory
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Required configuration:

```env
# Binance API (Get from https://www.binance.com/en/my/settings/api-management)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=True  # Set to False for real trading

# DeepSeek API (Get from https://platform.deepseek.com/)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Trading Settings
TRADING_SYMBOL=BTCUSDT
TRADING_QUANTITY=0.001  # Amount to trade per order
CHECK_INTERVAL_SECONDS=60  # Check market every 60 seconds
```

## 🚀 Usage

### Start the Server

```bash
# Start FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

## 📡 API Endpoints

### Bot Control

- **POST** `/bot/start` - Start the trading bot
- **POST** `/bot/stop` - Stop the trading bot
- **GET** `/bot/status` - Get current bot status

### Trading

- **POST** `/trade/manual` - Execute a manual trade
- **GET** `/trades` - Get trade history (last 50 trades)

### Market Data

- **GET** `/market-data/{symbol}` - Get current market analysis and indicators
- **GET** `/portfolio` - Get current portfolio and positions

### Example: Start the Bot

```bash
curl -X POST http://localhost:8000/bot/start
```

Response:
```json
{
  "status": "success",
  "message": "Trading bot started",
  "symbol": "BTCUSDT",
  "interval": "60s"
}
```

### Example: Get Market Analysis

```bash
curl http://localhost:8000/market-data/BTCUSDT
```

Response includes:
- Current price
- All technical indicators
- MACD crossover signals
- RSI zones
- EMA trends

## 🤖 How It Works

### Trading Loop

1. **Fetch Market Data**: Gets latest price data and candlesticks from Binance
2. **Calculate Indicators**: Computes all technical indicators (MACD, RSI, EMA, etc.)
3. **Create AI Prompt**: Builds enriched prompt with all market data
4. **AI Decision**: DeepSeek analyzes data and returns BUY/SELL/HOLD decision with confidence
5. **Execute Trade**: If confidence > 0.6, executes the trade on Binance
6. **Log & Track**: Saves trade to database with reasoning and indicators
7. **Wait**: Sleeps for configured interval before next check

### AI Decision Making

The bot sends a comprehensive prompt to DeepSeek containing:

- Current price and trend
- MACD values and crossovers
- RSI levels and zones
- EMA positions
- Bollinger Bands
- Volume data
- Current position (if any)

DeepSeek responds with:
```json
{
  "action": "BUY",
  "confidence": 0.85,
  "reasoning": "Strong bullish MACD crossover with RSI at 45 (neutral zone)..."
}
```

## 🔒 Safety Features

1. **Confidence Threshold**: Only executes trades with >60% confidence
2. **Daily Trade Limit**: Maximum 10 trades per day (configurable)
3. **Position Limits**: Maximum position size controls
4. **Testnet Mode**: Test strategies without risking real money
5. **Error Handling**: Comprehensive error handling and logging

## 📁 Project Structure

```
ai-trading-bot/
├── main.py                  # FastAPI application entry point
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration and settings
│   ├── binance_client.py   # Binance API wrapper
│   ├── deepseek_ai.py      # DeepSeek AI integration
│   ├── indicators.py       # Technical indicators calculation
│   ├── trading_bot.py      # Main trading logic
│   ├── database.py         # Database models and setup
│   └── models.py           # Pydantic models
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 📊 Database Schema

### Trades Table
- Trade history with timestamps
- Buy/Sell prices and quantities
- AI reasoning and confidence
- Indicators snapshot

### Portfolio Table
- Current positions
- Average buy prices
- P&L tracking

### Bot Metrics Table
- Total trades
- Win/loss statistics
- Performance metrics

## ⚙️ Configuration Options

### Trading Parameters

```python
TRADING_SYMBOL = "BTCUSDT"      # Trading pair
TRADING_QUANTITY = 0.001         # Amount per trade
MAX_POSITION_SIZE = 0.01         # Maximum position
CHECK_INTERVAL_SECONDS = 60      # Check frequency
```

### Technical Indicators

```python
EMA_SHORT_PERIOD = 12           # Fast EMA
EMA_LONG_PERIOD = 26            # Slow EMA
MACD_SIGNAL_PERIOD = 9          # Signal line
RSI_PERIOD = 14                 # RSI calculation period
```

### Risk Management (Scalping Strategy)

```python
STOP_LOSS_PERCENT = 0.5         # Stop loss % (at swing low)
TAKE_PROFIT_PERCENT = 1.0       # Take profit % (1:2 risk:reward)
MAX_DAILY_TRADES = 10           # Daily limit
```

**Risk:Reward = 1:2**
- Example on $60,000 entry: Stop at $59,700 (-$300), Target at $60,600 (+$600)

## 🧪 Testing on Binance Testnet

1. Go to [Binance Testnet](https://testnet.binance.vision/)
2. Create a testnet account
3. Generate API keys
4. Set `BINANCE_TESTNET=True` in `.env`
5. Use testnet API keys

The testnet gives you fake funds to test strategies safely!

## 📈 Monitoring

### Check Bot Status

```bash
curl http://localhost:8000/bot/status
```

### View Recent Trades

```bash
curl http://localhost:8000/trades?limit=10
```

### Get Portfolio

```bash
curl http://localhost:8000/portfolio
```

## ⚠️ Disclaimer

**This bot is for educational purposes only. Cryptocurrency trading involves significant risk.**

- Never invest more than you can afford to lose
- Always test on testnet first
- Past performance does not guarantee future results
- The AI makes decisions based on technical analysis, not fundamental analysis
- Markets can be unpredictable and irrational
- Always do your own research (DYOR)

## 🤝 Contributing

Improvements and suggestions are welcome! Areas for enhancement:

- Additional technical indicators
- More sophisticated risk management
- Backtesting functionality
- Multiple trading pair support
- Web dashboard UI
- Telegram notifications
- Advanced position sizing

## 📝 License

MIT License - feel free to use and modify as needed.

## 🆘 Support

If you encounter issues:

1. Check the console logs for error messages
2. Verify your API keys are correct
3. Ensure you have sufficient balance (or testnet funds)
4. Check that Binance API is accessible from your location
5. Verify DeepSeek API key is valid

## 🔮 Future Enhancements

- [ ] Multiple cryptocurrency pair support
- [ ] Backtesting engine
- [ ] Web dashboard for monitoring
- [ ] Telegram bot integration
- [ ] Advanced risk management strategies
- [ ] Support for other exchanges (Coinbase, Kraken)
- [ ] Machine learning model training on historical data
- [ ] Portfolio rebalancing
- [ ] Alert system for significant market movements

---

**Happy Trading! 🚀📈**

Remember: The best trades are the ones you understand!
