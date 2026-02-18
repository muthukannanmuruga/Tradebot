"""End-to-end flow test: klines → indicators → DeepSeek AI → sandbox order"""
import asyncio
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

from app.upstox_client import UpstoxClient
from app.indicators import TechnicalIndicators
from app.deepseek_ai import DeepSeekAI


async def test():
    client = UpstoxClient()
    instrument = 'NSE_EQ|INE848E01016'

    print('--- Step 1: Fetch klines (live market data) ---')
    df_5m = await client.get_historical_klines(instrument, interval='5m', limit=400)
    df_1h = await client.get_historical_klines(instrument, interval='1h', limit=200)
    df_4h = await client.get_historical_klines(instrument, interval='4h', limit=100)
    df_1d = await client.get_historical_klines(instrument, interval='1d', limit=100)
    print(f'5m candles: {len(df_5m)}, 1h: {len(df_1h)}, 4h: {len(df_4h)}, 1d: {len(df_1d)}')

    print()
    print('--- Step 2: Calculate technical indicators ---')
    indicators = TechnicalIndicators.calculate_multi_timeframe_indicators(df_5m, df_1h, df_4h, df_1d)
    summary = indicators['summary']
    price = summary['current_price']
    print(f'Current price: Rs{price:.2f}')
    align = summary['timeframe_alignment']
    print(f'Alignment: {align["alignment"]}')
    print(f'MACD bullish: {align["macd_bullish_count"]}/4, RSI suitable: {align["rsi_bullish_count"]}/4, EMA bullish: {align["ema_bullish_count"]}/4')
    for tf, name in [('5min', '5m'), ('1hour', '1h'), ('4hour', '4h'), ('1day', '1d')]:
        ind = indicators[tf]
        print(f'  {name}: EMA {ind["ema_trend"]:8s} | MACD {ind["macd_trend"]:8s} | RSI {ind["rsi"]:.1f}')

    print()
    print('--- Step 3: DeepSeek AI decision ---')
    ai = DeepSeekAI()
    decision = await ai.get_trading_decision(instrument, indicators, None)
    print(f'Decision   : {decision["decision"]}')
    print(f'Confidence : {decision["confidence"]:.2%}')
    print(f'Reasoning  : {decision["reasoning"][:300]}')

    print()
    print('--- Step 4: Sandbox order (BUY 1 share) ---')
    order = await client.place_market_order(instrument, 'BUY', 1)
    print(f'Order: {order}')

    print()
    print('✅ Full flow complete: klines → indicators → AI → order')


if __name__ == '__main__':
    asyncio.run(test())
