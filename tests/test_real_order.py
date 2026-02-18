"""
Script to place REAL orders with forced AI confidence for testing.
This uses REAL Binance API calls (testnet) to verify the complete flow.

WARNING: This will place ACTUAL orders on Binance Testnet!
Make sure BINANCE_TESTNET=True in .env

Run with: python test_real_order.py
"""

import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, 'e:\\Tradebot')

from app.trading_bot import TradingBot
from app.config import config


class RealOrderTester:
    """Test real order execution with forced AI confidence"""
    
    def __init__(self):
        self.bot = TradingBot()
        
        # Verify we're on testnet
        if not config.BINANCE_TESTNET:
            print("❌ ERROR: BINANCE_TESTNET must be True for testing!")
            print("❌ Set BINANCE_TESTNET=True in .env file")
            sys.exit(1)
        
        print("✅ Running on TESTNET - Safe to test")
    
    async def test_real_buy_order(self, symbol: str = "BTCUSDT"):
        """
        Place a REAL BUY order with forced high confidence
        
        This will:
        1. Fetch real market data
        2. Get real AI analysis  
        3. Override confidence to 75% (above threshold)
        4. Place ACTUAL order on Binance testnet
        """
        print("\n" + "="*70)
        print("🧪 REAL BUY ORDER TEST")
        print("="*70)
        print(f"Symbol: {symbol}")
        print(f"Amount: ${config.TRADING_AMOUNT_QUOTE} USDT")
        print(f"Testnet: {config.BINANCE_TESTNET}")
        print("="*70)
        
        try:
            # Get REAL multi-timeframe analysis
            print(f"\n📥 Fetching real market data for {symbol}...")
            mtf_analysis = await self.bot.get_multi_timeframe_analysis(symbol)
            
            # Get current price
            current_price = mtf_analysis['indicators']['summary']['current_price']
            print(f"💰 Current Price: ${current_price:,.2f}")
            
            # Display real indicators
            alignment = mtf_analysis["indicators"]["summary"]["timeframe_alignment"]
            print(f"\n🔄 Real Timeframe Alignment: {alignment['alignment']}")
            print(f"   MACD Bullish: {alignment['macd_bullish_count']}/4")
            print(f"   RSI Suitable: {alignment['rsi_bullish_count']}/4")
            print(f"   EMA Bullish: {alignment['ema_bullish_count']}/4")
            
            # Show 5-minute indicators (entry timeframe)
            ind_5m = mtf_analysis['indicators']['5min']
            print(f"\n📊 5-Minute Indicators:")
            print(f"   MACD: {ind_5m['macd']:.4f}")
            print(f"   MACD Signal: {ind_5m['macd_signal']:.4f}")
            print(f"   MACD Histogram: {ind_5m['macd_histogram']:.4f}")
            print(f"   RSI: {ind_5m['rsi']:.2f}")
            print(f"   Trend: {ind_5m['macd_trend']} / {ind_5m['ema_trend']}")
            
            # Get REAL AI decision
            print(f"\n🤖 Getting REAL AI analysis...")
            current_position = self.bot.positions.get(symbol)
            
            ai_decision = await self.bot.ai.get_trading_decision(
                symbol,
                mtf_analysis["indicators"],
                current_position,
                intraday_signal=None,
                portfolio_snapshot=None,
                recent_trades=[]
            )
            
            print(f"\n🎯 Original AI Decision:")
            print(f"   Decision: {ai_decision['decision']}")
            print(f"   Confidence: {ai_decision['confidence']:.2%}")
            print(f"   Reasoning: {ai_decision['reasoning'][:150]}...")
            
            # Ask user if they want to override
            print(f"\n" + "="*70)
            override = input("❓ Force BUY with 75% confidence? (yes/no): ").strip().lower()
            
            if override != 'yes':
                print("❌ Test cancelled")
                return
            
            # Force high confidence BUY
            ai_decision['decision'] = 'BUY'
            ai_decision['confidence'] = 0.75
            ai_decision['reasoning'] = f"[FORCED TEST] Original: {ai_decision['reasoning'][:100]}"
            
            print(f"\n🔄 Overridden AI Decision:")
            print(f"   Decision: BUY (FORCED)")
            print(f"   Confidence: 75% (FORCED - above 60% threshold)")
            
            # Clear any existing position for this test
            self.bot.positions[symbol] = None
            
            # Calculate quantity
            quantity = await self.bot.binance.get_quantity_from_quote(
                symbol,
                config.TRADING_AMOUNT_QUOTE
            )
            print(f"\n💵 Trade Details:")
            print(f"   Quantity: {quantity} {symbol.replace('USDT', '')}")
            print(f"   Value: ${config.TRADING_AMOUNT_QUOTE} USDT")
            print(f"   Price: ${current_price:,.2f}")
            
            # FINAL CONFIRMATION
            print(f"\n" + "⚠️ "*35)
            confirm = input("⚠️  PLACE REAL ORDER NOW? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Order cancelled")
                return
            
            # Execute REAL trade
            print(f"\n🚀 Placing REAL BUY order...")
            await self.bot._execute_decision(symbol, ai_decision, mtf_analysis)
            
            print(f"\n✅ Order execution completed!")
            print(f"📊 Check your position: {self.bot.positions.get(symbol)}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_real_sell_order(self, symbol: str = "BTCUSDT"):
        """
        Place a REAL SELL order (close position) with forced high confidence
        
        Requirements:
        - Must have an open position in the symbol
        """
        print("\n" + "="*70)
        print("🧪 REAL SELL ORDER TEST")
        print("="*70)
        print(f"Symbol: {symbol}")
        print(f"Testnet: {config.BINANCE_TESTNET}")
        print("="*70)
        
        try:
            # Check if we have a position
            current_position = self.bot.positions.get(symbol)
            
            if current_position != "LONG":
                print(f"\n❌ No LONG position found for {symbol}")
                print(f"   Current position: {current_position}")
                print(f"\n💡 Run test_real_buy_order first to open a position")
                return
            
            # Get portfolio entry
            from app.database import SessionLocal, Portfolio
            db = SessionLocal()
            try:
                portfolio_entry = db.query(Portfolio).filter(Portfolio.pair == symbol).first()
                if not portfolio_entry:
                    print(f"❌ Portfolio entry not found for {symbol}")
                    return
                
                print(f"\n📊 Current Position:")
                print(f"   Symbol: {portfolio_entry.pair}")
                print(f"   Quantity: {portfolio_entry.quantity}")
                print(f"   Entry Price: ${portfolio_entry.entry_price:,.2f}")
                print(f"   Current Price: ${portfolio_entry.current_price:,.2f}")
                print(f"   Unrealized P&L: ${portfolio_entry.unrealized_pl:.4f}")
                
                quantity = portfolio_entry.quantity
            finally:
                db.close()
            
            # Get REAL market analysis
            print(f"\n📥 Fetching real market data...")
            mtf_analysis = await self.bot.get_multi_timeframe_analysis(symbol)
            current_price = mtf_analysis['indicators']['summary']['current_price']
            
            # Get REAL AI decision
            print(f"\n🤖 Getting REAL AI analysis...")
            ai_decision = await self.bot.ai.get_trading_decision(
                symbol,
                mtf_analysis["indicators"],
                current_position,
                intraday_signal=None,
                portfolio_snapshot=None,
                recent_trades=[]
            )
            
            print(f"\n🎯 Original AI Decision:")
            print(f"   Decision: {ai_decision['decision']}")
            print(f"   Confidence: {ai_decision['confidence']:.2%}")
            
            # Ask user if they want to override
            print(f"\n" + "="*70)
            override = input("❓ Force SELL with 85% confidence? (yes/no): ").strip().lower()
            
            if override != 'yes':
                print("❌ Test cancelled")
                return
            
            # Force high confidence SELL
            ai_decision['decision'] = 'SELL'
            ai_decision['confidence'] = 0.85
            ai_decision['reasoning'] = f"[FORCED TEST] Closing position for testing"
            
            print(f"\n🔄 Overridden AI Decision:")
            print(f"   Decision: SELL (FORCED)")
            print(f"   Confidence: 85% (FORCED)")
            print(f"\n💰 Will sell: {quantity} {symbol.replace('USDT', '')}")
            print(f"   Expected value: ~${quantity * current_price:.2f}")
            
            # FINAL CONFIRMATION
            print(f"\n" + "⚠️ "*35)
            confirm = input("⚠️  PLACE REAL SELL ORDER NOW? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Order cancelled")
                return
            
            # Execute REAL trade
            print(f"\n🚀 Placing REAL SELL order...")
            await self.bot._execute_decision(symbol, ai_decision, mtf_analysis)
            
            print(f"\n✅ Order execution completed!")
            print(f"📊 Position closed: {self.bot.positions.get(symbol)}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def show_menu(self):
        """Interactive menu for testing"""
        while True:
            print("\n" + "="*70)
            print("🧪 REAL ORDER TESTING MENU (TESTNET)")
            print("="*70)
            print("1. Test REAL BUY order (BTCUSDT)")
            print("2. Test REAL SELL order (BTCUSDT)")
            print("3. Test REAL BUY order (ETHUSDT)")
            print("4. Test REAL SELL order (ETHUSDT)")
            print("5. Show current positions")
            print("6. Check portfolio")
            print("0. Exit")
            print("="*70)
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                await self.test_real_buy_order("BTCUSDT")
            elif choice == "2":
                await self.test_real_sell_order("BTCUSDT")
            elif choice == "3":
                await self.test_real_buy_order("ETHUSDT")
            elif choice == "4":
                await self.test_real_sell_order("ETHUSDT")
            elif choice == "5":
                print("\n📊 Current Positions:")
                for pair, pos in self.bot.positions.items():
                    print(f"   {pair}: {pos or 'None'}")
            elif choice == "6":
                try:
                    portfolio = await self.bot.get_portfolio()
                    print(f"\n💼 Portfolio Summary:")
                    print(f"   Total Balance: ${portfolio['total_balance']:.2f}")
                    print(f"   Available: ${portfolio['available_balance']:.2f}")
                    print(f"   Invested: ${portfolio['total_invested']:.2f}")
                    print(f"   Open Positions: {portfolio['open_positions']}")
                    print(f"   Total P&L: ${portfolio['total_profit_loss']:.4f}")
                    if portfolio['positions']:
                        print(f"\n   Positions:")
                        for pos in portfolio['positions']:
                            print(f"      {pos['pair']}: {pos['quantity']} @ ${pos['entry_price']:.2f}")
                except Exception as e:
                    print(f"   Error: {e}")
            elif choice == "0":
                print("\n👋 Exiting...")
                break
            else:
                print("❌ Invalid option")


async def main():
    """Main test runner"""
    print("\n" + "🚀"*35)
    print("REAL ORDER TESTING SCRIPT")
    print("Uses REAL Binance API calls with forced AI confidence")
    print("🚀"*35)
    
    tester = RealOrderTester()
    await tester.show_menu()


if __name__ == "__main__":
    asyncio.run(main())
