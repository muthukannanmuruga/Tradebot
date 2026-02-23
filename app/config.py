"""
Configuration management for the AI trading bot.
Loads settings from environment variables.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""

    # API Keys - MAINNET
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    
    # API Keys - TESTNET
    BINANCE_TESTNET_API_KEY: str = os.getenv("BINANCE_TESTNET_API_KEY", "")
    BINANCE_TESTNET_API_SECRET: str = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # ── Upstox Settings ────────────────────────────────────────────────
    UPSTOX_API_KEY: str = os.getenv("UPSTOX_API_KEY", "")
    UPSTOX_API_SECRET: str = os.getenv("UPSTOX_API_SECRET", "")
    UPSTOX_REDIRECT_URI: str = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/upstox/callback")
    UPSTOX_ACCESS_TOKEN: str = os.getenv("UPSTOX_ACCESS_TOKEN", "")  # live token
    UPSTOX_SANDBOX: bool = os.getenv("UPSTOX_SANDBOX", "False").lower() == "true"
    UPSTOX_ENABLED: bool = os.getenv("UPSTOX_ENABLED", "False").lower() == "true"
    # Sandbox-specific credentials (auto-selected when UPSTOX_SANDBOX=True)
    UPSTOX_SANDBOX_API_KEY: str = os.getenv("UPSTOX_SANDBOX_API_KEY", "")
    UPSTOX_SANDBOX_API_SECRET: str = os.getenv("UPSTOX_SANDBOX_API_SECRET", "")
    UPSTOX_SANDBOX_ACCESS_TOKEN: str = os.getenv("UPSTOX_SANDBOX_ACCESS_TOKEN", "")  # sandbox token

    # Upstox Trading Pairs – comma-separated instrument tokens
    # Example: NSE_EQ|INE848E01016,NSE_EQ|INE002A01018  (PNB, RELIANCE)
    UPSTOX_AUTO_SELECT_PAIRS: bool = os.getenv("UPSTOX_AUTO_SELECT_PAIRS", "False").lower() == "true"
    UPSTOX_TRADING_PAIRS_STR: str = os.getenv("UPSTOX_TRADING_PAIRS", "")
    UPSTOX_TRADING_PAIRS: list = (
        [p.strip() for p in UPSTOX_TRADING_PAIRS_STR.split(",") if p.strip()]
        if UPSTOX_TRADING_PAIRS_STR
        else []
    )

    # Upstox trade amount in INR
    UPSTOX_TRADING_AMOUNT: float = float(os.getenv("UPSTOX_TRADING_AMOUNT", "1000"))
    # Product type: I = Intraday, D = Delivery, MTF = Margin
    UPSTOX_PRODUCT_TYPE: str = os.getenv("UPSTOX_PRODUCT_TYPE", "I")
    # Margin utilization for intraday short/long (100 = use full permitted margin)
    UPSTOX_MARGIN_PERCENT: float = float(os.getenv("UPSTOX_MARGIN_PERCENT", "100"))
    UPSTOX_MOCK_BALANCE: float = float(os.getenv("UPSTOX_MOCK_BALANCE", "10000"))  # Mock balance for sandbox testing (INR)
    
    # Upstox Risk Management (in INR)
    UPSTOX_MAX_POSITION_PER_PAIR: float = float(os.getenv("UPSTOX_MAX_POSITION_PER_PAIR", "5000"))
    UPSTOX_MAX_OPEN_POSITIONS: int = int(os.getenv("UPSTOX_MAX_OPEN_POSITIONS", "3"))
    UPSTOX_MAX_PORTFOLIO_EXPOSURE: float = float(os.getenv("UPSTOX_MAX_PORTFOLIO_EXPOSURE", "10000"))

    # Binance Settings
    BINANCE_ENABLED: bool = os.getenv("BINANCE_ENABLED", "True").lower() == "true"
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "True").lower() == "true"
    
    # Auto-select pairs based on AI sentiment (True) or use manual pairs (False)
    AUTO_SELECT_PAIRS: bool = os.getenv("AUTO_SELECT_PAIRS", "False").lower() == "true"
    
    # Trading Pairs - Support multiple pairs separated by comma
    TRADING_PAIRS_STR: str = os.getenv("TRADING_PAIRS", "BTCUSDT,ETHUSDT,SOLUSDT")
    TRADING_PAIRS: list = [pair.strip() for pair in TRADING_PAIRS_STR.split(",")]
    
    # Legacy single pair support (for backwards compatibility)
    TRADING_PAIR: str = TRADING_PAIRS[0] if TRADING_PAIRS else "BTCUSDT"

    # Trading Parameters
    # TRADING_AMOUNT_QUOTE: spend amount in quote asset (e.g., 1 USDT) per trade per pair
    TRADING_AMOUNT_QUOTE: float = float(os.getenv("TRADING_AMOUNT_QUOTE", "1"))
    # Scalping strategy: 0.5% stop loss, 1% take profit (1:2 risk:reward)
    STOP_LOSS_PERCENT: float = float(os.getenv("STOP_LOSS_PERCENT", "0.5"))
    TAKE_PROFIT_PERCENT: float = float(os.getenv("TAKE_PROFIT_PERCENT", "1.0"))
    # DEPRECATED: global daily trades limit kept only for backward compatibility.
    # Prefer per-market limits below. The bots use per-market counters.
    MAX_DAILY_TRADES: int = int(os.getenv("MAX_DAILY_TRADES", "10"))
    # Per-market daily trade limits (each bot has its own counter — set independently)
    UPSTOX_MAX_DAILY_TRADES: int = int(os.getenv("UPSTOX_MAX_DAILY_TRADES", "10"))
    BINANCE_MAX_DAILY_TRADES: int = int(os.getenv("BINANCE_MAX_DAILY_TRADES", "10"))
    
    # Risk Management Parameters
    MAX_POSITION_PER_PAIR: float = float(os.getenv("MAX_POSITION_PER_PAIR", "20"))  # Max USDT per pair
    MAX_PORTFOLIO_EXPOSURE: float = float(os.getenv("MAX_PORTFOLIO_EXPOSURE", "50"))  # Max total USDT at risk
    # Per-market risk limits
    BINANCE_MAX_OPEN_POSITIONS: int = int(os.getenv("BINANCE_MAX_OPEN_POSITIONS", "3"))

    # Bot Settings
    # CHECK_INTERVAL_SECONDS: Check every 5 minutes to align with 5-minute candles
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.6"))


    # Technical Indicators
    # Tuned defaults for hourly intraday signals (shorter periods = more sensitivity)
    EMA_SHORT_PERIOD: int = int(os.getenv("EMA_SHORT_PERIOD", "6"))
    EMA_LONG_PERIOD: int = int(os.getenv("EMA_LONG_PERIOD", "18"))
    MACD_SIGNAL_PERIOD: int = int(os.getenv("MACD_SIGNAL_PERIOD", "5"))
    RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", "7"))
    BB_PERIOD: int = int(os.getenv("BB_PERIOD", "20"))
    BB_STDDEV: float = float(os.getenv("BB_STDDEV", "2.0"))
    ATR_PERIOD: int = int(os.getenv("ATR_PERIOD", "14"))

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://mediumdb_owner:npg_tLr49JysMEbj@ep-sparkling-star-a4d5qdkr-pooler.us-east-1.aws.neon.tech/Tradingbot?sslmode=require&channel_binding=require"
    )

    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    # Path to a markdown instruction file for DeepSeek (optional)
    DEEPSEEK_INSTRUCTION_PATH: str = os.getenv("DEEPSEEK_INSTRUCTION_PATH", "")

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate all required configuration"""
        errors = []

        if cls.BINANCE_ENABLED:
            if not cls.BINANCE_API_KEY:
                errors.append("BINANCE_API_KEY is not set (BINANCE_ENABLED=True)")
            if not cls.BINANCE_API_SECRET:
                errors.append("BINANCE_API_SECRET is not set (BINANCE_ENABLED=True)")
        if not cls.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY is not set")

        # Upstox validation (only when enabled)
        if cls.UPSTOX_ENABLED:
            if not cls.UPSTOX_API_KEY:
                errors.append("UPSTOX_API_KEY is not set (UPSTOX_ENABLED=True)")
            if not cls.UPSTOX_API_SECRET:
                errors.append("UPSTOX_API_SECRET is not set (UPSTOX_ENABLED=True)")
            if not cls.UPSTOX_ACCESS_TOKEN:
                errors.append("UPSTOX_ACCESS_TOKEN is not set (UPSTOX_ENABLED=True)")
            if not cls.UPSTOX_TRADING_PAIRS:
                errors.append("UPSTOX_TRADING_PAIRS is not set (UPSTOX_ENABLED=True)")

        return len(errors) == 0, errors


# Create global config instance
config = Config()
