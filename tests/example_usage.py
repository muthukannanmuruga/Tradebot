#!/usr/bin/env python3
"""
Example usage script for the AI Trading Bot
Demonstrates how to interact with the bot programmatically
"""
import requests
import time
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_bot_health():
    """Check if bot is running"""
    print_header("Checking Bot Health")
    try:
        response = requests.get(f"{BASE_URL}/")
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"✅ Service: {data['service']}")
        print(f"✅ Version: {data['version']}")
        return True
    except Exception as e:
        print(f"❌ Bot is not running: {e}")
        print("💡 Start the bot with: python main.py")
        return False


def get_market_analysis(symbol="BTCUSDT"):
    """Get current market analysis"""
    print_header(f"Market Analysis for {symbol}")
    try:
        response = requests.get(f"{BASE_URL}/market-data/{symbol}")
        data = response.json()
        
        indicators = data['indicators']
        
        print(f"\n💰 Current Price: ${indicators['current_price']:,.2f}")
        print(f"\n📊 Trend Indicators:")
        print(f"   EMA 12: ${indicators['ema_12']:,.2f}")
        print(f"   EMA 26: ${indicators['ema_26']:,.2f}")
        print(f"   Trend: {indicators['ema_trend'].upper()}")
        
        print(f"\n📈 MACD Analysis:")
        print(f"   MACD Line: {indicators['macd']:.4f}")
        print(f"   Signal Line: {indicators['macd_signal']:.4f}")
        print(f"   Histogram: {indicators['macd_histogram']:.4f}")
        print(f"   Crossover: {indicators['macd_crossover'].upper()}")
        
        print(f"\n🎯 Momentum:")
        print(f"   RSI: {indicators['rsi']:.2f}")
        print(f"   Zone: {indicators['rsi_zone'].upper()}")
        
        print(f"\n📊 Volatility:")
        print(f"   Bollinger Upper: ${indicators['bb_upper']:,.2f}")
        print(f"   Bollinger Middle: ${indicators['bb_middle']:,.2f}")
        print(f"   Bollinger Lower: ${indicators['bb_lower']:,.2f}")
        print(f"   ATR: {indicators['atr']:.2f}")
        
        return data
    
    except Exception as e:
        print(f"❌ Error getting market analysis: {e}")
        return None


def start_bot():
    """Start the trading bot"""
    print_header("Starting Trading Bot")
    try:
        response = requests.post(f"{BASE_URL}/bot/start")
        data = response.json()
        
        if data['status'] == 'success':
            print(f"✅ {data['message']}")
            print(f"📊 Symbol: {data['symbol']}")
            print(f"⏰ Interval: {data['interval']}")
            return True
        else:
            print(f"❌ Failed to start bot: {data}")
            return False
    
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return False


def stop_bot():
    """Stop the trading bot"""
    print_header("Stopping Trading Bot")
    try:
        response = requests.post(f"{BASE_URL}/bot/stop")
        data = response.json()
        
        if data['status'] == 'success':
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"❌ Failed to stop bot: {data}")
            return False
    
    except Exception as e:
        print(f"❌ Error stopping bot: {e}")
        return False


def get_bot_status():
    """Get current bot status"""
    print_header("Bot Status")
    try:
        response = requests.get(f"{BASE_URL}/bot/status")
        data = response.json()
        
        print(f"\n🤖 Running: {'Yes ✅' if data['is_running'] else 'No ❌'}")
        print(f"📊 Total Trades: {data['total_trades']}")
        print(f"📈 Current Position: {data.get('current_position', 'None')}")
        print(f"💰 Current Price: ${data.get('current_price', 0):,.2f}")
        
        if data.get('last_check'):
            print(f"⏰ Last Check: {data['last_check']}")
        
        return data
    
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return None


def get_recent_trades(limit=10):
    """Get recent trades"""
    print_header(f"Recent Trades (Last {limit})")
    try:
        response = requests.get(f"{BASE_URL}/trades?limit={limit}")
        data = response.json()
        
        trades = data['trades']
        
        if not trades:
            print("\n📭 No trades yet")
            return
        
        print(f"\n{'#':<4} {'Time':<20} {'Side':<6} {'Price':<12} {'Qty':<10} {'Value':<12}")
        print("-" * 70)
        
        for i, trade in enumerate(trades, 1):
            timestamp = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
            time_str = timestamp.strftime('%Y-%m-%d %H:%M')
            
            print(f"{i:<4} {time_str:<20} {trade['side']:<6} "
                  f"${trade['price']:<11,.2f} {trade['quantity']:<10.4f} "
                  f"${trade['value']:<11,.2f}")
        
        return trades
    
    except Exception as e:
        print(f"❌ Error getting trades: {e}")
        return None


