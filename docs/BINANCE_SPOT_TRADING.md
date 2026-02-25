# Binance SPOT Trading Configuration

## Overview

The Binance bot currently supports **SPOT trading only**. This means all crypto trades use your actual capital without leverage.

## Product Type: SPOT vs MARGIN

### Database Storage
- All Binance SPOT positions are stored with `product_type="SPOT"` in the database
- Future MARGIN positions will use `product_type="MARGIN"`
- This is separate from Upstox which uses "I" (Intraday), "D" (Delivery), "MTF" (Margin)

### Clear Separation
Binance uses explicit trading mode terminology:
- **SPOT** = Regular buy/sell with full capital (current implementation)
- **MARGIN** = Leveraged trading with borrowed funds (future support)

This makes the data self-documenting and avoids confusion with Upstox's product types.

## Configuration

### BINANCE_PRODUCT_TYPE
```env
# Options: SPOT (current) or MARGIN (future support)
BINANCE_PRODUCT_TYPE=SPOT
```

**Default**: SPOT

**Current Behavior**:
- Uses `/api/v3/order` API endpoints
- `client.create_order()` for market orders
- No leverage applied
- Full capital required for each trade

## SPOT vs MARGIN Trading

| Feature | SPOT (Current) | MARGIN (Not Implemented) |
|---------|----------------|--------------------------|
| API Endpoint | `/api/v3/order` | `/sapi/v1/margin/order` |
| Python Method | `create_order()` | `create_margin_order()` |
| Leverage | None (1x) | 3x-10x (varies by pair) |
| Capital Required | Full amount | Partial (with borrowed funds) |
| Risk | Lower | Higher (liquidation risk) |
| Interest Fees | None | Daily interest on borrowed funds |
| Product Type (DB) | "SPOT" | "MARGIN" (future) |

## Implementation Details

### Current SPOT Implementation

**BinanceClient** ([app/binance_client.py](../app/binance_client.py)):
```python
# Uses SPOT endpoints
order = self.client.create_order(
    symbol=symbol,
    side=side,
    type=ORDER_TYPE_MARKET,
    quantity=formatted_quantity
)
```

**BinanceTradingBot** ([app/binance_trading_bot.py](../app/binance_trading_bot.py)):
```python
# All positions use product_type="SPOT"
portfolio_entry = Portfolio(
    pair=symbol,
    product_type="SPOT",
    quantity=quantity,
    # ...
)
```

### Future MARGIN Support

To add margin trading support:

1. **Update BinanceClient**:
```python
async def place_margin_order(self, symbol: str, side: str, quantity: float, 
                             isolated: bool = False) -> Dict:
    """Place a margin order (cross or isolated)"""
    if isolated:
        order = self.client.create_isolated_margin_order(
            symbol=symbol, side=side, type=ORDER_TYPE_MARKET, 
            quantity=quantity
        )
    else:
        order = self.client.create_margin_order(
            symbol=symbol, side=side, type=ORDER_TYPE_MARKET, 
            quantity=quantity
        )
    return order
```

2. **Add new product_type="MARGIN"** to database
3. **Update risk management** for liquidation monitoring
4. **Add interest fee tracking** for borrowed funds

## Risk Management

### SPOT Trading Risks
- ✅ No liquidation risk (you own the full position)
- ✅ No interest fees
- ⚠️ Limited profit potential (1x only)
- ⚠️ Requires full capital

### Best Practices
1. **Position Sizing**: Use `MAX_POSITION_PER_PAIR` to limit exposure
2. **Portfolio Limits**: Set `MAX_PORTFOLIO_EXPOSURE` for total risk
3. **Stop Loss**: Configure `STOP_LOSS_PERCENT` for downside protection
4. **Take Profit**: Set `TAKE_PROFIT_PERCENT` for exits

## Environment Variables

```env
# ── Binance Trading Mode ──
BINANCE_PRODUCT_TYPE=SPOT          # SPOT (current) or MARGIN (future)

# ── Risk Management (USDT) ──
MAX_POSITION_PER_PAIR=20.0         # Max USDT per trading pair
MAX_PORTFOLIO_EXPOSURE=50.0        # Max total USDT across all pairs
BINANCE_MAX_OPEN_POSITIONS=3       # Max concurrent positions

# ── Trade Settings ──
TRADING_AMOUNT_QUOTE=1.0           # USDT per trade
STOP_LOSS_PERCENT=0.5              # 0.5% stop loss
TAKE_PROFIT_PERCENT=1.0            # 1.0% take profit
```

## API Endpoint Reference

### SPOT Endpoints (Current)
- **Place Order**: `POST /api/v3/order`
- **Get Balance**: `GET /api/v3/account`
- **Get Price**: `GET /api/v3/ticker/price`
- **Account Info**: `GET /api/v3/account`

### MARGIN Endpoints (Future)
- **Place Margin Order**: `POST /sapi/v1/margin/order`
- **Margin Account**: `GET /sapi/v1/margin/account`
- **Borrow**: `POST /sapi/v1/margin/loan`
- **Repay**: `POST /sapi/v1/margin/repay`

## Testing

### Verify SPOT Trading
```bash
# Check that all positions show product_type="SPOT"
curl http://localhost:8000/binance/portfolio

# Expected response:
{
  "positions": [
    {
      "pair": "BTCUSDT",
      "product_type": "SPOT",
      "quantity": 0.001,
      ...
    }
  ]
}
```

### Check Configuration
```python
from app.config import config
print(f"Product Type: {config.BINANCE_PRODUCT_TYPE}")  # Should show: SPOT
```

## Migration Notes

**Schema Change**: Existing positions with `product_type="I"` need to be updated to `product_type="SPOT"`.

**Update Query**:
```sql
-- Update all Binance positions from "I" to "SPOT"
UPDATE portfolio SET product_type = 'SPOT' 
WHERE pair NOT LIKE '%|%';  -- Binance pairs don't contain '|'

UPDATE trade SET product_type = 'SPOT'
WHERE pair NOT LIKE '%|%' AND product_type = 'I';

UPDATE bot_metrics SET product_type = 'SPOT'
WHERE market = 'binance' AND product_type = 'I';
```

**Database**: The `product_type` column already exists - we're just changing the values from "I" to "SPOT" for Binance to use proper crypto terminology.

## Summary

✅ **Current Status**: SPOT trading fully implemented  
⏳ **Future**: MARGIN trading planned (requires new API endpoints)  
🔒 **Safety**: SPOT = No liquidation risk, full capital required  
📊 **Tracking**: All trades marked as `product_type="SPOT"` in database
