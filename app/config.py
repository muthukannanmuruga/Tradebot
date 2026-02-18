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

    # Binance Settings
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "True").lower() == "true"
    
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
    MAX_DAILY_TRADES: int = int(os.getenv("MAX_DAILY_TRADES", "10"))
    
    # Risk Management Parameters
    MAX_POSITION_PER_PAIR: float = float(os.getenv("MAX_POSITION_PER_PAIR", "20"))  # Max USDT per pair
    MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "3"))  # Max concurrent open trades
    MAX_PORTFOLIO_EXPOSURE: float = float(os.getenv("MAX_PORTFOLIO_EXPOSURE", "50"))  # Max total USDT at risk

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

        if not cls.BINANCE_API_KEY:
            errors.append("BINANCE_API_KEY is not set")
        if not cls.BINANCE_API_SECRET:
            errors.append("BINANCE_API_SECRET is not set")
        if not cls.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY is not set")

        return len(errors) == 0, errors


# Create global config instance
config = Config()
