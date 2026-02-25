# Portfolio, Trade & BotMetrics Product Type Support

## Overview

The Portfolio, Trade, and BotMetrics tables now support tracking multiple product types (Intraday, Delivery, MTF) simultaneously. This allows you to:
- Hold both an intraday position AND a delivery position on the same stock without conflicts
- View historical trades filtered by product type
- Compare performance analytics (P&L, win rate, etc.) separately for intraday vs delivery strategies

## Product Type Meanings

### Upstox (Indian Stocks)
- **`I` = Intraday (MIS)** - Positions auto-squareoff at 3:30 PM, supports shorting
- **`D` = Delivery (CNC)** - Positions held overnight, requires full capital
- **`MTF` = Margin Trading** - Leveraged delivery positions

### Binance (Crypto)
- **`SPOT` = Regular Trading** - Buy/sell with full capital, no leverage
  - Positions can be held indefinitely (no auto-squareoff)
  - Uses `/api/v3/order` endpoints
  - No liquidation risk
- **`MARGIN` = Leveraged Trading** _(Not Yet Implemented)_
  - Would use `/sapi/v1/margin/order` endpoints
  - Supports leverage (3x-10x depending on pair)
  - Higher risk with liquidation potential

**Key Difference**: Binance uses explicit trading mode names (SPOT/MARGIN) while Upstox uses position type codes (I/D/MTF).

For detailed Binance SPOT vs MARGIN documentation, see [BINANCE_SPOT_TRADING.md](BINANCE_SPOT_TRADING.md).

## What Changed

### Database Schema

#### Portfolio Table
- **New Column**: `product_type` (VARCHAR, default='I')
  - `I` = Intraday (MIS)
  - `D` = Delivery (CNC)
  - `MTF` = Margin Trading Facility

- **Updated Unique Constraint**: Changed from `(pair)` to `(pair, product_type, is_sandbox)`
  - **Before**: Only one position per instrument (conflict if trying to hold both intraday and delivery)
  - **After**: Multiple positions per instrument (one per product type)

#### Trade Table
- **New Column**: `product_type` (VARCHAR, default='I', indexed)
  - Tracks whether each trade was intraday, delivery, or MTF
  - Enables filtering trade history by product type
  - Supports separate P&L analytics per product type

#### BotMetrics Table
- **New Column**: `product_type` (VARCHAR, default='I', indexed)
  - Tracks performance metrics separately per product type
  - Enables comparison of intraday vs delivery trading performance
  - Win rate, total P&L, average P&L per trade all tracked per product type

- **Updated Unique Constraint**: Changed from `(market, is_sandbox)` to `(market, product_type, is_sandbox)`
  - **Before**: Only one metrics row per market (binance/upstox)
  - **After**: Separate metrics rows per product type (e.g., upstox-intraday vs upstox-delivery)

### Code Changes
- All Portfolio queries in `upstox_trading_bot.py` now filter by `product_type`
- All Trade records created with `product_type` from bot's configured `UPSTOX_PRODUCT_TYPE`
- All BotMetrics queries filter by `product_type` for proper aggregation
- Portfolio, Trade, and Metrics API responses include `product_type` field
- Metrics endpoints now return data grouped by product type

## Migration

### Automatic Migration
Database schema is managed by SQLAlchemy models and created automatically on app startup:

```bash
# Just start the app normally
docker restart TradingBotApp
```

**What happens on startup:**
- `Base.metadata.create_all()` creates all tables based on the current SQLAlchemy models
- Existing tables are not modified (SQLAlchemy only creates missing tables)
- All columns and constraints are defined in the model definitions

**Note:** If you're upgrading from an older version, the database should already have all required columns from previous migrations. New deployments will get the complete schema automatically.

## Usage Examples

### Example 1: Running Two Bots Simultaneously

**Intraday Bot (Container 1)**
```env
UPSTOX_PRODUCT_TYPE=I
UPSTOX_TRADING_PAIRS=NSE_EQ|INE040A01034  # HDFC
```

**Delivery Bot (Container 2)**
```env
UPSTOX_PRODUCT_TYPE=D
UPSTOX_TRADING_PAIRS=NSE_EQ|INE040A01034  # HDFC
```

Both can trade HDFC independently without conflicts.

### Example 2: Cross-Day Delivery Holding

**Day 1 (Delivery Buy)**
```
Product Type: D
Action: BUY 10 HDFC @ ₹1500
Portfolio Entry: 
  - pair: NSE_EQ|INE040A01034
  - product_type: D
  - quantity: 10
  - entry_price: 1500
```

