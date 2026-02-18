from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import Optional
import asyncio

from app.trading_bot import TradingBot
from app.database import get_db, init_db
from app.models import BotStatus, PortfolioResponse, MarketAnalysis, TradeCreate
from app.config import config

# Global trading bot instance
trading_bot: Optional[TradingBot] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    global trading_bot
    if trading_bot and trading_bot.is_running:
        await trading_bot.stop()
    print("🛑 Trading bot stopped")


app = FastAPI(
    title="AI Trading Bot",
    description="Automated cryptocurrency trading bot powered by DeepSeek AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "AI Trading Bot",
        "version": "1.0.0"
    }


@app.post("/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the automated trading bot"""
    global trading_bot
    
    if trading_bot and trading_bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    trading_bot = TradingBot()
    background_tasks.add_task(trading_bot.start)
    
    return {
        "status": "success",
        "message": "Trading bot started",
        "symbol": config.TRADING_PAIR,
        "interval": f"{config.CHECK_INTERVAL_SECONDS}s"
    }


@app.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    global trading_bot
    
    if not trading_bot or not trading_bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    await trading_bot.stop()
    
    return {
        "status": "success",
        "message": "Trading bot stopped"
    }


@app.get("/bot/status", response_model=BotStatus)
async def get_bot_status():
    """Get current bot status"""
    global trading_bot
    
    if not trading_bot:
        return BotStatus(
            is_running=False,
            last_check=None,
            total_trades=0,
            current_position=None,
            daily_trades=0,
            max_daily_trades=config.MAX_DAILY_TRADES
        )
    
    return await trading_bot.get_status()


@app.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get current portfolio information"""
    global trading_bot
    
    if not trading_bot:
        # Auto-initialize bot if not started
        trading_bot = TradingBot()
    
    return await trading_bot.get_portfolio()


@app.get("/trades")
async def get_trades(limit: int = 50):
    """Get recent trades"""
    db = next(get_db())
    from app.database import Trade
    
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
    
    return {
        "trades": [
            {
                "id": trade.id,
                "created_at": trade.created_at,
                "pair": trade.pair,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "profit_loss": trade.profit_loss,
                "profit_loss_percent": trade.profit_loss_percent,
                "status": trade.status,
                "ai_reasoning": trade.ai_reasoning,
                "confidence": trade.confidence
            }
            for trade in trades
        ]
    }


@app.get("/metrics")
async def get_metrics():
    """Get bot performance metrics"""
    db = next(get_db())
    from app.database import BotMetrics
    
    metrics = db.query(BotMetrics).first()
    
    if not metrics:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit_loss": 0.0,
            "win_rate": 0.0,
            "last_trade_time": None,
            "updated_at": None
        }
    
    return {
        "total_trades": metrics.total_trades,
        "winning_trades": metrics.winning_trades,
        "losing_trades": metrics.losing_trades,
        "total_profit_loss": metrics.total_profit_loss,
        "win_rate": metrics.win_rate,
        "last_trade_time": metrics.last_trade_time,
        "updated_at": metrics.updated_at,
        "average_pl_per_trade": metrics.total_profit_loss / metrics.total_trades if metrics.total_trades > 0 else 0.0
    }


@app.get("/market-data/{symbol}")
async def get_market_data(symbol: str = "BTCUSDT"):
    """Get current market data and indicators"""
    global trading_bot
    
    if not trading_bot:
        trading_bot = TradingBot()
    
    # Convert short symbol to full trading pair (e.g., "btc" -> "BTCUSDT")
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    data = await trading_bot.get_market_analysis(symbol)
    
    return data


@app.post("/trade/manual")
async def manual_trade(
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    quantity: Optional[float] = None
):
    """Execute a manual trade. If quantity not provided, uses configured TRADING_AMOUNT_QUOTE."""
    global trading_bot
    
    if not trading_bot:
        trading_bot = TradingBot()
    
    if side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    
    # If quantity not provided, calculate based on configured quote amount
    if quantity is None:
        # Use configured amount (default $1 USDT)
        quote_amount = config.TRADING_AMOUNT_QUOTE
        
        # Check minimum notional requirement
        min_notional = await trading_bot.binance.get_min_notional(symbol)
        if quote_amount < min_notional:
            print(f"⚠️  Configured amount ${quote_amount} is below minimum notional ${min_notional}, using minimum")
            quote_amount = min_notional
        
        # Check available balance before auto-calculating quantity
        if side == "BUY":
            usdt_balance = await trading_bot.binance.get_account_balance("USDT")
            
            if usdt_balance < quote_amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient balance. Have ${usdt_balance:.2f} USDT, need at least ${quote_amount:.2f} USDT"
                )
        
        quantity = await trading_bot.binance.get_quantity_from_quote(symbol, quote_amount)
        print(f"📊 Auto-calculated quantity: {quantity} for ${quote_amount} USDT")
    else:
        # Manual quantity provided - validate balance
        if side == "BUY":
            current_price = await trading_bot.binance.get_current_price(symbol)
            required_usdt = quantity * current_price
            usdt_balance = await trading_bot.binance.get_account_balance("USDT")
            
            if usdt_balance < required_usdt * 1.01:  # 1% buffer for fees
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient balance. Have ${usdt_balance:.2f} USDT, need ${required_usdt:.2f} USDT (plus fees)"
                )
    
    result = await trading_bot.execute_trade(symbol, side, quantity, "Manual trade")
    
    return result


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

