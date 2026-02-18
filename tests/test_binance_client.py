import pandas as pd
import types
import pytest
from unittest.mock import MagicMock, patch

import app.binance_client as bc_module
from app.binance_client import BinanceClient


class FakeClient:
    def __init__(self):
        self.called = {}
        
    def get_server_time(self):
        # return a plausible serverTime in ms
        return {"serverTime": 1600000000000}

    def get_symbol_ticker(self, symbol=None):
        return {"price": "100.0"}

    def get_symbol_info(self, symbol):
        return {"baseAsset": "BTC", "quoteAsset": "USDT", "filters": [{"filterType":"LOT_SIZE","stepSize":"0.001"}, {"filterType":"MIN_NOTIONAL","minNotional":"10"}]}

    def get_klines(self, symbol=None, interval=None, limit=None):
        # Return simple kline rows: timestamp open high low close volume ...
        rows = []
        for i in range(limit):
            rows.append([1600000000000 + i*60000, "100", "101", "99", "100", "1000", 0, "1000", 0, 0, 0, 0])
        return rows

    def get_account(self, recvWindow=None):
        return {"balances": [{"asset": "USDT", "free": "50"}, {"asset":"BTC","free":"0.1"}]}

    def create_order(self, **kwargs):
        return {"orderId": 1, "symbol": kwargs.get('symbol'), "side": kwargs.get('side'), "price": "100", "executedQty": "0.01", "status": "FILLED", "transactTime": 123}

    def get_open_orders(self, symbol=None, recvWindow=None):
        return []

    def cancel_order(self, symbol=None, orderId=None, recvWindow=None):
        return {"status": "CANCELED"}


@patch('app.binance_client.Client', autospec=True)
def test_get_quantity_from_quote_and_klines(mock_client_cls):
    # Arrange
    mock_client_cls.return_value = FakeClient()
    client = BinanceClient()

    # Test get_quantity_from_quote
    qty = pytest.run(asyncio=False) if False else None
    import asyncio
    q = asyncio.get_event_loop().run_until_complete(client.get_quantity_from_quote('BTCUSDT', 5))
    # price=100 -> base quantity=0.05, with step 0.001 -> rounded to 0.05
    assert abs(q - 0.05) < 1e-8

    # Test historical klines -> DataFrame
    df = asyncio.get_event_loop().run_until_complete(client.get_historical_klines('BTCUSDT', limit=10))
    assert isinstance(df, pd.DataFrame)
    assert set(['timestamp', 'open', 'high', 'low', 'close', 'volume']).issubset(df.columns)


@pytest.mark.asyncio
async def test_account_and_order_calls(monkeypatch):
    # Patch actual Client to FakeClient
    with patch('app.binance_client.Client', return_value=FakeClient()):
        client = BinanceClient()
        bal = await client.get_account_balance('USDT')
        assert bal == 50.0

        # Use a quantity that meets minNotional (minNotional=10, price=100, so quantity >= 0.1)
        order = await client.place_market_order('BTCUSDT', 'BUY', 0.1)
        assert order['status'] == 'FILLED'
