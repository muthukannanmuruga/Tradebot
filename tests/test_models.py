from app.models import Trade, TradeCreate, TradeBase
from pydantic import ValidationError
from types import SimpleNamespace
from datetime import datetime, timezone


def test_trade_model_from_dict():
    data = {
        "pair": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,
        "entry_price": 100.0,
        "id": 1,
        "status": "OPEN",
        "created_at": datetime.now(timezone.utc)
    }
    t = Trade.model_validate(data)
    assert t.pair == "BTCUSDT"


def test_trade_model_from_attribute_object():
    # create a simple object with attributes matching Trade fields
    obj = SimpleNamespace()
    obj.pair = "BTCUSDT"
    obj.side = "BUY"
    obj.quantity = 0.02
    obj.entry_price = 101.0
    obj.id = 2
    obj.status = "OPEN"
    obj.created_at = datetime.now(timezone.utc)

    t = Trade.model_validate(obj)
    assert t.id == 2
