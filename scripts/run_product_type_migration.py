"""
Migration Script: Change Binance product_type from "I" to "SPOT"
Date: 2026-02-25

Run this to update all Binance positions to use proper crypto terminology.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Execute the product type migration"""
    print("=" * 60)
    print("🔄 Starting Binance Product Type Migration (I → SPOT)")
    print("=" * 60)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("\n📊 Checking current state...")
                
                # Count records before migration
                portfolio_count = conn.execute(text("""
                    SELECT COUNT(*) FROM portfolio 
                    WHERE pair NOT LIKE '%|%' AND product_type = 'I'
                """)).scalar()
                
                trade_count = conn.execute(text("""
                    SELECT COUNT(*) FROM trades 
                    WHERE pair NOT LIKE '%|%' AND product_type = 'I'
                """)).scalar()
                
                metrics_count = conn.execute(text("""
                    SELECT COUNT(*) FROM bot_metrics 
                    WHERE market = 'binance' AND product_type = 'I'
                """)).scalar()
                
                print(f"   Portfolio records to update: {portfolio_count}")
                print(f"   Trade records to update: {trade_count}")
                print(f"   BotMetrics records to update: {metrics_count}")
                
                if portfolio_count == 0 and trade_count == 0 and metrics_count == 0:
                    print("\n✅ No records to migrate - already up to date!")
                    trans.rollback()
                    return
                
                print("\n🔄 Updating records...")
                
                # Update Portfolio table
                portfolio_result = conn.execute(text("""
                    UPDATE portfolio 
                    SET product_type = 'SPOT' 
                    WHERE pair NOT LIKE '%|%' 
                      AND product_type = 'I'
                """))
                print(f"   ✅ Updated {portfolio_result.rowcount} Portfolio records")
                
                # Update Trade table
                trade_result = conn.execute(text("""
                    UPDATE trades 
                    SET product_type = 'SPOT'
                    WHERE pair NOT LIKE '%|%' 
                      AND product_type = 'I'
                """))
                print(f"   ✅ Updated {trade_result.rowcount} Trade records")
                
                # Update BotMetrics table
                metrics_result = conn.execute(text("""
                    UPDATE bot_metrics 
                    SET product_type = 'SPOT'
                    WHERE market = 'binance' 
                      AND product_type = 'I'
                """))
                print(f"   ✅ Updated {metrics_result.rowcount} BotMetrics records")
                
                # Verify the changes
                print("\n🔍 Verifying migration...")
                
                verification = conn.execute(text("""
                    SELECT 'Portfolio' as table_name, pair, product_type 
                    FROM portfolio 
                    WHERE pair NOT LIKE '%|%'
                    LIMIT 5
                """)).fetchall()
                
                print("\n   Sample Portfolio records:")
                for row in verification:
                    print(f"   - {row.pair}: {row.product_type}")
                
                metrics_verify = conn.execute(text("""
                    SELECT market, product_type, total_trades 
                    FROM bot_metrics 
                    WHERE market = 'binance'
                """)).fetchall()
                
                if metrics_verify:
                    print("\n   BotMetrics:")
                    for row in metrics_verify:
                        print(f"   - {row.market}: {row.product_type} ({row.total_trades} trades)")
                
                # Commit transaction
                trans.commit()
                
                print("\n" + "=" * 60)
                print("✅ Migration completed successfully!")
                print("=" * 60)
                print("\n📝 Summary:")
                print(f"   - Portfolio: {portfolio_result.rowcount} updated")
                print(f"   - Trade: {trade_result.rowcount} updated")
                print(f"   - BotMetrics: {metrics_result.rowcount} updated")
                print("\n🎯 All Binance records now use product_type='SPOT'")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                print("   Transaction rolled back - no changes made")
                raise
                
    except Exception as e:
        print(f"\n❌ Database connection error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n⚠️  This will update product_type from 'I' to 'SPOT' for all Binance records")
    print("   Upstox records (I/D/MTF) will NOT be affected\n")
    
    response = input("Continue with migration? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        run_migration()
    else:
        print("\n❌ Migration cancelled")
        sys.exit(0)
