"""
Check portfolio table entries
"""

from app.database import SessionLocal, Portfolio, Trade
from datetime import datetime


def check_portfolio():
    """Check portfolio table entries"""
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("PORTFOLIO TABLE ENTRIES")
        print("="*60)
        
        entries = db.query(Portfolio).all()
        
        if not entries:
            print("❌ No portfolio entries found")
            print("\n📝 Portfolio entries are created when BUY trades are executed.")
            print("📝 They are removed when SELL trades close positions.")
        else:
            print(f"\n✅ Found {len(entries)} portfolio entry(ies):\n")
            
            for entry in entries:
                print(f"🔹 {entry.pair}")
                print(f"   Quantity: {entry.quantity}")
                print(f"   Entry Price: ${entry.entry_price:.2f}")
                print(f"   Current Price: ${entry.current_price:.2f}")
                print(f"   Unrealized P&L: ${entry.unrealized_pl:.2f}")
                print(f"   Updated: {entry.updated_at}")
                print()
        
        # Show trades for reference
        print("\n" + "="*60)
        print("RECENT TRADES (for reference)")
        print("="*60)
        
        trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(5).all()
        
        if not trades:
            print("❌ No trades found")
        else:
            print(f"\n✅ Last {len(trades)} trade(s):\n")
            
            for trade in trades:
                print(f"🔹 Trade #{trade.id}")
                print(f"   Pair: {trade.pair}")
                print(f"   Side: {trade.side}")
                print(f"   Quantity: {trade.quantity}")
                print(f"   Price: ${trade.entry_price if trade.side == 'BUY' else trade.exit_price:.2f}")
                print(f"   Status: {trade.status}")
                print(f"   Created: {trade.created_at}")
                print()
        
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    check_portfolio()
