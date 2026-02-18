#!/usr/bin/env python3
"""
Test script to verify the trading bot setup
"""
import asyncio
import sys
from app.config import config


import pytest

@pytest.mark.asyncio
async def test_configuration():
    """Test if configuration is properly set"""
    print("=" * 60)
    print("AI Trading Bot - Configuration Test")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # Check Binance API
    print("\n🔍 Checking Binance Configuration...")
    if not config.BINANCE_API_KEY or config.BINANCE_API_KEY == "":
        errors.append("BINANCE_API_KEY is not set")
    else:
        print(f"✅ Binance API Key: {config.BINANCE_API_KEY[:10]}...")
    
    if not config.BINANCE_API_SECRET or config.BINANCE_API_SECRET == "":
        errors.append("BINANCE_API_SECRET is not set")
    else:
        print(f"✅ Binance API Secret: {config.BINANCE_API_SECRET[:10]}...")
    
    if config.BINANCE_TESTNET:
        warnings.append("Using Binance TESTNET (good for testing!)")
        print("⚠️  Testnet mode enabled")
    else:
        warnings.append("Using REAL Binance trading (be careful!)")
        print("🚨 REAL trading mode enabled!")
    
    # Check DeepSeek API
    print("\n🔍 Checking DeepSeek Configuration...")
    if not config.DEEPSEEK_API_KEY or config.DEEPSEEK_API_KEY == "":
        errors.append("DEEPSEEK_API_KEY is not set")
    else:
        print(f"✅ DeepSeek API Key: {config.DEEPSEEK_API_KEY[:10]}...")
    
    print(f"✅ DeepSeek Model: deepseek-chat")
    
    # Check Trading Settings
    print("\n🔍 Checking Trading Configuration...")
    print(f"✅ Trading Pair: {config.TRADING_PAIR}")
    print(f"✅ Trading Amount (quote asset): {config.TRADING_AMOUNT_QUOTE}")
    print(f"✅ Check Interval: {config.CHECK_INTERVAL_SECONDS}s")
    print(f"✅ Max Daily Trades: {config.MAX_DAILY_TRADES}")
    
    # Test Binance connection
    print("\n🔍 Testing Binance Connection...")
    try:
        from app.binance_client import BinanceClient
        binance = BinanceClient()
        price = await binance.get_current_price(config.TRADING_PAIR)
        print(f"✅ Connection successful! Current {config.TRADING_PAIR} price: ${price:.2f}")
    except Exception as e:
        errors.append(f"Binance connection failed: {str(e)}")
        print(f"❌ Connection failed: {e}")
    
    # Test DeepSeek connection
    print("\n🔍 Testing DeepSeek AI Connection...")
    try:
        from app.deepseek_ai import DeepSeekAI
        ai = DeepSeekAI()
        
        # Simple test prompt
        test_indicators = {
            "current_price": 50000.0,
            "ema_12": 49500.0,
            "ema_26": 49000.0,
            "ema_trend": "bullish",
            "macd": 100.0,
            "macd_signal": 80.0,
            "macd_histogram": 20.0,
            "macd_trend": "bullish",
            "macd_crossover": "bullish",
            "rsi": 55.0,
            "rsi_zone": "neutral",
            "bb_upper": 51000.0,
            "bb_middle": 50000.0,
            "bb_lower": 49000.0,
            "atr": 500.0,
            "volume": 1000.0
        }
        
        decision = await ai.get_trading_decision(
            config.TRADING_PAIR,
            test_indicators,
            None
        )
        
        print(f"✅ DeepSeek AI responding correctly!")
        print(f"   Test Decision: {decision['decision']}")
        print(f"   Confidence: {decision['confidence']:.2%}")
        
    except Exception as e:
        errors.append(f"DeepSeek AI connection failed: {str(e)}")
        print(f"❌ DeepSeek connection failed: {e}")
    
    # Test Database
    print("\n🔍 Testing Database...")
    try:
        from app.database import init_db, SessionLocal, Trade
        init_db()  # Not async - just call it directly
        db = SessionLocal()
        trade_count = db.query(Trade).count()
        db.close()
        print(f"✅ Database initialized! Current trade count: {trade_count}")
    except Exception as e:
        errors.append(f"Database initialization failed: {str(e)}")
        print(f"❌ Database failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"   - {error}")
        print("\n❌ Configuration has errors. Please fix them before running the bot.")
        print("💡 Make sure to copy .env.example to .env and fill in your API keys!")
        return False
    else:
        print("\n✅ All tests passed! Bot is ready to run.")
        print("\n🚀 To start the bot:")
        print("   python main.py")
        print("\n   Then visit http://localhost:8000/docs for API documentation")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_configuration())
    sys.exit(0 if success else 1)
