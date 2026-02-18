"""
Check bot metrics and performance statistics
"""

from app.database import SessionLocal, BotMetrics, Trade
from datetime import datetime


def check_metrics():
    """Check bot performance metrics"""
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("BOT PERFORMANCE METRICS")
        print("="*60)
        
        metrics = db.query(BotMetrics).first()
        
        if not metrics:
            print("❌ No metrics found")
            print("\n📝 Metrics are automatically tracked when trades are executed.")
            print("📝 SELL trades update metrics with realized P&L.")
        else:
            print(f"\n✅ Bot Performance:\n")
            
            print(f"📊 Total Trades: {metrics.total_trades}")
            print(f"✅ Winning Trades: {metrics.winning_trades}")
            print(f"❌ Losing Trades: {metrics.losing_trades}")
            print(f"💰 Total P&L: ${metrics.total_profit_loss:.2f}")
            print(f"📈 Win Rate: {metrics.win_rate:.1f}%")
            
            if metrics.last_trade_time:
                print(f"🕒 Last Trade: {metrics.last_trade_time}")
            
            print(f"🔄 Updated: {metrics.updated_at}")
            
            # Calculate additional stats
            if metrics.total_trades > 0:
                avg_pl = metrics.total_profit_loss / metrics.total_trades
                print(f"\n📊 Average P&L per trade: ${avg_pl:.2f}")
            
            # Show breakdown
            total_completed = metrics.winning_trades + metrics.losing_trades
            if total_completed > 0:
                win_pct = (metrics.winning_trades / total_completed) * 100
                loss_pct = (metrics.losing_trades / total_completed) * 100
                print(f"\n📊 Win/Loss Breakdown:")
                print(f"   ✅ Wins: {metrics.winning_trades} ({win_pct:.1f}%)")
                print(f"   ❌ Losses: {metrics.losing_trades} ({loss_pct:.1f}%)")
        
        # Show recent closed trades for context
        print("\n" + "="*60)
        print("RECENT CLOSED TRADES (with P&L)")
        print("="*60)
        
        closed_trades = db.query(Trade).filter(
            Trade.side == "SELL",
            Trade.profit_loss != None
        ).order_by(Trade.created_at.desc()).limit(5).all()
        
        if not closed_trades:
            print("\n❌ No closed trades with P&L data found")
        else:
            print(f"\n✅ Last {len(closed_trades)} closed trade(s):\n")
            
            for trade in closed_trades:
                pl_emoji = "✅" if trade.profit_loss > 0 else "❌"
                print(f"{pl_emoji} {trade.pair} - Trade #{trade.id}")
                print(f"   P&L: ${trade.profit_loss:.2f} ({trade.profit_loss_percent:.2f}%)")
                print(f"   Closed: {trade.created_at}")
                print()
        
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    check_metrics()
