"""
Test script to verify buy/sell order execution when AI confidence threshold is met.
Run this with: python test_trade_execution.py
"""

import asyncio
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

# Add app to path
sys.path.insert(0, 'e:\\Tradebot')

from app.trading_bot import TradingBot
from app.database import SessionLocal, Trade, Portfolio
from app.config import config


class TestTradeExecution:
    """Test trading execution with mocked AI and Binance"""
    
    def __init__(self):
        self.bot = TradingBot()
        
    async def test_buy_order_high_confidence(self):
        """Test BUY order when AI confidence >= 0.6"""
        print("\n" + "="*70)
        print("TEST 1: BUY Order - High Confidence (75%)")
        print("="*70)
        
        symbol = "BTCUSDT"
        
        # Mock Binance order response
        mock_order = {
            'orderId': 123456789,
            'symbol': symbol,
            'side': 'BUY',
            'price': '67784.00',
            'executedQty': '0.00001475',
            'status': 'FILLED'
        }
        
        # Mock AI decision - HIGH CONFIDENCE BUY
        mock_ai_decision = {
            'decision': 'BUY',
            'confidence': 0.75,  # 75% > 60% threshold
            'reasoning': 'Test: Strong bullish signal on 5m MACD crossover with 1d confirmation'
        }
        
        # Mock market analysis
        mock_analysis = {
            'indicators': {
                '5min': {
                    'macd': 5.2,
                    'macd_signal': 3.1,
                    'macd_histogram': 2.1,
                    'rsi': 45.0,
                    'ema_9': 67500,
                    'ema_21': 67300,
                    'macd_trend': 'bullish',
                    'ema_trend': 'bullish',
                    'rsi_zone': 'neutral'
                },
                'summary': {
                    'current_price': 67784.00,
                    'timeframe_alignment': {
                        'alignment': 'BULLISH',
                        'macd_bullish_count': 3,
                        'rsi_bullish_count': 3,
                        'ema_bullish_count': 3
                    }
                }
            }
        }
        
        # Patch methods
        with patch.object(self.bot.binance, 'place_market_order', new_callable=AsyncMock) as mock_place_order, \
             patch.object(self.bot.binance, 'get_current_price', new_callable=AsyncMock) as mock_price, \
             patch.object(self.bot.binance, 'get_quantity_from_quote', new_callable=AsyncMock) as mock_qty, \
             patch.object(self.bot.ai, 'get_trading_decision', new_callable=AsyncMock) as mock_ai:
            
            # Configure mocks
            mock_place_order.return_value = mock_order
            mock_price.return_value = 67784.00
            mock_qty.return_value = 0.00001475
            mock_ai.return_value = mock_ai_decision
            
            # Clear any existing position
            self.bot.positions[symbol] = None
            
            print(f"\n📊 Symbol: {symbol}")
            print(f"💰 Current Price: $67,784.00")
            print(f"🎯 AI Decision: BUY")
            print(f"📈 Confidence: 75% (Threshold: 60%)")
            print(f"💵 Trade Amount: ${config.TRADING_AMOUNT_QUOTE} USDT")
            print(f"🔢 Quantity: 0.00001475 BTC")
            
            # Execute decision
            await self.bot._execute_decision(symbol, mock_ai_decision, mock_analysis)
            
            # Verify order was placed
            if mock_place_order.called:
                print(f"\n✅ Order Placed Successfully!")
                print(f"   Order ID: {mock_order['orderId']}")
                print(f"   Side: {mock_order['side']}")
                print(f"   Quantity: {mock_order['executedQty']} BTC")
                print(f"   Price: ${mock_order['price']}")
                
                # Check database
                self._verify_database_entry(symbol, 'BUY')
                
                # Check position tracking
                if self.bot.positions.get(symbol) == "LONG":
                    print(f"✅ Position Updated: {symbol} = LONG")
                else:
                    print(f"❌ Position NOT Updated!")
            else:
                print(f"❌ Order NOT Placed!")
    
    async def test_buy_order_low_confidence(self):
        """Test BUY order SKIPPED when AI confidence < 0.6"""
        print("\n" + "="*70)
        print("TEST 2: BUY Order - Low Confidence (45%) - Should Skip")
        print("="*70)
        
        symbol = "ETHUSDT"
        
        # Mock AI decision - LOW CONFIDENCE BUY
        mock_ai_decision = {
            'decision': 'BUY',
            'confidence': 0.45,  # 45% < 60% threshold
            'reasoning': 'Test: Weak signal, not enough confirmation'
        }
        
        mock_analysis = {
            'indicators': {
                '5min': {},
                'summary': {'current_price': 1965.87}
            }
        }
        
        with patch.object(self.bot.binance, 'place_market_order', new_callable=AsyncMock) as mock_place_order:
            
            self.bot.positions[symbol] = None
            
            print(f"\n📊 Symbol: {symbol}")
            print(f"🎯 AI Decision: BUY")
            print(f"📉 Confidence: 45% (Threshold: 60%)")
            print(f"⚠️  Expected: Order should be SKIPPED")
            
            # Execute decision
            await self.bot._execute_decision(symbol, mock_ai_decision, mock_analysis)
            
            # Verify order was NOT placed
            if not mock_place_order.called:
                print(f"\n✅ Order Correctly SKIPPED (confidence below threshold)")
            else:
                print(f"❌ Order was placed but should have been skipped!")
    
    async def test_sell_order_high_confidence(self):
        """Test SELL order when AI confidence >= 0.6 and position is LONG"""
        print("\n" + "="*70)
        print("TEST 3: SELL Order - High Confidence (82%) - Close Position")
        print("="*70)
        
        symbol = "SOLUSDT"
        
        # Mock existing position
        self.bot.positions[symbol] = "LONG"
        
        # Create portfolio entry
        db = SessionLocal()
        try:
            # Remove existing entry if any
            db.query(Portfolio).filter(Portfolio.pair == symbol).delete()
            db.commit()
            
            # Create new position
            portfolio_entry = Portfolio(
                pair=symbol,
                quantity=0.01176,
                entry_price=85.00,
                current_price=86.50,
                unrealized_pl=0.01764,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(portfolio_entry)
            db.commit()
            print(f"✅ Created test portfolio entry: {symbol} @ $85.00")
        finally:
            db.close()
        
        # Mock Binance order response
        mock_order = {
            'orderId': 987654321,
            'symbol': symbol,
            'side': 'SELL',
            'price': '86.50',
            'executedQty': '0.01176',
            'status': 'FILLED'
        }
        
        # Mock AI decision - HIGH CONFIDENCE SELL
        mock_ai_decision = {
            'decision': 'SELL',
            'confidence': 0.82,  # 82% > 60% threshold
            'reasoning': 'Test: Take profit - target reached, bearish reversal forming'
        }
        
        mock_analysis = {
            'indicators': {
                '5min': {
                    'macd': -2.5,
                    'macd_signal': -1.2,
                    'rsi': 72.0,
                    'macd_trend': 'bearish',
                    'rsi_zone': 'overbought'
                },
                'summary': {'current_price': 86.50}
            }
        }
        
        with patch.object(self.bot.binance, 'place_market_order', new_callable=AsyncMock) as mock_place_order, \
             patch.object(self.bot.binance, 'get_current_price', new_callable=AsyncMock) as mock_price, \
             patch.object(self.bot.binance, 'get_quantity_from_quote', new_callable=AsyncMock) as mock_qty:
            
            mock_place_order.return_value = mock_order
            mock_price.return_value = 86.50
            mock_qty.return_value = 0.01176
            
            print(f"\n📊 Symbol: {symbol}")
            print(f"💰 Entry Price: $85.00")
            print(f"💰 Current Price: $86.50")
            print(f"📈 Unrealized P&L: $0.01764 (+1.76%)")
            print(f"🎯 AI Decision: SELL")
            print(f"📈 Confidence: 82% (Threshold: 60%)")
            print(f"🎯 Current Position: LONG")
            
            # Execute decision
            await self.bot._execute_decision(symbol, mock_ai_decision, mock_analysis)
            
            # Verify order was placed
            if mock_place_order.called:
                print(f"\n✅ SELL Order Placed Successfully!")
                print(f"   Order ID: {mock_order['orderId']}")
                print(f"   Side: {mock_order['side']}")
                print(f"   Quantity: {mock_order['executedQty']} SOL")
                print(f"   Price: ${mock_order['price']}")
                
                # Check database
                self._verify_database_entry(symbol, 'SELL')
                
                # Check position tracking
                if self.bot.positions.get(symbol) is None:
                    print(f"✅ Position Cleared: {symbol} = None")
                else:
                    print(f"❌ Position NOT Cleared!")
                
                # Check portfolio entry removed
                db = SessionLocal()
                try:
                    entry = db.query(Portfolio).filter(Portfolio.pair == symbol).first()
                    if entry is None:
                        print(f"✅ Portfolio Entry Removed")
                    else:
                        print(f"❌ Portfolio Entry Still Exists!")
                finally:
                    db.close()
            else:
                print(f"❌ SELL Order NOT Placed!")
    
    async def test_hold_decision(self):
        """Test HOLD decision - no orders should be placed"""
        print("\n" + "="*70)
        print("TEST 4: HOLD Decision - No Action")
        print("="*70)
        
        symbol = "BTCUSDT"
        
        # Mock AI decision - HOLD
        mock_ai_decision = {
            'decision': 'HOLD',
            'confidence': 0.95,  # High confidence to hold
            'reasoning': 'Test: Market conditions not favorable for entry or exit'
        }
        
        mock_analysis = {
            'indicators': {
                '5min': {},
                'summary': {'current_price': 67784.00}
            }
        }
        
        with patch.object(self.bot.binance, 'place_market_order', new_callable=AsyncMock) as mock_place_order:
            
            self.bot.positions[symbol] = None
            
            print(f"\n📊 Symbol: {symbol}")
            print(f"🎯 AI Decision: HOLD")
            print(f"📊 Confidence: 95%")
            print(f"⏸️  Expected: No order should be placed")
            
            # Execute decision
            await self.bot._execute_decision(symbol, mock_ai_decision, mock_analysis)
            
            # Verify NO order was placed
            if not mock_place_order.called:
                print(f"\n✅ Correctly HELD position - No order placed")
            else:
                print(f"❌ Order was placed but should have held!")
    
    def _verify_database_entry(self, symbol, side):
        """Verify trade was recorded in database"""
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(
                Trade.pair == symbol,
                Trade.side == side
            ).order_by(Trade.created_at.desc()).first()
            
            if trade:
                print(f"\n✅ Database Entry Created:")
                print(f"   Pair: {trade.pair}")
                print(f"   Side: {trade.side}")
                print(f"   Quantity: {trade.quantity}")
                print(f"   Price: ${trade.entry_price or trade.exit_price}")
                print(f"   Status: {trade.status}")
                print(f"   Order ID: {trade.order_id}")
                if trade.confidence:
                    print(f"   Confidence: {trade.confidence:.2%}")
            else:
                print(f"❌ No database entry found for {symbol} {side}")
        finally:
            db.close()
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        print("\n" + "🧪" * 35)
        print("TRADE EXECUTION TEST SUITE")
        print("Testing buy/sell orders with AI confidence threshold")
        print("🧪" * 35)
        
        try:
            await self.test_buy_order_high_confidence()
            await asyncio.sleep(1)
            
            await self.test_buy_order_low_confidence()
            await asyncio.sleep(1)
            
            await self.test_sell_order_high_confidence()
            await asyncio.sleep(1)
            
            await self.test_hold_decision()
            
            print("\n" + "="*70)
            print("✅ ALL TESTS COMPLETED")
            print("="*70)
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test runner"""
    test_suite = TestTradeExecution()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
