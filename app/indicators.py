import pandas as pd
import numpy as np
from typing import Dict, Tuple
from app.config import config


class TechnicalIndicators:
    """Calculate various technical indicators"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            data: Price data series
            period: EMA period
        
        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average
        
        Args:
            data: Price data series
            period: SMA period
        
        Returns:
            SMA series
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast_period: int = None,
        slow_period: int = None,
        signal_period: int = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data: Price data series
            fast_period: Fast EMA period (default from settings)
            slow_period: Slow EMA period (default from settings)
            signal_period: Signal line period (default from settings)
        
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        fast_period = fast_period or config.EMA_SHORT_PERIOD
        slow_period = slow_period or config.EMA_LONG_PERIOD
        signal_period = signal_period or config.MACD_SIGNAL_PERIOD
        
        # Calculate EMAs
        ema_fast = TechnicalIndicators.calculate_ema(data, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(data, slow_period)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = None) -> pd.Series:
        """
        Calculate Relative Strength Index
        
        Args:
            data: Price data series
            period: RSI period (default from settings)
        
        Returns:
            RSI series
        """
        period = period or config.RSI_PERIOD
        
        # Calculate price changes
        delta = data.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: int = 2
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            data: Price data series
            period: Period for moving average
            std_dev: Number of standard deviations
        
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle_band = TechnicalIndicators.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period
        
        Returns:
            ATR series
        """
        # True Range calculation
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the moving average of True Range
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict:
        """
        Calculate all technical indicators for the given DataFrame
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Dictionary with all calculated indicators
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Calculate indicators
        ema_12 = TechnicalIndicators.calculate_ema(close, config.EMA_SHORT_PERIOD)
        ema_26 = TechnicalIndicators.calculate_ema(close, config.EMA_LONG_PERIOD)
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(close)
        rsi = TechnicalIndicators.calculate_rsi(close)
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(close)
        atr = TechnicalIndicators.calculate_atr(high, low, close)
        
        # Get latest values
        indicators = {
            "current_price": float(close.iloc[-1]),
            "ema_12": float(ema_12.iloc[-1]),
            "ema_26": float(ema_26.iloc[-1]),
            "macd": float(macd_line.iloc[-1]),
            "macd_signal": float(signal_line.iloc[-1]),
            "macd_histogram": float(histogram.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "bb_upper": float(bb_upper.iloc[-1]),
            "bb_middle": float(bb_middle.iloc[-1]),
            "bb_lower": float(bb_lower.iloc[-1]),
            "atr": float(atr.iloc[-1]),
            "volume": float(df['volume'].iloc[-1]),
            # Previous values for trend analysis
            "prev_macd": float(macd_line.iloc[-2]) if len(macd_line) > 1 else None,
            "prev_macd_signal": float(signal_line.iloc[-2]) if len(signal_line) > 1 else None,
            "prev_rsi": float(rsi.iloc[-2]) if len(rsi) > 1 else None,
        }
        
        # Add trend information
        indicators["ema_trend"] = "bullish" if indicators["ema_12"] > indicators["ema_26"] else "bearish"
        indicators["macd_trend"] = "bullish" if indicators["macd"] > indicators["macd_signal"] else "bearish"
        
        # MACD crossover detection
        if indicators["prev_macd"] and indicators["prev_macd_signal"]:
            if indicators["prev_macd"] < indicators["prev_macd_signal"] and indicators["macd"] > indicators["macd_signal"]:
                indicators["macd_crossover"] = "bullish"
            elif indicators["prev_macd"] > indicators["prev_macd_signal"] and indicators["macd"] < indicators["macd_signal"]:
                indicators["macd_crossover"] = "bearish"
            else:
                indicators["macd_crossover"] = "none"
        else:
            indicators["macd_crossover"] = "none"
        
        # RSI zones
        if indicators["rsi"] < 30:
            indicators["rsi_zone"] = "oversold"
        elif indicators["rsi"] > 70:
            indicators["rsi_zone"] = "overbought"
        else:
            indicators["rsi_zone"] = "neutral"
        
        return indicators

    @staticmethod
    def calculate_multi_timeframe_indicators(
        df_5m: pd.DataFrame,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame,
        df_1d: pd.DataFrame
    ) -> Dict:
        """
        Calculate indicators for all timeframes (5min, 1hr, 4hr, 1day)
        
        Args:
            df_5m: 5-minute candles DataFrame
            df_1h: 1-hour candles DataFrame
            df_4h: 4-hour candles DataFrame
            df_1d: 1-day candles DataFrame
        
        Returns:
            Dictionary with indicators for all timeframes
        """
        indicators_5m = TechnicalIndicators.calculate_all_indicators(df_5m)
        indicators_1h = TechnicalIndicators.calculate_all_indicators(df_1h)
        indicators_4h = TechnicalIndicators.calculate_all_indicators(df_4h)
        indicators_1d = TechnicalIndicators.calculate_all_indicators(df_1d)
        
        return {
            "5min": indicators_5m,
            "1hour": indicators_1h,
            "4hour": indicators_4h,
            "1day": indicators_1d,
            # Summary for quick reference
            "summary": {
                "current_price": indicators_5m["current_price"],
                "timeframe_alignment": TechnicalIndicators._analyze_timeframe_alignment(
                    indicators_5m, indicators_1h, indicators_4h, indicators_1d
                )
            }
        }
    
    @staticmethod
    def _analyze_timeframe_alignment(
        ind_5m: Dict,
        ind_1h: Dict,
        ind_4h: Dict,
        ind_1d: Dict
    ) -> Dict:
        """
        Analyze alignment across timeframes with MACD priority
        Priority: MACD (50%) > RSI (30%) > EMA (20%)
        
        Returns:
            Summary of how timeframes align with weighted scores
        """
        # Count MACD trends (HIGHEST PRIORITY - 50% weight)
        macd_bullish = sum([
            ind_5m["macd_trend"] == "bullish",
            ind_1h["macd_trend"] == "bullish",
            ind_4h["macd_trend"] == "bullish",
            ind_1d["macd_trend"] == "bullish"
        ])
        
        # Check for MACD crossovers on higher timeframes (major signal)
        macd_crossover_4h = ind_4h.get("macd_crossover", "none")
        macd_crossover_1d = ind_1d.get("macd_crossover", "none")
        has_higher_tf_crossover = macd_crossover_4h != "none" or macd_crossover_1d != "none"
        
        # Count RSI zones (MEDIUM PRIORITY - 30% weight)
        rsi_bullish = sum([
            ind_5m["rsi"] < 70 and ind_5m["rsi"] > 30,  # Neutral = good
            ind_1h["rsi"] < 70 and ind_1h["rsi"] > 30,
            ind_4h["rsi"] < 70,  # Not overbought
            ind_1d["rsi"] < 70   # Not overbought
        ])
        
        # RSI extremes on higher timeframes (filters)
        higher_tf_rsi_overbought = ind_4h["rsi"] > 70 or ind_1d["rsi"] > 70
        higher_tf_rsi_oversold = ind_4h["rsi"] < 30 or ind_1d["rsi"] < 30
        
        # Count EMA trends (LOWEST PRIORITY - 20% weight)
        ema_bullish = sum([
            ind_5m["ema_trend"] == "bullish",
            ind_1h["ema_trend"] == "bullish",
            ind_4h["ema_trend"] == "bullish",
            ind_1d["ema_trend"] == "bullish"
        ])
        
        # Higher timeframe MACD bias (most important)
        higher_tf_macd_bullish = (
            ind_4h["macd_trend"] == "bullish" and 
            ind_1d["macd_trend"] == "bullish"
        )
        higher_tf_macd_bearish = (
            ind_4h["macd_trend"] == "bearish" and 
            ind_1d["macd_trend"] == "bearish"
        )
        
        # Determine overall alignment (MACD-weighted)
        if macd_bullish >= 3 and not higher_tf_rsi_overbought:
            alignment = "STRONG_BULLISH"
        elif macd_bullish <= 1 and not higher_tf_rsi_oversold:
            alignment = "STRONG_BEARISH"
        elif higher_tf_macd_bullish and not higher_tf_rsi_overbought:
            alignment = "BULLISH_MACD_HTF"
        elif higher_tf_macd_bearish and not higher_tf_rsi_oversold:
            alignment = "BEARISH_MACD_HTF"
        else:
            alignment = "MIXED"
        
        return {
            "alignment": alignment,
            "macd_bullish_count": macd_bullish,  # Primary metric
            "rsi_bullish_count": rsi_bullish,    # Secondary metric
            "ema_bullish_count": ema_bullish,    # Tertiary metric
            "higher_tf_macd_bullish": higher_tf_macd_bullish,
            "higher_tf_macd_bearish": higher_tf_macd_bearish,
            "higher_tf_rsi_overbought": higher_tf_rsi_overbought,
            "higher_tf_rsi_oversold": higher_tf_rsi_oversold,
            "has_higher_tf_macd_crossover": has_higher_tf_crossover
        }

    @staticmethod
    def generate_intraday_signal(df: pd.DataFrame) -> Dict:
        """
        Generate a simple intraday trading signal based on multiple indicators.

        Returns a dict with keys: `signal` ("BUY"/"SELL"/"HOLD"),
        `confidence` (0-1), and `reasoning` (str).

        Strategy (simple, explainable):
        - EMA crossover (12/26) bullish/bearish
        - MACD line vs signal and MACD crossover
        - RSI in supportive zone (avoid extreme overbought/oversold)
        - Volume confirmation vs 20-period average

        This is intended as a lightweight intraday filter you can extend.
        """
        indicators = TechnicalIndicators.calculate_all_indicators(df)

        # Safe access
        rsi = indicators.get("rsi")
        ema_12 = indicators.get("ema_12")
        ema_26 = indicators.get("ema_26")
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        macd_crossover = indicators.get("macd_crossover")

        # Volume confirmation: compare last volume to 20-period average
        vol_confirm = False
        try:
            vol_series = df["volume"].astype(float)
            vol_mean = vol_series.rolling(window=20).mean().iloc[-1]
            vol_confirm = (vol_series.iloc[-1] > vol_mean) if not np.isnan(vol_mean) else False
        except Exception:
            vol_confirm = False

        # Weighted signals (sum of weights -> confidence)
        weights = {
            "ema": 0.30,
            "macd_line": 0.25,
            "macd_cross": 0.20,
            "rsi": 0.15,
            "volume": 0.10,
        }

        bull_score = 0.0
        bear_score = 0.0
        reasons = []

        # EMA trend
        if ema_12 is not None and ema_26 is not None:
            if ema_12 > ema_26:
                bull_score += weights["ema"]
                reasons.append("EMA12 > EMA26 (bullish)")
            else:
                bear_score += weights["ema"]
                reasons.append("EMA12 < EMA26 (bearish)")

        # MACD line vs signal
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                bull_score += weights["macd_line"]
                reasons.append("MACD > signal (bullish)")
            else:
                bear_score += weights["macd_line"]
                reasons.append("MACD < signal (bearish)")

        # MACD crossover
        if macd_crossover == "bullish":
            bull_score += weights["macd_cross"]
            reasons.append("MACD bullish crossover")
        elif macd_crossover == "bearish":
            bear_score += weights["macd_cross"]
            reasons.append("MACD bearish crossover")

        # RSI supportive zone: prefer buys when RSI between 40-70, sells when 30-45
        if rsi is not None:
            if 40 <= rsi <= 70:
                bull_score += weights["rsi"]
                reasons.append(f"RSI={rsi:.1f} supportive for bulls")
            elif 30 <= rsi <= 45:
                bear_score += weights["rsi"]
                reasons.append(f"RSI={rsi:.1f} supportive for bears")
            else:
                # neutral/no score
                reasons.append(f"RSI={rsi:.1f} neutral/extreme")

        # Volume confirmation
        if vol_confirm:
            # amplify whichever side currently leads by adding its weight
            if bull_score > bear_score:
                bull_score += weights["volume"]
                reasons.append("Volume above 20-period average (supports buy)")
            elif bear_score > bull_score:
                bear_score += weights["volume"]
                reasons.append("Volume above 20-period average (supports sell)")
            else:
                reasons.append("Volume above 20-period average (no directional bias)")
        else:
            reasons.append("Volume not above 20-period average")

        # Normalize confidence (cap at 1.0)
        confidence = float(min(1.0, bull_score if bull_score > bear_score else bear_score))

        if bull_score > bear_score and confidence >= 0.5:
            signal = "BUY"
        elif bear_score > bull_score and confidence >= 0.5:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "reasoning": "; ".join(reasons),
        }

