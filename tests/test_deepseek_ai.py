import json
from app.deepseek_ai import DeepSeekAI


def test_parse_decision_json():
    ai = DeepSeekAI()
    js = json.dumps({"action": "BUY", "confidence": 0.8, "reasoning": "test"})
    out = ai._parse_decision(js)
    assert out["action"] == "BUY"
    assert abs(out["confidence"] - 0.8) < 1e-6
    assert "test" in out["reasoning"]


def test_parse_decision_nonjson():
    ai = DeepSeekAI()
    text = "I think we should BUY because momentum is strong"
    out = ai._parse_decision(text)
    assert out["action"] in {"BUY", "SELL", "HOLD"}
    assert out["confidence"] == 0.5
    assert text in out["reasoning"]
