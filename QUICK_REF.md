# 🚀 AI Trading Bot - Quick Reference

## One-Minute Setup

```bash
# 1. Configure API keys
nano .env

# 2. Verify everything works
python verify_startup.py

# 3. Start the bot
python main.py

# 4. Open dashboard
# http://localhost:8000/docs
```

---

## Testing Scripts

| Script | Purpose | Time | When to Use |
|--------|---------|------|------------|
| `verify_startup.py` | Quick module check | 2s | Before running bot |
| `test_db_connection.py` | Database test | 3s | Troubleshooting DB |
| `test_setup.py` | Full integration | 5s | After config changes |

---

## Key Files

```
.env                    # Your configuration (EDIT THIS!)
.env.example            # Configuration template
requirements.txt        # Python dependencies
main.py                 # Start the bot here

app/
├── config.py           # Settings management
├── database.py         # PostgreSQL models
├── binance_client.py   # Exchange API
├── deepseek_ai.py      # AI integration
└── trading_bot.py      # Bot logic
```

---

## Common Commands

```bash
# Verify setup
python verify_startup.py

# Test database
python test_db_connection.py

# Full configuration test
python test_setup.py

# Start the bot
python main.py

# View API docs
# Open: http://localhost:8000/docs

# Check current status
curl http://localhost:8000/bot/status

# Start trading
curl -X POST http://localhost:8000/bot/start

# Stop trading
curl -X POST http://localhost:8000/bot/stop
```

---

## Environment Variables (.env)

```env
# Required - Get from Binance
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=True              # Use testnet first!

# Required - Get from DeepSeek
DEEPSEEK_API_KEY=your_key_here

# Optional - Customize behavior
TRADING_PAIR=BTCUSDT              # What to trade
TRADING_QUANTITY=0.001            # Position size
CHECK_INTERVAL_SECONDS=60         # How often to check
MAX_DAILY_TRADES=10               # Daily limit
```

---

## API Endpoints

### Bot Control
- `POST /bot/start` - Start trading
- `POST /bot/stop` - Stop trading
- `GET /bot/status` - Current status

### Data
- `GET /portfolio` - Your positions
- `GET /trades` - Trade history
- `GET /` - Health check

### Documentation
- `http://localhost:8000/docs` - Interactive API docs
- `http://localhost:8000/redoc` - API reference

---

## Database

**Type**: PostgreSQL (Neon)  
**Tables**:
- `trades` - Every trade executed
- `portfolio` - Current positions
- `bot_metrics` - Performance stats

---

## Troubleshooting

**Module not found?**
```bash
pip install -r requirements.txt
```

**Database won't connect?**
```bash
python test_db_connection.py
```

**API keys not working?**
```bash
python test_setup.py
```

**Port 8000 in use?**
```env
# Edit .env
API_PORT=8001
```

---

## Architecture

```
Your Computer
├── main.py (FastAPI)
│   ├── Trading Bot Loop
│   │   ├── Binance API → Get prices
│   │   ├── Calculate indicators
│   │   ├── DeepSeek AI → Get decision
│   │   ├── Execute trade (if confident)
│   │   └── Log to PostgreSQL
│   └── REST API (http://localhost:8000)
└── PostgreSQL (Neon Cloud)
```

---

## Important ⚠️

- ✅ Start on **TESTNET** (fake funds)
- ✅ Test for **1-2 weeks** before real money
- ✅ Start with **SMALL** position sizes
- ✅ Keep **API KEYS** in .env (never git commit)
- ✅ Monitor the bot **regularly**
- ✅ Have a **kill switch** ready

---

## Getting Help

1. Check `TESTING_GUIDE.md` for detailed test info
2. Check `README.md` for full documentation
3. Check `SETUP_COMPLETE.md` for setup status
4. Check `.env.example` for configuration template

---

## Success Checklist

- [ ] `.env` created and filled in
- [ ] `verify_startup.py` passes
- [ ] `test_setup.py` passes
- [ ] `python main.py` starts without errors
- [ ] API docs load at `http://localhost:8000/docs`
- [ ] `/bot/status` endpoint responds

If all ✅, you're ready to trade! 🚀

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-16
