#!/usr/bin/env python3
"""Check REAL account balances (MAINNET - BE CAREFUL!)"""
import asyncio
import os
from dotenv import load_dotenv

# Override testnet setting temporarily
os.environ['BINANCE_TESTNET'] = 'False'

load_dotenv()

from app.binance_client import BinanceClient

async def check_real_balance():
    print("\n" + "="*50)
    print("⚠️  WARNING: CHECKING REAL BINANCE ACCOUNT")
    print("="*50)
    
    client = BinanceClient()
    usdt_balance = await client.get_account_balance('USDT')
    btc_balance = await client.get_account_balance('BTC')
    
    print("\nReal Account Balances:")
    print("="*50)
    print(f"USDT: {usdt_balance:.2f}")
    print(f"BTC: {btc_balance:.8f}")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(check_real_balance())
