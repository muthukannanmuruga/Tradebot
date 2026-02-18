"""
Manual test script to trigger a trade with mocked high confidence AI
Run this with: python test_manual_trade.py
"""

import asyncio
import sys
from unittest.mock import patch, AsyncMock

sys.path.insert(0, 'e:\\Tradebot')

from app.trading_bot import TradingBot


async def test_single_trade():
    """Test a single BUY trade with high confidence"""
    
    print("🧪 Manual Trade Test")
    print("="*60)
    print("This will simulate a BUY order for BTCUSDT")
    print("with 85% AI confidence (above 60% threshold)")
    print("="*60)
    
    # Initialize bot
    bot = TradingBot()
    
    # Mock Binance responses
    mock_order = {
        'orderId': 999999999,
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'price': '67784.00',
        'executedQty': '0.00001475',
        'fills': [{'price': '67784.00'}],
        'status': 'FILLED'
    }
    
    # Mock market data
    mock_klines_data = {
        'close': 67784.00,
        'high': 68000.00,
        'low': 67500.00
    }
    
    # High confidence BUY decision
    mock_ai_response = {
        'decision': 'BUY',
        'confidence': 0.85,  # 85% confidence
        'reasoning': 'MANUAL TEST: Strong bullish MACD crossover on 5m with higher TF confirmation. RSI at 45 (neutral). EMA trend is bullish.'
    }
    
    with patch.object(bot.binance, 'place_market_order', new_callable=AsyncMock) as mock_order_call, \
         patch.object(bot.binance, 'get_current_price', new_callable=AsyncMock) as mock_price, \
         patch.object(bot.binance, 'get_quantity_from_quote', new_callable=AsyncMock) as mock_qty:
        
        # Setup mocks
        mock_order_call.return_value = mock_order
        mock_price.return_value = 67784.00
        mock_qty.return_value = 0.00001475
        
        # Clear position
        bot.positions['BTCUSDT'] = None
        
        print("\n📊 Pre-Trade Status:")
        print(f"   Symbol: BTCUSDT")
        print(f"   Position: {bot.positions.get('BTCUSDT') or 'None'}")
        print(f"   AI Confidence: 85%")
        print(f"   Threshold: 60%")
        print(f"   Decision: BUY")
        
        # Execute trade directly
        print("\n🚀 Executing trade...")
        
        try:
            await bot.execute_trade(
                symbol='BTCUSDT',
                side='BUY',
                quantity=0.00001475,
                reasoning=mock_ai_response['reasoning'],
                confidence=mock_ai_response['confidence'],
                indicators={'macd': 5.0, 'rsi': 45.0, 'ema_9': 67500}
            )
            
            print("\n📊 Post-Trade Status:")
            print(f"   Position: {bot.positions.get('BTCUSDT')}")
            print(f"   Order Called: {mock_order_call.called}")
            print(f"   Call Count: {mock_order_call.call_count}")
            
            if mock_order_call.called:
                print("\n✅ SUCCESS: Trade executed!")
                print(f"   Order ID: {mock_order['orderId']}")
                print(f"   Quantity: {mock_order['executedQty']} BTC")
                print(f"   Price: ${mock_order['price']}")
            else:
                print("\n❌ FAILED: Order was not placed!")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "🧪"*30)
    asyncio.run(test_single_trade())
    print("🧪"*30 + "\n")