def get_portfolio():
    """Get current portfolio"""
    print_header("Portfolio")
    try:
        response = requests.get(f"{BASE_URL}/portfolio")
        data = response.json()
        
        print(f"\n💵 USDT Balance: ${data['usdt_balance']:,.2f}")
        
        if data.get('positions'):
            print("\n📊 Open Positions:")
            for position in data['positions']:
                print(f"\n   Symbol: {position['symbol']}")
                print(f"   Side: {position['side']}")
                print(f"   Quantity: {position['quantity']}")
                print(f"   Entry Price: ${position['entry_price']:,.2f}")
                print(f"   Current Price: ${position['current_price']:,.2f}")
                print(f"   P&L: ${position['pnl']:,.2f} ({position['pnl_percent']:.2f}%)")
        else:
            print("\n📭 No open positions")
        
        return data
    
    except Exception as e:
        print(f"❌ Error getting portfolio: {e}")
        return None


def manual_trade(symbol="BTCUSDT", side="BUY", quantity=0.001):
    """Execute a manual trade"""
    print_header(f"Manual Trade: {side} {quantity} {symbol}")
    try:
        response = requests.post(
            f"{BASE_URL}/trade/manual",
            params={
                "symbol": symbol,
                "side": side,
                "quantity": quantity
            }
        )
        data = response.json()
        
        print(f"✅ Trade executed!")
        print(f"   Order ID: {data.get('orderId')}")
        print(f"   Symbol: {data.get('symbol')}")
        print(f"   Side: {data.get('side')}")
        print(f"   Quantity: {data.get('executedQty')}")
        
        return data
    
    except Exception as e:
        print(f"❌ Error executing trade: {e}")
        return None


def monitor_bot(duration_seconds=300, check_interval=30):
    """Monitor bot for a specified duration"""
    print_header(f"Monitoring Bot for {duration_seconds}s (Check every {check_interval}s)")
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = int(time.time() - start_time)
        
        print(f"\n[{elapsed}s / {duration_seconds}s] Iteration {iteration}")
        
        # Get status
        status = get_bot_status()
        
        # Wait before next check
        if elapsed < duration_seconds:
            print(f"\n⏳ Waiting {check_interval}s before next check...")
            time.sleep(check_interval)
    
    print_header("Monitoring Complete")


def main():
    """Main example usage"""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     AI Trading Bot - Example Usage Script        ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Check if bot is running
    if not check_bot_health():
        return
    
    while True:
        print("\n" + "=" * 60)
        print("  Select an action:")
        print("=" * 60)
        print("  1. Get Market Analysis")
        print("  2. Start Trading Bot")
        print("  3. Stop Trading Bot")
        print("  4. Get Bot Status")
        print("  5. View Recent Trades")
        print("  6. View Portfolio")
        print("  7. Execute Manual Trade (Test)")
        print("  8. Monitor Bot (5 minutes)")
        print("  0. Exit")
        print("=" * 60)
        
        choice = input("\nEnter choice (0-8): ").strip()
        
        if choice == "1":
            get_market_analysis()
        
        elif choice == "2":
            start_bot()
        
        elif choice == "3":
            stop_bot()
        
        elif choice == "4":
            get_bot_status()
        
        elif choice == "5":
            get_recent_trades()
        
        elif choice == "6":
            get_portfolio()
        
        elif choice == "7":
            symbol = input("Symbol (default BTCUSDT): ").strip() or "BTCUSDT"
            side = input("Side (BUY/SELL): ").strip().upper()
            quantity = float(input("Quantity (default 0.001): ").strip() or "0.001")
            
            confirm = input(f"\n⚠️  Execute {side} {quantity} {symbol}? (yes/no): ")
            if confirm.lower() == "yes":
                manual_trade(symbol, side, quantity)
            else:
                print("❌ Trade cancelled")
        
        elif choice == "8":
            monitor_bot()
        
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
