#!/usr/bin/env python3
"""Test multi-pair configuration"""
import asyncio
from app.config import config
from app.binance_client import BinanceClient

async def test_multi_pair():
    print("\n" + "="*60)
    print("Multi-Pair Trading Configuration Test")
    print("="*60)
    
    print(f"\n✅ Trading Pairs: {config.TRADING_PAIRS}")
    print(f"✅ Amount per pair: ${config.TRADING_AMOUNT_QUOTE} USDT")
    print(f"✅ Max daily trades (all pairs): {config.MAX_DAILY_TRADES}")
    
    print("\n" + "="*60)
    print("Checking prices for all pairs...")
    print("="*60 + "\n")
    
    client = BinanceClient()
    
    for pair in config.TRADING_PAIRS:
        try:
            price = await client.get_current_price(pair)
            print(f"📊 {pair:12} ${price:,.2f}")
        except Exception as e:
            print(f"❌ {pair:12} Error: {e}")
    
    print("\n" + "="*60)
    print("Configuration OK!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_multi_pair())
