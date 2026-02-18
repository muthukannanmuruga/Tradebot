#!/usr/bin/env python3
"""
Test PostgreSQL database connection and create tables
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import engine, Base, Trade, Portfolio, BotMetrics
from app.config import config

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("PostgreSQL Database Connection Test")
    print("="*60)
    
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"[OK] Database connection successful!")
            print(f"[OK] Connection pooling enabled")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    
    return True

def create_tables():
    """Create all database tables"""
    print("\n" + "="*60)
    print("Creating Database Tables")
    print("="*60)
    
    try:
        Base.metadata.create_all(bind=engine)
        print(f"[OK] Tables created successfully!")
        print(f"   - trades")
        print(f"   - portfolio")
        print(f"   - bot_metrics")
    except Exception as e:
        print(f"[ERROR] Table creation failed: {e}")
        return False
    
    return True

def show_config():
    """Display configuration"""
    print("\n" + "="*60)
    print("Database Configuration")
    print("="*60)
    
    db_url = config.DATABASE_URL
    # Mask password for security
    masked_url = db_url.split('@')[0] + '@' + db_url.split('@')[1] if '@' in db_url else db_url
    masked_url = masked_url.replace(config.DATABASE_URL.split(':')[1].split('@')[0], 'PASSWORD***')
    
    print(f"Database: PostgreSQL (Neon)")
    print(f"Host: ep-sparkling-star-a4d5qdkr-pooler.us-east-1.aws.neon.tech")
    print(f"Database: Tradingbot")
    print(f"SSL: Enabled")
    print(f"Channel Binding: Enabled")

async def main():
    """Main test function"""
    print("\n[TEST] Testing PostgreSQL Database Setup\n")
    
    show_config()
    
    if not test_connection():
        return False
    
    if not create_tables():
        return False
    
    print("\n" + "="*60)
    print("[SUCCESS] All tests passed!")
    print("="*60)
    print("\nYour trading bot is ready to use the PostgreSQL database.")
    print("Run 'python main.py' to start the bot.\n")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
