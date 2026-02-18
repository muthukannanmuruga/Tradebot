"""
Test script for multi-timeframe analysis
"""
import asyncio
from app.binance_trading_bot import TradingBot
from app.config import config


async def test_multi_timeframe():
    """Test the multi-timeframe analysis functionality"""
    print("🚀 Testing Multi-Timeframe Analysis...")
    print(f"📊 Trading Pairs: {config.TRADING_PAIRS}")
    print(f"⏰ Check Interval: {config.CHECK_INTERVAL_SECONDS} seconds\n")
    
    # Initialize trading bot
    bot = TradingBot()
    
    # Test with first trading pair
    symbol = config.TRADING_PAIRS[0]
    print(f"🔍 Analyzing {symbol}...\n")
    
    try:
        # Get multi-timeframe analysis
        mtf_analysis = await bot.get_multi_timeframe_analysis(symbol)
        
        print("="*70)
        print("MULTI-TIMEFRAME ANALYSIS RESULTS")
        print("="*70)
        
        indicators = mtf_analysis["indicators"]
        alignment = indicators["summary"]["timeframe_alignment"]
        
        print(f"\n📊 Symbol: {symbol}")
        print(f"💰 Current Price: ${indicators['summary']['current_price']:.2f}")
        print(f"\n🔄 Timeframe Alignment: {alignment['alignment']}")
        print(f"   • EMA Bullish: {alignment['ema_bullish_count']}/4 timeframes")
        print(f"   • MACD Bullish: {alignment['macd_bullish_count']}/4 timeframes")
        print(f"   • Higher TF Bias: {'BULLISH' if alignment['higher_timeframes_bullish'] else 'BEARISH' if alignment['higher_timeframes_bearish'] else 'MIXED'}")
        
        print("\n" + "="*70)
        print("DETAILED TIMEFRAME BREAKDOWN")
        print("="*70)
        
        for tf_key, tf_name in [("5min", "5-MINUTE"), ("1hour", "1-HOUR"), ("4hour", "4-HOUR"), ("1day", "1-DAY")]:
            ind = indicators[tf_key]
            print(f"\n{tf_name} Timeframe:")
            print(f"  • Price: ${ind['current_price']:.2f}")
            print(f"  • EMA Trend: {ind['ema_trend'].upper()}")
            print(f"    - EMA 12: ${ind['ema_12']:.2f}")
            print(f"    - EMA 26: ${ind['ema_26']:.2f}")
            print(f"  • MACD: {ind['macd_trend'].upper()}")
            print(f"    - MACD Line: {ind['macd']:.4f}")
            print(f"    - Signal: {ind['macd_signal']:.4f}")
            print(f"    - Crossover: {ind['macd_crossover']}")
            print(f"  • RSI: {ind['rsi']:.2f} ({ind['rsi_zone'].upper()})")
            print(f"  • Bollinger Bands:")
            print(f"    - Upper: ${ind['bb_upper']:.2f}")
            print(f"    - Middle: ${ind['bb_middle']:.2f}")
            print(f"    - Lower: ${ind['bb_lower']:.2f}")
            print(f"  • ATR: {ind['atr']:.4f}")
            print(f"  • Volume: {ind['volume']:.2f}")
        
        print("\n" + "="*70)
        print("✅ Multi-timeframe analysis completed successfully!")
        print("="*70)
        
        # Now test AI decision with this data
        print("\n🤖 Getting AI Trading Decision...\n")
        
        ai_decision = await bot.ai.get_trading_decision(
            symbol,
            indicators,
            None,  # No current position
            portfolio_snapshot=None,
            recent_trades=[]
        )
        
        print("="*70)
        print("AI TRADING DECISION")
        print("="*70)
        print(f"Decision: {ai_decision['decision']}")
        print(f"Confidence: {ai_decision['confidence']:.2%}")
        print(f"Reasoning: {ai_decision['reasoning']}")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_multi_timeframe())
