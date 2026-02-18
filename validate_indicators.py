#!/usr/bin/env python3
"""
Validate Technical Indicators
Logs raw klines and calculated indicators for manual verification
"""
import asyncio
import pandas as pd
from app.binance_client import BinanceClient
from app.indicators import TechnicalIndicators
from app.config import config

async def validate_indicators(symbol="BTCUSDT", limit=50):
    """Fetch klines and display with calculated indicators"""
    
    print("\n" + "="*80)
    print(f"Technical Indicator Validation - {symbol}")
    print("="*80)
    
    # Fetch data
    client = BinanceClient()
    df = await client.get_historical_klines(symbol, limit=limit)
    
    # Calculate indicators
    indicators = TechnicalIndicators.calculate_all_indicators(df)
    intraday_signal = TechnicalIndicators.generate_intraday_signal(df)
    
    print(f"\n📊 Fetched {len(df)} candles (most recent shown below)")
    print("="*80)
    
    # Show last 10 candles with OHLCV
    print("\n🕯️  RAW KLINE DATA (Last 10 Candles):")
    print("-"*80)
    recent_df = df.tail(10).copy()
    recent_df['timestamp'] = pd.to_datetime(recent_df['timestamp'], unit='ms')
    
    # Format for display
    display_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    print(recent_df[display_cols].to_string(index=False))
    
    # Show calculated indicators
    print("\n\n📈 CALCULATED INDICATORS (Current Values):")
    print("="*80)
    
    print("\n1️⃣  PRICE & TREND:")
    print(f"   Current Price:        ${indicators['current_price']:,.2f}")
    print(f"   EMA 12:               ${indicators['ema_12']:,.2f}")
    print(f"   EMA 26:               ${indicators['ema_26']:,.2f}")
    print(f"   EMA Trend:            {indicators['ema_trend'].upper()}")
    print(f"   Price vs EMA12:       {'Above' if indicators['current_price'] > indicators['ema_12'] else 'Below'}")
    
    print("\n2️⃣  MACD:")
    print(f"   MACD Line:            {indicators['macd']:.4f}")
    print(f"   Signal Line:          {indicators['macd_signal']:.4f}")
    print(f"   Histogram:            {indicators['macd_histogram']:.4f}")
    print(f"   Crossover:            {indicators['macd_crossover'].upper()}")
    print(f"   MACD Trend:           {indicators['macd_trend'].upper()}")
    
    if indicators.get('prev_macd') and indicators.get('prev_macd_signal'):
        print(f"   Previous MACD:        {indicators['prev_macd']:.4f}")
        print(f"   Previous Signal:      {indicators['prev_macd_signal']:.4f}")
    
    print("\n3️⃣  RSI:")
    print(f"   RSI:                  {indicators['rsi']:.2f}")
    print(f"   RSI Zone:             {indicators['rsi_zone'].upper()}")
    if indicators.get('prev_rsi'):
        print(f"   Previous RSI:         {indicators['prev_rsi']:.2f}")
    
    print("\n4️⃣  BOLLINGER BANDS:")
    print(f"   Upper Band:           ${indicators['bb_upper']:,.2f}")
    print(f"   Middle Band (SMA20):  ${indicators['bb_middle']:,.2f}")
    print(f"   Lower Band:           ${indicators['bb_lower']:,.2f}")
    print(f"   Price Position:       ", end="")
    
    if indicators['current_price'] > indicators['bb_upper']:
        print("Above Upper Band (Overbought)")
    elif indicators['current_price'] < indicators['bb_lower']:
        print("Below Lower Band (Oversold)")
    else:
        print("Within Bands (Normal)")
    
    print("\n5️⃣  VOLATILITY:")
    print(f"   ATR (14):             {indicators['atr']:.2f}")
    print(f"   Current Volume:       {indicators['volume']:,.2f}")
    
    # Show EMA series (last 10 values)
    print("\n\n📊 EMA SERIES (Last 10 Values):")
    print("-"*80)
    ema_df = pd.DataFrame({
        'Close': df['close'].tail(10).values,
        'EMA12': df['close'].ewm(span=config.EMA_SHORT_PERIOD, adjust=False).mean().tail(10).values,
        'EMA26': df['close'].ewm(span=config.EMA_LONG_PERIOD, adjust=False).mean().tail(10).values
    })
    print(ema_df.to_string(index=False))
    
    # Show MACD series (last 10 values)
    print("\n\n📉 MACD SERIES (Last 10 Values):")
    print("-"*80)
    
    ema_short = df['close'].ewm(span=12, adjust=False).mean()
    ema_long = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema_short - ema_long
    signal_line = macd_line.ewm(span=config.MACD_SIGNAL_PERIOD, adjust=False).mean()
    histogram = macd_line - signal_line
    
    macd_df = pd.DataFrame({
        'MACD': macd_line.tail(10).values,
        'Signal': signal_line.tail(10).values,
        'Histogram': histogram.tail(10).values
    })
    print(macd_df.to_string(index=False))
    
    # Show RSI series (last 10 values)
    print("\n\n📊 RSI SERIES (Last 10 Values):")
    print("-"*80)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=config.RSI_PERIOD).mean()
    avg_loss = loss.rolling(window=config.RSI_PERIOD).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    rsi_df = pd.DataFrame({
        'Close': df['close'].tail(10).values,
        'RSI': rsi.tail(10).values
    })
    print(rsi_df.to_string(index=False))
    
    # Show intraday signal
    print("\n\n⚡ INTRADAY SIGNAL:")
    print("="*80)
    print(f"   Signal:               {intraday_signal['signal']}")
    print(f"   Confidence:           {intraday_signal['confidence']:.2f}")
    print(f"   Reasoning:            {intraday_signal['reasoning']}")
    
    # Export to CSV for detailed analysis
    print("\n\n💾 EXPORTING DATA:")
    print("-"*80)
    
    # Prepare full dataframe with all calculated values
    export_df = df.copy()
    export_df['ema_12'] = df['close'].ewm(span=config.EMA_SHORT_PERIOD, adjust=False).mean()
    export_df['ema_26'] = df['close'].ewm(span=config.EMA_LONG_PERIOD, adjust=False).mean()
    export_df['macd'] = macd_line
    export_df['macd_signal'] = signal_line
    export_df['macd_histogram'] = histogram
    export_df['rsi'] = rsi
    
    # Bollinger Bands
    sma = df['close'].rolling(window=config.BB_PERIOD).mean()
    std = df['close'].rolling(window=config.BB_PERIOD).std()
    export_df['bb_upper'] = sma + (std * config.BB_STDDEV)
    export_df['bb_middle'] = sma
    export_df['bb_lower'] = sma - (std * config.BB_STDDEV)
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    export_df['atr'] = true_range.rolling(window=config.ATR_PERIOD).mean()
    
    # Export to CSV
    filename = f'indicator_validation_{symbol}.csv'
    export_df.to_csv(filename, index=False)
    print(f"✅ Exported {len(export_df)} rows to: {filename}")
    print(f"   You can open this in Excel/Google Sheets to verify calculations")
    
    # Configuration used
    print("\n\n⚙️  CONFIGURATION:")
    print("-"*80)
    print(f"   EMA Short Period:     {config.EMA_SHORT_PERIOD}")
    print(f"   EMA Long Period:      {config.EMA_LONG_PERIOD}")
    print(f"   MACD Signal Period:   {config.MACD_SIGNAL_PERIOD}")
    print(f"   RSI Period:           {config.RSI_PERIOD}")
    print(f"   BB Period:            {config.BB_PERIOD}")
    print(f"   BB StdDev:            {config.BB_STDDEV}")
    print(f"   ATR Period:           {config.ATR_PERIOD}")
    
    print("\n" + "="*80)
    print("✅ Validation Complete!")
    print("="*80 + "\n")
    
    # Cross-verification tips
    print("📝 HOW TO VERIFY:")
    print("-"*80)
    print("1. Open the CSV file in Excel/Google Sheets")
    print("2. Compare with TradingView or other charting tools")
    print("3. Verify EMA: Use Excel formula =AVERAGE.EWM() or online calculators")
    print("4. Verify RSI: Check against RSI calculators online")
    print("5. Verify MACD: MACD = EMA12 - EMA26, Signal = EMA of MACD")
    print("\n📊 Online Tools for Verification:")
    print("   - TradingView: https://www.tradingview.com/")
    print("   - Binance Chart: https://www.binance.com/en/trade/BTC_USDT")
    print("   - RSI Calculator: https://www.investopedia.com/terms/r/rsi.asp")
    print("-"*80 + "\n")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    asyncio.run(validate_indicators(symbol, limit))
