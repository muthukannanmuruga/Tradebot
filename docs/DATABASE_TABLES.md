# Database Tables Overview

This document explains all database tables and how they're used.

## 1. **Portfolio Table** 📊

**Purpose:** Tracks current open positions in real-time

**Fields:**
- `pair` - Trading pair (e.g., BTCUSDT)
- `quantity` - Amount held
- `entry_price` - Average entry price
- `current_price` - Latest price
- `unrealized_pl` - Unrealized profit/loss
- `updated_at` - Last update timestamp

**How it works:**
- ✅ **Created** when BUY trades are executed
- 🔄 **Updated** if adding to existing position (averages entry price)
- ❌ **Deleted** when SELL trades close the position
- 📈 **Prices updated** every time `get_portfolio()` is called

**View entries:** `python check_portfolio.py`


## 2. **BotMetrics Table** 📈

**Purpose:** Tracks overall bot performance and statistics

**Fields:**
- `total_trades` - Count of all closed trades
- `winning_trades` - Count of profitable trades
- `losing_trades` - Count of losing trades
- `total_profit_loss` - Cumulative P&L across all trades
- `win_rate` - Percentage of winning trades
- `last_trade_time` - Timestamp of last trade
- `updated_at` - Last metrics update

**How it works:**
- 🔧 **Initialized** automatically when bot starts
- 📊 **Updated** every time a SELL trade closes a position
- ✅ Tracks if trade was profitable or not
- 📈 Recalculates win rate after each trade

**View metrics:** `python check_metrics.py`


## 3. **Trades Table** 💼

**Purpose:** Complete history of all executed trades

**Fields:**
- `pair` - Trading pair
- `side` - BUY or SELL
- `quantity` - Trade quantity
- `entry_price` - Entry price (for BUY trades)
- `exit_price` - Exit price (for SELL trades)
- `profit_loss` - Realized P&L (calculated on SELL)
- `profit_loss_percent` - P&L percentage
- `status` - OPEN, CLOSED, CANCELLED
- `ai_reasoning` - AI's decision reasoning
- `confidence` - AI confidence level
- `created_at` - Trade timestamp
- `order_id` - Binance order ID

**How it works:**
- 📝 **Created** for every BUY and SELL trade
- 💰 **P&L calculated** when position is closed (SELL)
- 📊 Used for historical analysis and reporting


## API Endpoints

### Get Portfolio
```bash
GET /portfolio
```
Returns current portfolio with all open positions and P&L

### Get Metrics
```bash
GET /metrics
```
Returns bot performance statistics:
- Total trades
- Win/loss breakdown
- Total P&L
- Win rate
- Average P&L per trade

### Get Trades
```bash
GET /trades?limit=50
```
Returns trade history


## Verification Scripts

1. **check_portfolio.py** - View current portfolio entries
2. **check_metrics.py** - View bot performance metrics
3. **test_db_connection.py** - Test database connection


## Data Flow Example

### Opening a Position (BUY):
1. Execute BUY trade → Trade record created (status: OPEN)
2. Portfolio entry created with entry price and quantity
3. Position tracking updated

### Closing a Position (SELL):
1. Execute SELL trade → Trade record created (status: CLOSED)
2. Calculate realized P&L from portfolio entry
3. Update closed trade with P&L data
4. **Update BotMetrics:**
   - Increment total_trades
   - Increment winning_trades or losing_trades
   - Add P&L to total_profit_loss
   - Recalculate win_rate
5. Delete portfolio entry (position closed)


## Current Status

✅ **Portfolio Table** - Fully implemented and tracking open positions
✅ **BotMetrics Table** - Fully implemented and tracking performance
✅ **Trades Table** - Fully implemented with P&L tracking

All tables are automatically maintained during trade execution!
