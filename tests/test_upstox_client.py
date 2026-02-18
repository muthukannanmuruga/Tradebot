"""
Tests for Upstox client and trading bot.
Run with: pytest tests/test_upstox_client.py -v
"""

import pytest
import pytest_asyncio
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    """Patch config values for Upstox testing."""
    with patch("app.config.config") as cfg, \
         patch("app.upstox_client.config", cfg):
        cfg.UPSTOX_API_KEY = "test-api-key"
        cfg.UPSTOX_API_SECRET = "test-api-secret"
        cfg.UPSTOX_REDIRECT_URI = "http://localhost:8000/upstox/callback"
        cfg.UPSTOX_ACCESS_TOKEN = "test-access-token"
        cfg.UPSTOX_SANDBOX = True
        cfg.UPSTOX_SANDBOX_API_KEY = ""   # empty → fall back to live key
        cfg.UPSTOX_SANDBOX_API_SECRET = ""
        cfg.UPSTOX_ENABLED = True
        cfg.UPSTOX_TRADING_PAIRS = ["NSE_EQ|INE848E01016"]
        cfg.UPSTOX_TRADING_AMOUNT = 1000.0
        cfg.UPSTOX_PRODUCT_TYPE = "I"
        cfg.CHECK_INTERVAL_SECONDS = 300
        cfg.MAX_DAILY_TRADES = 10
        cfg.MAX_OPEN_POSITIONS = 3
        cfg.MAX_POSITION_PER_PAIR = 20000
        cfg.MAX_PORTFOLIO_EXPOSURE = 50000
        cfg.STOP_LOSS_PERCENT = 0.5
        cfg.TAKE_PROFIT_PERCENT = 1.0
        cfg.DEEPSEEK_API_KEY = "test-deepseek-key"
        cfg.EMA_SHORT_PERIOD = 6
        cfg.EMA_LONG_PERIOD = 18
        cfg.MACD_SIGNAL_PERIOD = 5
        cfg.RSI_PERIOD = 7
        cfg.BB_PERIOD = 20
        cfg.BB_STDDEV = 2.0
        cfg.ATR_PERIOD = 14
        yield cfg


@pytest.fixture
def upstox_client(mock_config):
    """Create UpstoxClient with mocked config."""
    from app.upstox_client import UpstoxClient

    client = UpstoxClient()
    return client


# ── UpstoxClient Unit Tests ──────────────────────────────────────────


class TestUpstoxClient:
    """Tests for UpstoxClient."""

    def test_init(self, upstox_client):
        """Test client initializes with config values."""
        assert upstox_client.access_token == "test-access-token"
        assert upstox_client.api_key == "test-api-key"
        assert upstox_client.use_sandbox is True

    def test_login_url(self, upstox_client):
        """Test OAuth2 login URL generation."""
        url = upstox_client.get_login_url()
        assert "api.upstox.com/v2/login/authorization/dialog" in url
        assert "client_id=test-api-key" in url
        assert "response_type=code" in url

    def test_headers(self, upstox_client):
        """Test authorization headers."""
        headers = upstox_client._headers()
        assert headers["Authorization"] == "Bearer test-access-token"
        assert headers["Content-Type"] == "application/json"

    def test_calculate_from_date(self, upstox_client):
        """Test date range calculation for different intervals."""
        from_date = upstox_client._calculate_from_date("5m", 100)
        assert isinstance(from_date, str)
        assert len(from_date) == 10  # YYYY-MM-DD

        from_date_1d = upstox_client._calculate_from_date("1d", 30)
        assert isinstance(from_date_1d, str)

    def test_interval_map(self, upstox_client):
        """Test all interval mappings exist."""
        expected = ["5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        for interval in expected:
            assert interval in upstox_client.INTERVAL_MAP

    @pytest.mark.asyncio
    async def test_get_current_price(self, upstox_client):
        """Test price fetching with mocked response."""
        mock_resp = {
            "data": {
                "NSE_EQ|INE848E01016": {"last_price": 123.45}
            }
        }
        with patch.object(upstox_client, "_get", new_callable=AsyncMock, return_value=mock_resp):
            price = await upstox_client.get_current_price("NSE_EQ|INE848E01016")
            assert price == 123.45

    @pytest.mark.asyncio
    async def test_get_historical_klines(self, upstox_client):
        """Test kline data parsing."""
        mock_resp = {
            "data": {
                "candles": [
                    ["2025-01-02T09:15:00+05:30", 100.0, 105.0, 99.0, 103.0, 50000, 0],
                    ["2025-01-02T09:20:00+05:30", 103.0, 107.0, 102.0, 106.0, 60000, 0],
                ]
            }
        }
        with patch.object(upstox_client, "_get", new_callable=AsyncMock, return_value=mock_resp):
            df = await upstox_client.get_historical_klines(
                "NSE_EQ|INE848E01016", interval="5m", limit=100
            )
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2
            assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
            assert df["close"].iloc[-1] == 106.0

    @pytest.mark.asyncio
    async def test_get_account_balance(self, upstox_client):
        """Test balance retrieval."""
        mock_resp = {
            "data": {
                "equity": {"available_margin": 15507.46},
                "commodity": {"available_margin": 0},
            }
        }
        with patch.object(upstox_client, "_get", new_callable=AsyncMock, return_value=mock_resp):
            balance = await upstox_client.get_account_balance()
            assert balance == 15507.46

    @pytest.mark.asyncio
    async def test_place_market_order(self, upstox_client):
        """Test market order placement."""
        mock_resp = {
            "status": "success",
            "data": {"order_ids": ["1234567890"]},
        }
        with patch.object(upstox_client, "_post", new_callable=AsyncMock, return_value=mock_resp):
            result = await upstox_client.place_market_order(
                "NSE_EQ|INE848E01016", "BUY", 10, product="I"
            )
            assert result["orderId"] == "1234567890"
            assert result["side"] == "BUY"
            assert result["quantity"] == 10

    @pytest.mark.asyncio
    async def test_get_quantity_from_quote(self, upstox_client):
        """Test quantity calculation from INR amount."""
        with patch.object(
            upstox_client,
            "get_current_price",
            new_callable=AsyncMock,
            return_value=500.0,
        ):
            qty = await upstox_client.get_quantity_from_quote(
                "NSE_EQ|INE848E01016", 1000.0
            )
            assert qty == 2  # 1000 / 500 = 2

    def test_format_quantity(self, upstox_client):
        """Test quantity formatting (integer for equities)."""
        assert upstox_client.format_quantity(10.7, "NSE_EQ|INE848E01016") == "10"
        assert upstox_client.format_quantity(1.0, "NSE_EQ|INE848E01016") == "1"


# ── Integration-style Tests ──────────────────────────────────────────


class TestUpstoxTradingBotInit:
    """Test UpstoxTradingBot initialization (without live API calls)."""

    def test_bot_attributes(self, mock_config):
        """Test bot initializes with correct attributes."""
        with patch("app.upstox_trading_bot.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_db.query.return_value.first.return_value = MagicMock(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit_loss=0.0,
                win_rate=0.0,
            )

            from app.upstox_trading_bot import UpstoxTradingBot

            bot = UpstoxTradingBot()
            assert bot.is_running is False
            assert bot.trading_pairs == ["NSE_EQ|INE848E01016"]
            assert bot.product_type == "I"
            assert bot.trade_count == 0
