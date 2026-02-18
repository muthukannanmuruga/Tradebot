#!/usr/bin/env python3
"""
Complete startup verification for AI Trading Bot
"""
import asyncio
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def verify_all():
    """Verify all components"""
    print("\n" + "="*70)
    print(" [*] AI TRADING BOT - STARTUP VERIFICATION")
    print("="*70 + "\n")
    
    errors = []
    warnings = []
    
    # 1. Check imports
    print("1. Checking Python imports...")
    try:
        from app.config import config
        from app.database import init_db, engine, Trade, Portfolio, BotMetrics
        from app.binance_client import BinanceClient
        from app.deepseek_ai import DeepSeekAI
        from app.indicators import TechnicalIndicators
        from app.binance_trading_bot import TradingBot
        from app.models import BotStatus, PortfolioResponse, MarketAnalysis
        from main import app
        print("   [OK] All modules imported successfully\n")
    except Exception as e:
        errors.append(f"Import failed: {e}")
        print(f"   [ERROR] Import error: {e}\n")
        return errors, warnings
    
    # 2. Check configuration
    print("2. Checking configuration...")
    try:
        if not config.BINANCE_API_KEY:
            warnings.append("BINANCE_API_KEY not set in .env")
            print("   [WARN] BINANCE_API_KEY not configured")
        else:
            print(f"   [OK] Binance API configured")
        
        if not config.DEEPSEEK_API_KEY:
            warnings.append("DEEPSEEK_API_KEY not set in .env")
            print("   [WARN] DEEPSEEK_API_KEY not configured")
        else:
            print(f"   [OK] DeepSeek API configured")
        
        print(f"   [OK] Trading pair: {config.TRADING_PAIR}")
        print(f"   [OK] Testnet mode: {config.BINANCE_TESTNET}")
        print(f"   [OK] Database URL: PostgreSQL (Neon)\n")
    except Exception as e:
        errors.append(f"Configuration check failed: {e}")
        print(f"   [ERROR] Error: {e}\n")
    
    # 3. Check database connection
    print("3. Checking database connection...")
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("   [OK] Database connection successful")
        
        init_db()
        print("   [OK] Database tables initialized\n")
    except Exception as e:
        errors.append(f"Database connection failed: {e}")
        print(f"   [ERROR] Database error: {e}\n")
    
    # 4. Check FastAPI
    print("4. Checking FastAPI application...")
    try:
        from main import app
        routes_count = len(app.routes)
        print(f"   [OK] FastAPI app loaded ({routes_count} routes)")
        print(f"   [OK] API docs available at: http://localhost:8000/docs\n")
    except Exception as e:
        errors.append(f"FastAPI check failed: {e}")
        print(f"   [ERROR] Error: {e}\n")
    
    # 5. Print summary
    print("="*70)
    if not errors:
        print(" [SUCCESS] ALL CHECKS PASSED - READY TO START!")
        print("="*70)
        print("\nNext Steps:\n")
        print("   1. Add API keys to .env (if not already done):")
        print("      - BINANCE_API_KEY")
        print("      - BINANCE_API_SECRET")
        print("      - DEEPSEEK_API_KEY\n")
        print("   2. Start the bot:")
        print("      python main.py\n")
        print("   3. Access API documentation:")
        print("      http://localhost:8000/docs\n")
        return errors, warnings
    else:
        print(" [FAILURE] ERRORS FOUND - FIX THESE BEFORE STARTING\n")
        print("Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print("="*70 + "\n")
        return errors, warnings

if __name__ == "__main__":
    errors, warnings = asyncio.run(verify_all())
    
    if warnings and not errors:
        print("[WARNINGS] (non-blocking):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print()
    
    sys.exit(1 if errors else 0)
