"""
Pydantic models for API responses and data validation.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Literal


class TradeBase(BaseModel):
    """Base trade data"""

    pair: str
    side: Literal["BUY", "SELL"]
    quantity: float
    entry_price: float


class TradeCreate(TradeBase):
    """Trade creation request"""

    ai_reasoning: str
    confidence: float


class Trade(TradeBase):
    """Trade response model"""

    id: int
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None

    # Pydantic v2: allow model creation from ORM / attribute objects
    model_config = ConfigDict(from_attributes=True)


class BotStatus(BaseModel):
    """Bot status response"""

    is_running: bool
    last_check: Optional[datetime] = None
    total_trades: int
    current_position: Optional[str] = None
    daily_trades: int = 0
    max_daily_trades: int = 0
    current_price: Optional[float] = None


class MarketAnalysis(BaseModel):
    """Market analysis response"""

    pair: str
    current_price: float
    macd: float
    macd_signal: float
    macd_histogram: float
    rsi: float
    ema_12: float
    ema_26: float
    bb_upper: float
    bb_lower: float
    bb_middle: float
    atr: float
    ai_decision: str
    confidence: float
    reasoning: str


class PortfolioResponse(BaseModel):
    """Portfolio response"""

    total_balance: float
    available_balance: float
    total_invested: float
    open_positions: int
    total_profit_loss: float
    profit_loss_percent: float
    win_rate: float
