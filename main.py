from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import json
from typing import Optional
import asyncio

from app.binance_trading_bot import TradingBot
from app.database import get_db, init_db
from app.models import BotStatus, PortfolioResponse, MarketAnalysis, TradeCreate
from app.config import config
from typing import Literal

# Conditional Upstox import
if config.UPSTOX_ENABLED:
    from app.upstox_trading_bot import UpstoxTradingBot

# Global trading bot instances
trading_bot: Optional[TradingBot] = None
upstox_bot = None  # Optional[UpstoxTradingBot]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    init_db()
    yield
    # Shutdown
    global trading_bot, upstox_bot
    if trading_bot and trading_bot.is_running:
        await trading_bot.stop()
    if upstox_bot and upstox_bot.is_running:
        await upstox_bot.stop()
    print("🛑 Trading bots stopped")


app = FastAPI(
    title="AI Trading Bot",
    description="Automated cryptocurrency trading bot powered by DeepSeek AI",
    version="1.0.0",
    lifespan=lifespan
)


def _get_view_is_sandbox(market: str) -> bool:
    """Return True if admin setting chooses 'sandbox' view for a market, otherwise False.

    Falls back to config.BINANCE_TESTNET / config.UPSTOX_SANDBOX when no admin override exists.
    """
    db = next(get_db())
    try:
        from app.database import AdminSetting

        key = f"view_{market}"
        setting = db.query(AdminSetting).filter(AdminSetting.key == key).first()
        if setting and setting.value:
            return setting.value.lower() == "sandbox"
        # fallback
        if market == "binance":
            return config.BINANCE_TESTNET
        if market == "upstox":
            return config.UPSTOX_SANDBOX
        return False
    finally:
        db.close()

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


# ═══════════════════════════════════════════════════════════════════
#  BINANCE ENDPOINTS  (Crypto market)
# ═══════════════════════════════════════════════════════════════════


