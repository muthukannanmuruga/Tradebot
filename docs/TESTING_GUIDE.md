# 🧪 Testing & Verification Guide

Your AI Trading Bot has three complementary test scripts to verify different aspects of your setup.

## 📋 Test Scripts Overview

### 1. **verify_startup.py** - Quick Startup Check ⚡
**Purpose**: Fast verification that all modules load correctly
**Use When**: Before running the bot, to ensure no import or initialization errors
**Time**: ~2 seconds
**Tests**:
- ✅ Python module imports
- ✅ Configuration loading
- ✅ Database connection
- ✅ FastAPI application initialization
- ✅ Routes available

```bash
python verify_startup.py
```

**Best For**: Quick pre-flight checks, CI/CD pipelines, startup verification

---

### 2. **test_db_connection.py** - Database Testing 💾
**Purpose**: Focused verification of PostgreSQL database connection and table creation
**Use When**: Troubleshooting database issues or after migrating databases
**Time**: ~3 seconds
**Tests**:
- ✅ PostgreSQL connectivity
- ✅ SSL/TLS connection details
- ✅ Connection pooling
- ✅ Table creation (trades, portfolio, bot_metrics)

```bash
python test_db_connection.py
```

**Best For**: Database troubleshooting, verifying Neon connection, table schema validation

---

### 3. **test_setup.py** - Full Integration Test 🔗
**Purpose**: Comprehensive test of all API connections and configurations
**Use When**: Initial setup or after configuration changes
**Time**: ~5 seconds (depends on network)
**Tests**:
- ✅ Configuration values loaded
- ✅ Binance API connection (fetches live price)
- ✅ DeepSeek AI connection (test inference)
- ✅ Database connection and schema
- ✅ Trading parameters

```bash
python test_setup.py
```

**Best For**: Full setup verification, testing actual API credentials, pre-deployment checklist

---

## 🎯 Which Test to Use?

### Scenario 1: Just set up the bot
```bash
python verify_startup.py     # Fast sanity check
python test_setup.py         # Full verification with API tests
```

### Scenario 2: Troubleshooting database issues
```bash
python test_db_connection.py
```

### Scenario 3: Verifying API credentials work
```bash
python test_setup.py
```

### Scenario 4: Before each production start
```bash
python verify_startup.py
```

### Scenario 5: After modifying configuration
```bash
python test_setup.py
```

---

## 📊 Test Output Examples

### ✅ Successful Startup Verification
```
======================================================================
 🚀 AI TRADING BOT - STARTUP VERIFICATION
======================================================================

1️⃣  Checking Python imports...
   ✅ All modules imported successfully

2️⃣  Checking configuration...
   ✅ Binance API configured
   ✅ DeepSeek API configured
   ✅ Trading pair: BTCUSDT
   ✅ Testnet mode: True
   ✅ Database URL: PostgreSQL (Neon)

3️⃣  Checking database connection...
   ✅ Database connection successful
   ✅ Database tables initialized

4️⃣  Checking FastAPI application...
   ✅ FastAPI app loaded (12 routes)
   ✅ API docs available at: http://localhost:8000/docs

======================================================================
 ✅ ALL CHECKS PASSED - READY TO START!
======================================================================
```

### ✅ Successful Database Test
```
🚀 Testing PostgreSQL Database Setup

============================================================
Database Configuration
============================================================
Database: PostgreSQL (Neon)
Host: ep-sparkling-star-a4d5qdkr-pooler.us-east-1.aws.neon.tech
Database: Tradingbot
SSL: Enabled
Channel Binding: Enabled

============================================================
PostgreSQL Database Connection Test
============================================================
✅ Database connection successful!
✅ Connection pooling enabled

============================================================
Creating Database Tables
============================================================
✅ Tables created successfully!
   - trades
   - portfolio
   - bot_metrics
```

### ✅ Successful Setup Test
```
============================================================
AI Trading Bot - Configuration Test
============================================================

🔍 Checking Binance Configuration...
✅ Binance API Key: your_binan...
✅ Binance API Secret: your_binan...
⚠️  Testnet mode enabled

🔍 Checking DeepSeek Configuration...
✅ DeepSeek API Key: your_deeps...
✅ DeepSeek Model: deepseek-chat

🔍 Checking Trading Configuration...
✅ Trading Pair: BTCUSDT
✅ Trading Quantity: 0.001
✅ Check Interval: 60s
✅ Max Daily Trades: 10

🔍 Testing Binance Connection...
✅ Connection successful! Current BTCUSDT price: $68510.11

🔍 Testing DeepSeek AI Connection...
✅ DeepSeek AI responding correctly!
   Test Decision: HOLD
   Confidence: 65.00%

🔍 Testing Database...
✅ Database initialized! Current trade count: 0

============================================================
TEST SUMMARY
============================================================
✅ All tests passed! Bot is ready to run.
```

---

## 🔴 Troubleshooting Test Failures

