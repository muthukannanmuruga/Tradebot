# Migration: Binance Product Type Change (I → SPOT)

## Date
February 25, 2026

## Overview
Changed Binance product type designation from `"I"` (Intraday) to `"SPOT"` to use proper cryptocurrency trading terminology.

## Motivation
- **Clarity**: "SPOT" is standard crypto terminology, "I" (Intraday) is stock market terminology
- **Separation**: Maintains clear distinction between Upstox (I/D/MTF) and Binance (SPOT/MARGIN)
- **Future-proof**: Sets up clean path for MARGIN trading support

## Changes Made

### Code Updates
1. **app/binance_trading_bot.py** - 17 instances changed
   - All `product_type="I"` → `product_type="SPOT"`
   - All queries filtering by `product_type=="I"` → `product_type=="SPOT"`

2. **main.py** - 1 instance changed
   - `/binance/trades` endpoint filter updated

3. **app/config.py**
   - Added clarification: `# Database values: "SPOT" (current), "MARGIN" (future)`

### Documentation Updates
1. **docs/BINANCE_SPOT_TRADING.md**
   - Updated all references from "I" to "SPOT"
   - Added migration SQL section
   - Clarified SPOT vs MARGIN product types

2. **docs/PORTFOLIO_PRODUCT_TYPE.md**
   - Updated Binance product type section
   - Clarified difference between Upstox codes (I/D/MTF) and Binance modes (SPOT/MARGIN)

3. **.env.example**
   - Added BINANCE_PRODUCT_TYPE documentation

### Database Migration
Created **migrations/002_binance_product_type_spot.sql**:
```sql
-- Update Portfolio, Trade, and BotMetrics tables
UPDATE portfolio SET product_type = 'SPOT' 
WHERE pair NOT LIKE '%|%' AND product_type = 'I';

UPDATE trade SET product_type = 'SPOT'
WHERE pair NOT LIKE '%|%' AND product_type = 'I';

UPDATE bot_metrics SET product_type = 'SPOT'
WHERE market = 'binance' AND product_type = 'I';
```

## Running the Migration

### Option 1: Manual SQL (Recommended)
```bash
# Connect to your database
psql $DATABASE_URL

# Run the migration
\i migrations/002_binance_product_type_spot.sql
```

### Option 2: Python Script
```python
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Update Portfolio
    conn.execute(text("""
        UPDATE portfolio SET product_type = 'SPOT' 
        WHERE pair NOT LIKE '%|%' AND product_type = 'I'
    """))
    
    # Update Trade
    conn.execute(text("""
        UPDATE trade SET product_type = 'SPOT'
        WHERE pair NOT LIKE '%|%' AND product_type = 'I'
    """))
    
    # Update BotMetrics
    conn.execute(text("""
        UPDATE bot_metrics SET product_type = 'SPOT'
        WHERE market = 'binance' AND product_type = 'I'
    """))
    
    conn.commit()
    print("✅ Migration completed!")
```

## Verification

### Check Portfolio
```sql
SELECT pair, product_type, quantity 
FROM portfolio 
WHERE pair NOT LIKE '%|%';
-- Expected: All show product_type = 'SPOT'
```

### Check Trades
```sql
SELECT pair, product_type, side, COUNT(*) as count
FROM trade 
WHERE pair NOT LIKE '%|%'
GROUP BY pair, product_type, side;
-- Expected: All Binance trades show product_type = 'SPOT'
```

### Check Metrics
```sql
SELECT market, product_type, total_trades 
FROM bot_metrics 
WHERE market = 'binance';
-- Expected: Shows product_type = 'SPOT'
```

### API Verification
```bash
# Check portfolio endpoint
curl http://localhost:8000/binance/portfolio

# Expected response:
{
  "positions": [
    {
      "pair": "BTCUSDT",
      "product_type": "SPOT",  # ✅ Changed from "I"
      "quantity": 0.001,
      ...
    }
  ]
}
```

## Backward Compatibility

### Breaking Change: ⚠️ YES
This is a **breaking change** if you have external systems querying by `product_type='I'` for Binance data.

**Update external queries**:
```sql
-- OLD (won't work after migration)
SELECT * FROM portfolio WHERE product_type = 'I' AND pair = 'BTCUSDT';

-- NEW (correct)
SELECT * FROM portfolio WHERE product_type = 'SPOT' AND pair = 'BTCUSDT';
```

## Rollback (if needed)

```sql
-- Revert Binance records back to "I"
UPDATE portfolio SET product_type = 'I' 
WHERE pair NOT LIKE '%|%' AND product_type = 'SPOT';

UPDATE trade SET product_type = 'I'
WHERE pair NOT LIKE '%|%' AND product_type = 'SPOT';

UPDATE bot_metrics SET product_type = 'I'
WHERE market = 'binance' AND product_type = 'SPOT';
```

## Product Type Reference

| Market | Old Value | New Value | Meaning |
|--------|-----------|-----------|---------|
| Binance | `I` | `SPOT` | Regular crypto trades (no leverage) |
| Binance | `M` (future) | `MARGIN` (future) | Leveraged crypto trades |
| Upstox | `I` | `I` | Intraday (auto-squareoff at 3:30 PM) |
| Upstox | `D` | `D` | Delivery (held overnight) |
| Upstox | `MTF` | `MTF` | Margin trading facility |

## Files Changed
- ✅ app/binance_trading_bot.py (17 changes)
- ✅ main.py (1 change)
- ✅ app/config.py (comment clarification)
- ✅ docs/BINANCE_SPOT_TRADING.md
- ✅ docs/PORTFOLIO_PRODUCT_TYPE.md
- ✅ .env.example
- ✅ migrations/002_binance_product_type_spot.sql (new file)

## Testing Checklist

- [ ] Run migration SQL
- [ ] Verify all Binance positions show `product_type='SPOT'`
- [ ] Test portfolio endpoint returns correct product_type
- [ ] Test trades endpoint filters correctly
- [ ] Test metrics endpoint shows SPOT metrics
- [ ] Verify risk management queries work (max positions, exposure, etc.)
- [ ] Test new trades are created with `product_type='SPOT'`
- [ ] Verify Upstox positions still show correct product_type (I/D/MTF)

## Notes

- No code changes needed after migration - all updated to use "SPOT"
- Upstox remains unchanged (still uses I/D/MTF)
- Future MARGIN support will use `product_type='MARGIN'`
- Migration affects all environments (testnet and mainnet)
