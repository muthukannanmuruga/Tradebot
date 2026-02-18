#!/usr/bin/env python3
"""Check account balances"""
import asyncio
from app.binance_client import BinanceClient

async def check_balance():
    client = BinanceClient()
    usdt_balance = await client.get_account_balance('USDT')
    btc_balance = await client.get_account_balance('BTC')
    
    print("\n" + "="*50)
    print("Account Balances")
    print("="*50)
    print(f"USDT: {usdt_balance:.2f}")
    print(f"BTC: {btc_balance:.8f}")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(check_balance())