**Day 7 (Delivery Sell)**
```
Action: SELL 10 HDFC @ ₹1650
P&L: (1650 - 1500) × 10 = ₹1500
Portfolio Entry: Removed
Trade Status: CLOSED
```

The position persists across days because:
- 3:30 PM auto-squareoff only runs for intraday (`product_type='I'`)
- Delivery positions stay open until manually closed
- Startup sync validates against `get_holdings()` API

### Example 3: Same-Day Intraday + Delivery

**Morning (Delivery Buy)**
```
Product Type: D
BUY 5 HDFC @ ₹1500
```

**Afternoon (Intraday Trade)**
```
Product Type: I
BUY 10 HDFC @ ₹1520  ← No conflict!
SELL 10 HDFC @ ₹1530  ← Independent of delivery position
```

**Portfolio after market close:**
- Delivery position: 5 HDFC @ ₹1500 (open)
- Intraday position: Auto-squared-off by Upstox at 3:30 PM

## Database Query Examples

### Get All Positions
```sql
SELECT pair, product_type, quantity, entry_price, unrealized_pl
FROM portfolio
WHERE is_sandbox = false;
```

### Get Intraday Positions Only
```sql
SELECT *
FROM portfolio
WHERE product_type = 'I' AND is_sandbox = false;
```

### Get Delivery Holdings Only
```sql
SELECT *
FROM portfolio
WHERE product_type = 'D' AND is_sandbox = false;
```

### Get Trade History by Product Type
```sql
-- All intraday trades
SELECT created_at, pair, side, quantity, profit_loss, status
FROM trades
WHERE product_type = 'I' AND is_sandbox = false
ORDER BY created_at DESC;

-- All delivery trades
SELECT created_at, pair, side, quantity, profit_loss, status
FROM trades
WHERE product_type = 'D' AND is_sandbox = false
ORDER BY created_at DESC;

-- Calculate separate P&L by product type
SELECT 
    product_type,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(profit_loss) as total_pl,
    AVG(profit_loss) as avg_pl_per_trade
FROM trades
WHERE status = 'CLOSED' AND is_sandbox = false
GROUP BY product_type;
```

### Get Performance Metrics by Product Type
```sql
-- View all metrics by product type
SELECT 
    market,
    product_type,
    total_trades,
    winning_trades,
    losing_trades,
    total_profit_loss,
    win_rate,
    last_trade_time
FROM bot_metrics
WHERE is_sandbox = false
ORDER BY market, product_type;

-- Compare intraday vs delivery performance
SELECT 
    product_type,
    total_profit_loss,
    win_rate,
    ROUND(total_profit_loss / NULLIF(total_trades, 0), 2) as avg_pl_per_trade
FROM bot_metrics
WHERE market = 'upstox' AND is_sandbox = false;

-- Example output:
-- product_type | total_profit_loss | win_rate | avg_pl_per_trade
-- -------------+-------------------+----------+-----------------
-- I            | 2500.00           | 65.50    | 125.00
-- D            | 8000.00           | 72.00    | 400.00
```

## API Response Changes

### GET /upstox/portfolio

**Before:**
```json
{
  "positions": [
    {
      "pair": "NSE_EQ|INE040A01034",
      "quantity": 10,
      "entry_price": 1500,
      "unrealized_pl": 150
    }
  ]
}
```

**After:**
```json
{
  "positions": [
    {
      "pair": "NSE_EQ|INE040A01034",
      "product_type": "I",
      "quantity": 10,
      "entry_price": 1500,
      "unrealized_pl": 150
    },
    {
      "pair": "NSE_EQ|INE040A01034",
      "product_type": "D",
      "quantity": 5,
      "entry_price": 1480,
      "unrealized_pl": 100
    }
  ]
}
```

### GET /upstox/metrics & GET /binance/metrics

**Before:**
```json
{
  "total_trades": 50,
  "winning_trades": 32,
  "losing_trades": 18,
  "total_profit_loss": 5400.00,
  "win_rate": 64.00,
  "last_trade_time": "2025-01-15T14:30:00Z",
  "updated_at": "2025-01-15T14:30:05Z",
  "average_pl_per_trade": 108.00
}
```

