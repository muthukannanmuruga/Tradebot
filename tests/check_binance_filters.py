"""
Quick script to check Binance symbol filters and validate quantity calculation
"""

import asyncio
import sys

sys.path.insert(0, 'e:\\Tradebot')

from app.binance_client import BinanceClient
from app.config import config


async def check_symbol_filters(symbol: str = "BTCUSDT"):
    """Check symbol filters and test quantity calculation"""
    
    print(f"\n{'='*70}")
    print(f"🔍 Checking Binance Filters for {symbol}")
    print(f"{'='*70}")
    
    client = BinanceClient()
    
    # Get symbol info
    info = client.client.get_symbol_info(symbol)
    
    if not info:
        print(f"❌ Symbol info not found for {symbol}")
        return
    
    print(f"\n📊 Symbol Info:")
    print(f"   Base Asset: {info['baseAsset']}")
    print(f"   Quote Asset: {info['quoteAsset']}")
    print(f"   Status: {info['status']}")
    
    # Get current price
    price = await client.get_current_price(symbol)
    print(f"\n💰 Current Price: ${price:,.2f}")
    
    # Display all filters
    print(f"\n🔧 Filters:")
    for f in info.get('filters', []):
        filter_type = f.get('filterType')
        print(f"\n   {filter_type}:")
        for key, value in f.items():
            if key != 'filterType':
                print(f"      {key}: {value}")
    
    # Test quantity calculation
    print(f"\n{'='*70}")
    print(f"🧪 Testing Quantity Calculation")
    print(f"{'='*70}")
    
    quote_amount = config.TRADING_AMOUNT_QUOTE
    print(f"\nQuote Amount: ${quote_amount} USDT")
    
    try:
        quantity = await client.get_quantity_from_quote(symbol, quote_amount)
        print(f"\n✅ Calculated Quantity: {quantity} {info['baseAsset']}")
        print(f"   Value: ${quantity * price:.4f}")
        
        # Test formatting
        formatted = client.format_quantity(quantity, symbol)
        print(f"\n📝 Formatted Quantity: {formatted}")
        print(f"   Type: {type(formatted)}")
        print(f"   Length: {len(formatted)}")
        
        # Validate against filters
        print(f"\n✅ Validation:")
        for f in info.get('filters', []):
            if f.get('filterType') == 'LOT_SIZE':
                min_qty = float(f.get('minQty', 0))
                max_qty = float(f.get('maxQty', float('inf')))
                step_size = float(f.get('stepSize'))
                
                print(f"   MIN_QTY: {min_qty} - {'✅ Pass' if quantity >= min_qty else '❌ FAIL'}")
                print(f"   MAX_QTY: {max_qty} - {'✅ Pass' if quantity <= max_qty else '❌ FAIL'}")
                print(f"   STEP_SIZE: {step_size}")
                
            if f.get('filterType') == 'MIN_NOTIONAL':
                min_notional = float(f.get('minNotional', 0))
                notional = quantity * price
                print(f"   MIN_NOTIONAL: {min_notional} - {'✅ Pass' if notional >= min_notional else '❌ FAIL'} (current: {notional:.4f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function"""
    print("\n" + "🔍"*35)
    print("BINANCE SYMBOL FILTER CHECKER")
    print("🔍"*35)
    
    # Check for testnet
    if config.BINANCE_TESTNET:
        print("✅ Using TESTNET")
    else:
        print("⚠️  Using MAINNET")
    
    await check_symbol_filters("BTCUSDT")
    
    # Ask if want to check another symbol
    print("\n" + "="*70)
    another = input("Check another symbol? (enter symbol or 'no'): ").strip().upper()
    if another and another != 'NO':
        await check_symbol_filters(another)


if __name__ == "__main__":
    asyncio.run(main())
