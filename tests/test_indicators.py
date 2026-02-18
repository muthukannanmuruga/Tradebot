import pandas as pd
import numpy as np
from app.indicators import TechnicalIndicators


def make_series(n=100):
    # create a monotonic increasing series with small noise
    x = np.linspace(1, 100, n)
    noise = np.random.normal(0, 0.1, n)
    return pd.Series(x + noise)


def test_ema_sma_consistency():
    s = make_series(50)
    ema_short = TechnicalIndicators.calculate_ema(s, 6)
    ema_long = TechnicalIndicators.calculate_ema(s, 18)
    sma = TechnicalIndicators.calculate_sma(s, 20)

    # output lengths match
    assert len(ema_short) == len(s)
    assert len(ema_long) == len(s)
    assert len(sma) == len(s)

    # for a rising series, short EMA should be >= long EMA at the end
    assert ema_short.iloc[-1] >= ema_long.iloc[-1]


def test_macd_definition():
    s = make_series(60)
    macd_line, signal_line, hist = TechnicalIndicators.calculate_macd(s, fast_period=6, slow_period=18, signal_period=5)

    # macd_line equals fast - slow
    fast = TechnicalIndicators.calculate_ema(s, 6)
    slow = TechnicalIndicators.calculate_ema(s, 18)
    pd.testing.assert_series_equal(macd_line, fast - slow)

    # histogram equals macd - signal
    pd.testing.assert_series_equal(hist, macd_line - signal_line)


def test_rsi_basic_properties():
    # constant rising prices -> RSI should be high (close to 100)
    s = pd.Series(np.linspace(1, 100, 50))
    rsi = TechnicalIndicators.calculate_rsi(s, period=7)

    # length check
    assert len(rsi) == len(s)
    # final RSI should be > 70 for monotonic rising series
    assert rsi.iloc[-1] > 70


def test_calculate_all_indicators_returns_expected_keys():
    # Prepare a dummy OHLCV df
    n = 120
    close = np.linspace(100, 110, n)
    high = close + 0.5
    low = close - 0.5
    volume = np.ones(n) * 1000
    df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    indicators = TechnicalIndicators.calculate_all_indicators(df)
    expected_keys = {"current_price", "ema_12", "ema_26", "macd", "macd_signal", "macd_histogram", "rsi", "bb_upper", "bb_middle", "bb_lower", "atr", "volume"}
    assert expected_keys.issubset(set(indicators.keys()))
