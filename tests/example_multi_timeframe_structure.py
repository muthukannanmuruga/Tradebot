"""
Example: Multi-Timeframe Data Structure

This shows the complete data structure that is calculated and fed to the AI
"""

example_multi_timeframe_data = {
    "5min": {
        "current_price": 68151.96,
        "ema_12": 68102.25,
        "ema_26": 68142.03,
        "ema_trend": "bearish",
        "macd": -39.7828,
        "macd_signal": -65.5856,
        "macd_histogram": 25.8028,
        "macd_trend": "bullish",
        "macd_crossover": "none",
        "rsi": 77.57,
        "rsi_zone": "overbought",
        "bb_upper": 68351.56,
        "bb_middle": 68151.05,
        "bb_lower": 67950.54,
        "atr": 721.32,
        "volume": 2.40
    },
    "1hour": {
        "current_price": 68151.97,
        "ema_12": 68306.12,
        "ema_26": 68438.52,
        "ema_trend": "bearish",
        "macd": -132.40,
        "macd_signal": -80.03,
        "macd_histogram": -52.37,
        "macd_trend": "bearish",
        "macd_crossover": "none",
        "rsi": 17.32,
        "rsi_zone": "oversold",
        "bb_upper": 69126.90,
        "bb_middle": 68354.67,
        "bb_lower": 67582.45,
        "atr": 3123.05,
        "volume": 60.40
    },
    "4hour": {
        "current_price": 68151.97,
        "ema_12": 68368.82,
        "ema_26": 68609.15,
        "ema_trend": "bearish",
        "macd": -240.33,
        "macd_signal": -211.53,
        "macd_histogram": -28.80,
        "macd_trend": "bearish",
        "macd_crossover": "none",
        "rsi": 44.12,
        "rsi_zone": "neutral",
        "bb_upper": 70894.25,
        "bb_middle": 69079.88,
        "bb_lower": 67265.51,
        "atr": 11531.34,
        "volume": 100.00
    },
    "1day": {
        "current_price": 68151.97,
        "ema_12": 68636.01,
        "ema_26": 69631.70,
        "ema_trend": "bearish",
        "macd": -995.69,
        "macd_signal": -1158.75,
        "macd_histogram": 163.06,
        "macd_trend": "bullish",
        "macd_crossover": "none",
        "rsi": 45.76,
        "rsi_zone": "neutral",
        "bb_upper": None,  # May be NaN if not enough data
        "bb_middle": None,
        "bb_lower": None,
        "atr": 50374.03,
        "volume": 259.12
    },
    "summary": {
        "current_price": 68151.96,
        "timeframe_alignment": {
            "alignment": "BEARISH_HTF",  # Overall classification
            "ema_bullish_count": 0,      # 0/4 timeframes bullish
            "macd_bullish_count": 2,     # 2/4 timeframes bullish
            "higher_timeframes_bullish": False,  # 4h+1d NOT bullish
            "higher_timeframes_bearish": True    # 4h+1d ARE bearish
        }
    }
}

# This complete structure is what gets passed to the AI for decision making
print("="*70)
print("EXAMPLE: Complete Multi-Timeframe Data Structure")
print("="*70)
print("\nThis is the FULL data that AI receives for each trading decision:\n")

import json
print(json.dumps(example_multi_timeframe_data, indent=2))

print("\n" + "="*70)
print("AI DECISION PROCESS")
print("="*70)
print("""
The AI analyzes this data following these rules:

1. HIGHER TIMEFRAME PRIORITY (1-day & 4-hour):
   - Both show bearish EMA trend → DO NOT BUY
   - MACD trends: 1d bullish, 4h bearish → Mixed momentum
   
2. LOWER TIMEFRAME CONFIRMATION (1-hour & 5-minute):
   - 1h: Oversold RSI (17.32) → Potential bounce
   - 5m: Overbought RSI (77.57) → Short-term pullback likely
   
3. TIMEFRAME ALIGNMENT:
   - EMA Bullish: 0/4 → Strong bearish consensus
   - MACD Bullish: 2/4 → Mixed
   - Higher TF Bias: BEARISH → Critical factor
   
4. DECISION LOGIC:
   - Higher timeframes are bearish → CANNOT BUY
   - Mixed signals across timeframes → LOW CONFIDENCE
   - No 3+ timeframe alignment → HOLD recommended
   
5. FINAL DECISION: HOLD with 55% confidence
   - Too risky to buy against higher timeframe bearish trend
   - Too risky to sell with 1h oversold (potential bounce)
   - Conservative approach until better alignment
""")

print("\n" + "="*70)
print("TRADING SCENARIOS")
print("="*70)
print("""
SCENARIO 1 - STRONG BUY SIGNAL (High Confidence > 0.75):
✅ 1-day: Bullish EMA, Bullish MACD, RSI 45-55
✅ 4-hour: Bullish EMA, Bullish MACD, RSI 50-65
✅ 1-hour: Bullish EMA, Bullish MACD, RSI 40-60
✅ 5-minute: Bullish EMA, Bullish MACD crossover, RSI 35-65
→ AI Decision: BUY with 0.80-0.90 confidence

SCENARIO 2 - MODERATE BUY SIGNAL (Medium Confidence 0.65-0.75):
✅ 1-day: Bullish EMA, RSI neutral
✅ 4-hour: Bullish EMA, Bullish MACD
⚠️ 1-hour: Mixed or consolidating
✅ 5-minute: Bullish MACD crossover, good entry
→ AI Decision: BUY with 0.65-0.75 confidence

SCENARIO 3 - HOLD SIGNAL (Low/Medium Confidence < 0.65):
⚠️ Mixed signals across timeframes
⚠️ Higher TF bullish but lower TF bearish (or vice versa)
⚠️ Less than 3 timeframes aligned
→ AI Decision: HOLD with 0.40-0.65 confidence

SCENARIO 4 - STRONG SELL SIGNAL (High Confidence > 0.75):
❌ 1-day: Bearish EMA, Bearish MACD
❌ 4-hour: Bearish EMA, Bearish MACD
❌ 1-hour: Bearish EMA, RSI > 65
❌ 5-minute: Bearish MACD crossover
→ AI Decision: SELL with 0.80-0.90 confidence
""")