### ❌ Import Errors in verify_startup.py
```
ImportError: No module named 'psycopg2'
```
**Solution**:
```bash
pip install -r requirements.txt
```

---

### ❌ Database Connection Failed
```
Connection refused / FATAL: remaining connection slots reserved
```
**Solution**:
```bash
# Check Neon connection string in .env
cat .env | grep DATABASE_URL

# Test connection directly
psql 'postgresql://...your_connection_string...'

# Verify PostgreSQL is running
python test_db_connection.py
```

---

### ❌ Binance API Error (401 Unauthorized)
```
binance.exceptions.BinanceAPIException: Invalid API-key
```
**Solution**:
1. Verify API key is correct in `.env`
2. Check if API key has correct permissions
3. Make sure testnet API key (not mainnet)
4. Regenerate API key if necessary

---

### ❌ DeepSeek API Error (401 Unauthorized)
```
Error: Client error '401 Unauthorized'
```
**Solution**:
1. Verify DeepSeek API key in `.env`
2. Check API credits in DeepSeek console
3. Ensure API key is active
4. Test with curl:
```bash
curl https://api.deepseek.com/user/credit/get \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### ❌ Configuration Not Found
```
BINANCE_API_KEY is not set
```
**Solution**:
```bash
# Create .env from template
cp .env.example .env

# Edit with your credentials
nano .env

# Verify variables are set
cat .env
```

---

## 🚀 Complete Startup Checklist

- [ ] **Configuration**
  ```bash
  cp .env.example .env
  # Edit .env with your API keys
  nano .env
  ```

- [ ] **Verify Setup**
  ```bash
  python verify_startup.py
  ```

- [ ] **Test Database**
  ```bash
  python test_db_connection.py
  ```

- [ ] **Full Integration Test**
  ```bash
  python test_setup.py
  ```

- [ ] **Review Configuration**
  ```bash
  python -c "from app.config import config; print(f'Pair: {config.TRADING_PAIR}, Testnet: {config.BINANCE_TESTNET}')"
  ```

- [ ] **Start the Bot**
  ```bash
  python main.py
  ```

- [ ] **Access Dashboard**
  ```
  http://localhost:8000/docs
  ```

---

## 📈 After Passing Tests

Once all tests pass:

1. **Review the logs** - Check for any warnings
2. **Check current prices** - Verify market data is fetching
3. **Test an API call** - Try `/bot/status` endpoint
4. **Monitor trades** - Watch the trading loop execute
5. **Check database** - Verify trades are logged

---

## 🔍 Advanced Testing

### Check specific configuration
```bash
python -c "from app.config import config; print(vars(config))"
```

### Test database directly
```bash
python -c "from app.database import engine; print(engine)"
```

### Test Binance API directly
```python
python << 'EOF'
import asyncio
from app.binance_client import BinanceClient

async def test():
    client = BinanceClient()
    price = await client.get_current_price("BTCUSDT")
    print(f"BTC Price: ${price}")

asyncio.run(test())
EOF
```

### Test DeepSeek API directly
```python
python << 'EOF'
import asyncio
from app.deepseek_ai import DeepSeekAI

async def test():
    ai = DeepSeekAI()
    indicators = {"current_price": 50000, "rsi": 55}
    decision = await ai.get_trading_decision("BTCUSDT", indicators)
    print(f"Decision: {decision}")

asyncio.run(test())
EOF
```

---

## 📊 Exit Codes

All test scripts return exit codes:

```bash
python verify_startup.py
echo $?  # 0 = success, 1 = failure
```

- **0** = All tests passed ✅
- **1** = One or more tests failed ❌

---

## 🎯 Recommended Testing Workflow

### Daily Before Trading
```bash
python verify_startup.py  # 2 seconds
```

### Weekly Full Check
```bash
python test_setup.py      # 5 seconds
```

### After Changes
```bash
python verify_startup.py
python test_setup.py
```

### Troubleshooting
```bash
python test_db_connection.py    # Database issues
python test_setup.py             # API/Config issues
python verify_startup.py         # Module/import issues
```

---

## 💡 Pro Tips

1. **Automate testing** - Add to your startup script:
   ```bash
   python verify_startup.py && python main.py
   ```

2. **Log test results** - Save output for debugging:
   ```bash
   python test_setup.py > test_log.txt 2>&1
   ```

3. **Run in CI/CD** - Use exit codes:
   ```bash
   python verify_startup.py || exit 1
   python test_setup.py || exit 1
   python main.py
   ```

4. **Schedule tests** - Run periodically:
   ```bash
   # Every 6 hours
   0 */6 * * * cd /home/user/Tradebot && python verify_startup.py
   ```

---

## 📞 Support

If tests fail:
1. Check `.env` configuration
2. Verify API credentials work
3. Check internet connectivity
4. Review error messages carefully
5. Check application logs
6. Verify database connection

---

**All three tests work together to ensure your bot is production-ready! 🚀**