**After:**
```json
{
  "metrics_by_product_type": [
    {
      "product_type": "I",
      "total_trades": 30,
      "winning_trades": 20,
      "losing_trades": 10,
      "total_profit_loss": 2200.00,
      "win_rate": 66.67,
      "last_trade_time": "2025-01-15T14:30:00Z",
      "updated_at": "2025-01-15T14:30:05Z",
      "average_pl_per_trade": 73.33
    },
    {
      "product_type": "D",
      "total_trades": 20,
      "winning_trades": 12,
      "losing_trades": 8,
      "total_profit_loss": 3200.00,
      "win_rate": 60.00,
      "last_trade_time": "2025-01-14T10:15:00Z",
      "updated_at": "2025-01-14T10:15:10Z",
      "average_pl_per_trade": 160.00
    }
  ],
  "total_profit_loss": 5400.00,
  "total_trades": 50
}
```

Now you can compare:
- **Intraday strategy**: Lower avg P&L per trade (₹73), but higher win rate (66.67%)
- **Delivery strategy**: Higher avg P&L per trade (₹160), but lower win rate (60%)

## Sync Logic

The `_sync_auto_squareoffs()` function handles both product types:

1. **Fetches live data from Upstox:**
   - `get_positions()` → Intraday positions
   - `get_holdings()` → Delivery holdings

2. **Validates DB entries:**
   - If instrument NOT in live data → closes DB entry
   - Handles both `product_type='I'` and `product_type='D'`

3. **Scheduled sync:**
   - **Intraday**: 3:30 PM daily (auto-squareoff)
   - **Delivery**: Only on startup (no scheduled squareoff)

## Backward Compatibility

### Existing Data
- All existing portfolio entries will default to `product_type='I'` (Intraday)
- If you had delivery positions before, manually update them:
  ```sql
  UPDATE portfolio 
  SET product_type = 'D' 
  WHERE pair IN ('NSE_EQ|...');  -- list delivery pairs
  ```

### Binance Bot
- Binance continues to use default `product_type='I'`
- No changes needed to Binance code
- Binance and Upstox use different pair formats (BTCUSDT vs NSE_EQ|...), so no conflicts

## Troubleshooting

### Error: "duplicate key value violates unique constraint"
**Cause**: Trying to create two positions with same (pair, product_type, is_sandbox)

**Solution**: Check if position already exists:
```python
existing = db.query(Portfolio).filter(
    Portfolio.pair == instrument,
    Portfolio.product_type == self.product_type,
    Portfolio.is_sandbox == config.UPSTOX_SANDBOX
).first()
```

### Position Not Syncing After Migration
**Cause**: Old positions missing `product_type`

**Solution**: Restart the bot or manually set `product_type`:
```sql
UPDATE portfolio 
SET product_type = 'I'  -- or 'D' for delivery
WHERE product_type IS NULL;
```

### Getting Wrong Position in Query
**Cause**: Not filtering by `product_type`

**Solution**: Always include product_type filter:
```python
portfolio_entry = db.query(Portfolio).filter(
    Portfolio.pair == instrument,
    Portfolio.product_type == self.product_type,  # ← Required!
    Portfolio.is_sandbox == is_sandbox
).first()
```

## Testing

### Verify Schema Update
```sql
\d portfolio

-- Should show:
-- product_type VARCHAR DEFAULT 'I'
-- Indexes: idx_portfolio_product_type
-- Constraints: uq_portfolio_position UNIQUE (pair, product_type, is_sandbox)
```

### Test Dual Position
```python
# Intraday position
POST /upstox/trade/manual
{
  "instrument_token": "NSE_EQ|INE040A01034",
  "side": "BUY",
  "quantity": 10
}
# Set UPSTOX_PRODUCT_TYPE=I in env

# Delivery position (different bot or change env var)
POST /upstox/trade/manual
{
  "instrument_token": "NSE_EQ|INE040A01034",
  "side": "BUY",
  "quantity": 5
}
# Set UPSTOX_PRODUCT_TYPE=D in env

# Check portfolio
GET /upstox/portfolio
# Should show TWO positions for HDFC with different product_types
```

## Summary

✅ **Before**: Could only hold ONE position per instrument (either intraday OR delivery)  
✅ **After**: Can hold MULTIPLE positions per instrument (intraday AND delivery simultaneously)  
✅ **Migration**: Automatic on startup, manual SQL script available as backup  
✅ **Backward Compatible**: Existing data defaults to intraday (`product_type='I'`)  
✅ **API Enhanced**: Portfolio response now includes `product_type` field