@app.post("/binance/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the Binance automated trading bot"""
    global trading_bot

    if not config.BINANCE_ENABLED:
        raise HTTPException(status_code=400, detail="Binance is not enabled. Set BINANCE_ENABLED=True in .env")

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


@app.post("/binance/stop")
async def stop_bot():
    """Stop the Binance trading bot"""
    global trading_bot

    if not config.BINANCE_ENABLED:
        raise HTTPException(status_code=400, detail="Binance is not enabled")

    if not trading_bot or not trading_bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    await trading_bot.stop()
    
    return {
        "status": "success",
        "message": "Trading bot stopped"
    }


@app.get("/binance/status", response_model=BotStatus)
async def get_bot_status():
    """Get Binance bot status"""
    global trading_bot

    if not config.BINANCE_ENABLED:
        return BotStatus(
            is_running=False,
            last_check=None,
            total_trades=0,
            current_position=None,
            daily_trades=0,
            max_daily_trades=config.MAX_DAILY_TRADES
        )

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


@app.get("/binance/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get Binance portfolio information"""
    global trading_bot

    if not config.BINANCE_ENABLED:
        raise HTTPException(status_code=400, detail="Binance is not enabled. Set BINANCE_ENABLED=True in .env")

    if not trading_bot:
        # Auto-initialize bot if not started
        trading_bot = TradingBot()
    
    return await trading_bot.get_portfolio()


@app.get("/binance/trades")
async def get_trades(limit: int = 50):
    """Get recent Binance trades"""
    db = next(get_db())
    from app.database import Trade
    
    is_sandbox = _get_view_is_sandbox("binance")
    trades = db.query(Trade).filter(
        Trade.product_type == "SPOT",
        Trade.is_sandbox == is_sandbox
    ).order_by(Trade.created_at.desc()).limit(limit).all()
    
    return {
        "trades": [
            {
                "id": trade.id,
                "created_at": trade.created_at,
                "pair": trade.pair,
                "product_type": trade.product_type,
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


@app.get("/binance/metrics")
async def get_metrics():
    """Get Binance bot performance metrics (grouped by product_type)"""
    db = next(get_db())
    from app.database import BotMetrics
    
    is_sandbox = _get_view_is_sandbox("binance")
    all_metrics = db.query(BotMetrics).filter(
        BotMetrics.market == "binance",
        BotMetrics.is_sandbox == is_sandbox
    ).all()
    
    if not all_metrics:
        return {
            "metrics_by_product_type": [],
            "total_profit_loss": 0.0,
            "total_trades": 0
        }
    
    metrics_list = []
    total_pl = 0.0
    total_trades = 0
    
    for metrics in all_metrics:
        metrics_list.append({
            "product_type": metrics.product_type,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "total_profit_loss": metrics.total_profit_loss,
            "win_rate": metrics.win_rate,
            "last_trade_time": metrics.last_trade_time,
            "updated_at": metrics.updated_at,
            "average_pl_per_trade": metrics.total_profit_loss / metrics.total_trades if metrics.total_trades > 0 else 0.0
        })
        total_pl += metrics.total_profit_loss
        total_trades += metrics.total_trades
    
    return {
        "metrics_by_product_type": metrics_list,
        "total_profit_loss": total_pl,
        "total_trades": total_trades
    }


@app.get("/binance/market-data/{symbol}")
async def get_market_data(symbol: str = "BTCUSDT"):
    """Get Binance market data and indicators"""
    global trading_bot

    if not config.BINANCE_ENABLED:
        raise HTTPException(status_code=400, detail="Binance is not enabled. Set BINANCE_ENABLED=True in .env")

    if not trading_bot:
        trading_bot = TradingBot()
    
    # Convert short symbol to full trading pair (e.g., "btc" -> "BTCUSDT")
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    data = await trading_bot.get_market_analysis(symbol)
    
    return data


@app.post("/binance/trade/manual")
async def manual_trade(
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    quantity: Optional[float] = None
):
    """Execute a manual Binance trade. If quantity not provided, uses configured TRADING_AMOUNT_QUOTE."""""
    global trading_bot

    if not config.BINANCE_ENABLED:
        raise HTTPException(status_code=400, detail="Binance is not enabled. Set BINANCE_ENABLED=True in .env")

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


# ═══════════════════════════════════════════════════════════════════
#  UPSTOX ENDPOINTS  (Indian stock market)
# ═══════════════════════════════════════════════════════════════════


@app.post("/upstox/start")
async def start_upstox_bot(background_tasks: BackgroundTasks):
    """Start the Upstox trading bot"""
    global upstox_bot

    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled. Set UPSTOX_ENABLED=True in .env")

    if upstox_bot and upstox_bot.is_running:
        raise HTTPException(status_code=400, detail="Upstox bot is already running")

    sandbox = getattr(config, "UPSTOX_SANDBOX", False)
    active_token = (
        getattr(config, "UPSTOX_SANDBOX_ACCESS_TOKEN", "") if sandbox
        else config.UPSTOX_ACCESS_TOKEN
    ) or ""

    if not active_token.strip():
        token_var = "UPSTOX_SANDBOX_ACCESS_TOKEN" if sandbox else "UPSTOX_ACCESS_TOKEN"
        raise HTTPException(
            status_code=400,
            detail=(
                f"{token_var} is empty. "
                + ("POST /upstox/set-token with the token from the developer portal." if sandbox
                   else "Call GET /upstox/auth-url, log in, then try again.")
            ),
        )

    upstox_bot = UpstoxTradingBot()
    background_tasks.add_task(upstox_bot.start)

    return {
        "status": "success",
        "message": "Upstox trading bot started",
        "instruments": config.UPSTOX_TRADING_PAIRS,
        "product_type": config.UPSTOX_PRODUCT_TYPE,
        "interval": f"{config.CHECK_INTERVAL_SECONDS}s",
    }


@app.post("/upstox/stop")
async def stop_upstox_bot():
    """Stop the Upstox trading bot"""
    global upstox_bot

    if not upstox_bot or not upstox_bot.is_running:
        raise HTTPException(status_code=400, detail="Upstox bot is not running")

    await upstox_bot.stop()
    return {"status": "success", "message": "Upstox trading bot stopped"}


@app.get("/upstox/metrics")
async def get_upstox_metrics():
    """Get Upstox bot performance metrics (grouped by product_type)"""
    db = next(get_db())
    from app.database import BotMetrics

    is_sandbox = _get_view_is_sandbox("upstox")
    all_metrics = db.query(BotMetrics).filter(
        BotMetrics.market == "upstox",
        BotMetrics.is_sandbox == is_sandbox
    ).all()

    if not all_metrics:
        return {
            "metrics_by_product_type": [],
            "total_profit_loss": 0.0,
            "total_trades": 0
        }

    metrics_list = []
    total_pl = 0.0
    total_trades = 0
    
    for metrics in all_metrics:
        metrics_list.append({
            "product_type": metrics.product_type,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "total_profit_loss": metrics.total_profit_loss,
            "win_rate": metrics.win_rate,
            "last_trade_time": metrics.last_trade_time,
            "updated_at": metrics.updated_at,
            "average_pl_per_trade": metrics.total_profit_loss / metrics.total_trades if metrics.total_trades > 0 else 0.0,
        })
        total_pl += metrics.total_profit_loss
        total_trades += metrics.total_trades
    
    return {
        "metrics_by_product_type": metrics_list,
        "total_profit_loss": total_pl,
        "total_trades": total_trades
    }


@app.get("/upstox/status")
async def get_upstox_status():
    """Get Upstox bot status"""
    global upstox_bot

    if not config.UPSTOX_ENABLED:
        return {"enabled": False, "message": "Upstox is not enabled"}

    if not upstox_bot:
        return {
            "enabled": True,
            "is_running": False,
            "last_check": None,
            "total_trades": 0,
            "instruments": config.UPSTOX_TRADING_PAIRS,
        }

    return await upstox_bot.get_status()


@app.get("/upstox/portfolio")
async def get_upstox_portfolio():
    """Get Upstox portfolio"""
    global upstox_bot

    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    if not upstox_bot:
        upstox_bot = UpstoxTradingBot()

    return await upstox_bot.get_portfolio()


@app.get("/upstox/market-data/{instrument_key}")
async def get_upstox_market_data(instrument_key: str):
    """Get Upstox multi-timeframe market data (5m, 1h, 4h, 1d) for an instrument token."""
    global upstox_bot

    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    if not upstox_bot:
        upstox_bot = UpstoxTradingBot()

    return await upstox_bot.get_multi_timeframe_analysis(instrument_key)


@app.post("/upstox/trade/manual")
async def upstox_manual_trade(
    instrument_token: str,
    side: str = "BUY",
    quantity: Optional[int] = None,
):
    """Execute a manual Upstox trade.
    instrument_token can be full 'NSE_EQ|INE848E01016' or bare ISIN 'INE848E01016' (NSE_EQ| auto-prefixed).
    """
    global upstox_bot

    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    if side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")

    # Auto-prefix exchange segment if caller passed a bare ISIN
    if "|" not in instrument_token:
        instrument_token = f"NSE_EQ|{instrument_token}"

    if not upstox_bot:
        upstox_bot = UpstoxTradingBot()

    if quantity is None:
        quantity = await upstox_bot.upstox.get_quantity_from_quote(
            instrument_token, config.UPSTOX_TRADING_AMOUNT
        )

    result = await upstox_bot.execute_trade(
        instrument_token, side, int(quantity), "Manual Upstox trade"
    )
    return result


@app.get("/upstox/orders")
async def get_upstox_orders():
    """List all orders placed today (works in sandbox and live)."""
    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    orders = await client.get_order_book()
    mode = "sandbox" if _get_view_is_sandbox("upstox") else "live"
    return {"mode": mode, "count": len(orders), "orders": orders}


@app.get("/upstox/order/{order_id}")
async def get_upstox_order(order_id: str):
    """Get full history/status of a specific order by order_id."""
    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    detail = await client.get_order_details(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return detail


@app.get("/upstox/trades")
async def get_upstox_trades():
    """List all trades executed today (fills)."""
    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    trades = await client.get_trades()
    mode = "sandbox" if _get_view_is_sandbox("upstox") else "live"
    return {"mode": mode, "count": len(trades), "trades": trades}


@app.delete("/upstox/order/{order_id}")
async def cancel_upstox_order(order_id: str):
    """Cancel an open Upstox order by order_id."""
    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    result = await client.cancel_order(order_id)
    return result

@app.get("/admin/view-environment")
async def admin_view_environment():
    """Return current admin view override for markets (live vs sandbox)."""
    db = next(get_db())
    try:
        from app.database import AdminSetting

        def _read(key: str, default: str) -> str:
            s = db.query(AdminSetting).filter(AdminSetting.key == key).first()
            return s.value if s and s.value else default

        binance_default = "sandbox" if config.BINANCE_TESTNET else "live"
        upstox_default = "sandbox" if config.UPSTOX_SANDBOX else "live"

        return {
            "binance": _read("view_binance", binance_default),
            "upstox": _read("view_upstox", upstox_default),
        }
    finally:
        db.close()

@app.post("/admin/toggle-view")
async def admin_toggle_view(market: Literal["binance", "upstox"], view: Literal["sandbox", "live"]):
    """Set admin view override for a market. Use `view=sandbox` or `view=live`."""
    db = next(get_db())
    try:
        from app.database import AdminSetting

        key = f"view_{market}"
        existing = db.query(AdminSetting).filter(AdminSetting.key == key).first()
        if existing:
            existing.value = view
        else:
            setting = AdminSetting(key=key, value=view)
            db.add(setting)
        db.commit()
        return {"market": market, "view": view, "status": "ok"}
    finally:
        db.close()


@app.get("/upstox/auth-debug")
async def upstox_auth_debug():
    """Diagnostic endpoint – shows the EXACT client_id and redirect_uri that will
    be sent to Upstox. Compare these character-for-character with your portal settings."""
    sandbox = config.UPSTOX_SANDBOX
    raw_sandbox_key = getattr(config, "UPSTOX_SANDBOX_API_KEY", "")
    raw_live_key = config.UPSTOX_API_KEY

    active_key = raw_sandbox_key if (sandbox and raw_sandbox_key) else raw_live_key
    redirect = config.UPSTOX_REDIRECT_URI

    from urllib.parse import quote as _quote
    encoded_redirect = _quote(redirect)
    full_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={active_key}"
        f"&redirect_uri={encoded_redirect}"
    )

    return {
        "mode": "sandbox" if sandbox else "live",
        # Values sent to Upstox – must match portal EXACTLY
        "client_id_sent": active_key,
        "client_id_length": len(active_key),
        "redirect_uri_sent": redirect,
        "redirect_uri_length": len(redirect),
        "redirect_uri_encoded": encoded_redirect,
        # Raw values loaded from .env – check for stray quotes or spaces
        "raw_sandbox_api_key": repr(raw_sandbox_key),
        "raw_live_api_key": repr(raw_live_key),
        "raw_redirect_uri": repr(redirect),
        # Full auth URL for reference
        "full_auth_url": full_url,
        "portal_check": "Go to https://account.upstox.com/developer/apps and confirm client_id and redirect_uri match the values above exactly.",
    }


@app.get("/upstox/token-status")
async def upstox_token_status():
    """Check whether the active Upstox token is set and the bot is ready to start."""
    sandbox = getattr(config, "UPSTOX_SANDBOX", False)
    live_token = (config.UPSTOX_ACCESS_TOKEN or "").strip()
    sandbox_token = (getattr(config, "UPSTOX_SANDBOX_ACCESS_TOKEN", "") or "").strip()
    active_token = sandbox_token if sandbox else live_token
    has_token = bool(active_token)

    api_key = (
        getattr(config, "UPSTOX_SANDBOX_API_KEY", "") if sandbox
        else config.UPSTOX_API_KEY
    )

    if not has_token:
        if sandbox:
            next_step = "POST /upstox/set-token  body: {\"token\": \"<from developer portal>\"}"
        else:
            next_step = "GET /upstox/auth-url → open link → log in → token auto-saved"
    else:
        next_step = "POST /upstox/start"

    return {
        "ready": has_token,
        "mode": "sandbox" if sandbox else "live",
        "token_set": has_token,
        "token_preview": (active_token[:8] + "...") if has_token else None,
        "next_step": next_step,
    }


@app.get("/upstox/auth-url")
async def get_upstox_auth_url():
    """Get the Upstox OAuth2 login URL (live) or sandbox token instructions."""
    if not config.UPSTOX_API_KEY:
        raise HTTPException(status_code=400, detail="UPSTOX_API_KEY is not set")

    sandbox = getattr(config, "UPSTOX_SANDBOX", False)

    if sandbox:
        # Sandbox tokens are generated directly in the developer portal – no OAuth flow
        return {
            "mode": "sandbox",
            "auth_url": None,
            "instructions": [
                "Sandbox apps do NOT use the OAuth redirect flow.",
                "1. Go to https://account.upstox.com/developer/apps",
                "2. Open your SANDBOX app (c2fec908-...).",
                "3. Click the 'Generate Token' button in the portal.",
                "4. Copy the generated access token.",
                "5. POST /upstox/set-token  body: {\"token\": \"<paste token here>\"}",
                "6. Call GET /upstox/token-status to confirm, then POST /upstox/start.",
            ],
        }

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    login_url = client.get_login_url()
    return {
        "mode": "live",
        "auth_url": login_url,
        "instructions": [
            "1. Open auth_url in your browser and log in with Upstox credentials.",
            "2. After login you will be redirected to /upstox/callback automatically.",
            "3. The callback exchanges the code and saves UPSTOX_ACCESS_TOKEN to .env.",
            "4. Call GET /upstox/token-status to confirm the token is set.",
            "5. Call POST /upstox/start to launch the bot.",
        ],
    }


@app.get("/upstox/callback")
async def upstox_callback(code: str = "", state: str = ""):
    """Upstox OAuth2 callback - exchanges auth code for access token (live only).
    Sandbox apps do not use OAuth; tokens are generated directly in the developer portal."""
    sandbox = getattr(config, "UPSTOX_SANDBOX", False)

    if sandbox:
        # Sandbox does not use the OAuth redirect flow at all
        return {
            "mode": "sandbox",
            "status": "not_applicable",
            "message": (
                "Sandbox apps do not use the OAuth callback flow. "
                "Generate a token directly from the developer portal instead."
            ),
            "steps": [
                "1. Go to https://account.upstox.com/developer/apps",
                "2. Open your sandbox app (c2fec908-...).",
                "3. Click 'Generate Token' in the portal.",
                "4. Copy the token and POST /upstox/set-token  body: {\"token\": \"<token>\"}",
            ],
        }

    if not code:
        from fastapi.responses import RedirectResponse
        from app.upstox_client import UpstoxClient
        client = UpstoxClient()
        return RedirectResponse(url=client.get_login_url())

    from app.upstox_client import UpstoxClient
    client = UpstoxClient()
    try:
        token_data = await client.exchange_code_for_token(code)
    except Exception as exc:
        return {
            "status": "error",
            "step": "token_exchange",
            "detail": str(exc),
            "hint": (
                "401 usually means wrong API secret or redirect_uri mismatch. "
                "Check UPSTOX_API_SECRET in .env matches the live app secret shown at "
                "https://account.upstox.com/developer/apps and that the Redirect URI "
                "in the portal is exactly: http://127.0.0.1:8000/upstox/callback (no trailing slash)."
            ),
            "client_id_used": client.api_key,
            "redirect_uri_used": client.redirect_uri,
        }
    access_token = token_data.get("access_token", "")

    # Try to persist the access token into the project's .env file
    saved = False
    save_error = None
    try:
        import os, re

        project_root = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(project_root, ".env")

        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace existing UPSTOX_ACCESS_TOKEN line or append if missing
            token_line = f'UPSTOX_ACCESS_TOKEN="{access_token}"'
            if re.search(r"(?m)^UPSTOX_ACCESS_TOKEN\s*=.*$", content):
                new_content = re.sub(r"(?m)^UPSTOX_ACCESS_TOKEN\s*=.*$", token_line, content)
            else:
                new_content = content.rstrip() + "\n" + token_line + "\n"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Update runtime config value so the app can use it immediately
            try:
                config.UPSTOX_ACCESS_TOKEN = access_token
            except Exception:
                pass

            saved = True
        else:
            save_error = f".env not found at {env_path}"
    except Exception as e:
        save_error = str(e)

    response = {
        "status": "success" if access_token else "error",
        "token_saved_to": "UPSTOX_ACCESS_TOKEN (live)",
        "saved_to_env": saved,
    }
    if save_error:
        response["save_error"] = save_error

    return response


@app.post("/upstox/set-token")
async def upstox_set_token(payload: dict):
    """
    Manually set the Upstox access token (required for sandbox apps).
    Sandbox tokens are generated in the developer portal, not via OAuth.

    Body: { "token": "<access token from portal>" }
    """
    token = (payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="'token' field is required and must not be empty.")

    # Persist to the correct .env variable based on mode
    sandbox = getattr(config, "UPSTOX_SANDBOX", False)
    env_key = "UPSTOX_SANDBOX_ACCESS_TOKEN" if sandbox else "UPSTOX_ACCESS_TOKEN"
    saved = False
    save_error = None
    try:
        import os, re
        project_root = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(project_root, ".env")

        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            token_line = f'{env_key}="{token}"'
            pattern = rf"(?m)^{env_key}\s*=.*$"
            if re.search(pattern, content):
                new_content = re.sub(pattern, token_line, content)
            else:
                new_content = content.rstrip() + "\n" + token_line + "\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            saved = True
        else:
            save_error = f".env not found at {env_path}"
    except Exception as e:
        save_error = str(e)

    # Update runtime config immediately
    try:
        if sandbox:
            config.UPSTOX_SANDBOX_ACCESS_TOKEN = token
        else:
            config.UPSTOX_ACCESS_TOKEN = token
    except Exception:
        pass

    mode = "sandbox" if sandbox else "live"
    return {
        "status": "success",
        "mode": mode,
        "saved_to": env_key,
        "token_preview": token[:8] + "...",
        "saved_to_env": saved,
        "save_error": save_error,
        "next_step": "GET /upstox/token-status to verify, then POST /upstox/start to launch the bot.",
    }


@app.post("/upstox/request-rotation")
async def upstox_request_rotation():
    """Best-effort request to Upstox token-request endpoints and persist token if returned."""
    if not config.UPSTOX_ENABLED:
        raise HTTPException(status_code=400, detail="Upstox is not enabled")

    from app.upstox_token_manager import UpstoxTokenManager

    manager = UpstoxTokenManager()
    result = await manager.request_access_token_via_api()

    # If we received an access_token in the response body, persist it to .env
    saved = False
    save_error = None
    access_token = None
    try:
        body = result.get("response")
        if isinstance(body, dict):
            access_token = body.get("access_token")

        if access_token:
            import os, re

            project_root = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.join(project_root, ".env")

            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()

                token_line = f'UPSTOX_ACCESS_TOKEN="{access_token}"'
                if re.search(r"(?m)^UPSTOX_ACCESS_TOKEN\s*=.*$", content):
                    new_content = re.sub(r"(?m)^UPSTOX_ACCESS_TOKEN\s*=.*$", token_line, content)
                else:
                    new_content = content.rstrip() + "\n" + token_line + "\n"

                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                try:
                    config.UPSTOX_ACCESS_TOKEN = access_token
                except Exception:
                    pass

                saved = True
            else:
                save_error = f".env not found at {env_path}"
    except Exception as e:
        save_error = str(e)

    return {"result": result, "saved_to_env": saved, "access_token": access_token, "save_error": save_error}


@app.get("/ai/crypto-sentiment")
async def crypto_sentiment():
    """AI analysis of crypto market sentiment, news & geopolitical events with trade suggestions."""
    from app.deepseek_ai import DeepSeekAI

    ai = DeepSeekAI()
    result = await ai.get_market_sentiment(market="crypto")
    return result


@app.get("/ai/indian-market-sentiment")
async def indian_market_sentiment():
    """AI analysis of Indian stock market sentiment, news & geopolitical events with trade suggestions."""
    from app.deepseek_ai import DeepSeekAI

    ai = DeepSeekAI()
    result = await ai.get_market_sentiment(market="indian_stocks")
    return result


@app.post("/upstox/webhook")
async def upstox_webhook(request: Request):
    """Endpoint to receive Upstox postback/webhook events (order updates, trades, etc)."""
    try:
        body = await request.body()
        if not body:
            # Empty body – likely a ping/verification request from Upstox
            return {"status": "ok"}
        payload = json.loads(body)
    except Exception:
        # Non-JSON body – acknowledge and ignore
        return {"status": "ok"}

    print("[upstox webhook] received:", payload)

    global upstox_bot
    if upstox_bot and hasattr(upstox_bot, "handle_webhook"):
        try:
            await upstox_bot.handle_webhook(payload)
        except Exception as e:
            print("Error forwarding webhook to bot:", e)

    return {"status": "received"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

