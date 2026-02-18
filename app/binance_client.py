
from binance.client import Client

import pandas as pd
from binance.enums import *
from binance.exceptions import BinanceAPIException
from typing import List, Dict, Optional
from datetime import datetime
from app.config import config
import time

class BinanceClient:
    """Wrapper for Binance API operations"""
    def __init__(self):
        if config.BINANCE_TESTNET:
            api_key = config.BINANCE_TESTNET_API_KEY
            api_secret = config.BINANCE_TESTNET_API_SECRET
            self.client = Client(api_key, api_secret, testnet=True)
            self.client.API_URL = 'https://testnet.binance.vision/api'
            print("✅ Using Binance TESTNET credentials")
        else:
            api_key = config.BINANCE_API_KEY
            api_secret = config.BINANCE_API_SECRET
            self.client = Client(api_key, api_secret)
            print("✅ Using Binance MAINNET credentials")
        # Fetch and log server time offset
        try:
            server_time_resp = self.client.get_server_time()
            server_time_ms = int(server_time_resp.get('serverTime', 0))
            local_time_ms = int(time.time() * 1000)
            self.time_offset_ms = server_time_ms - local_time_ms
            print(f"⏱️  Server time offset: {self.time_offset_ms} ms (local may be {'behind' if self.time_offset_ms > 0 else 'ahead'} by {abs(self.time_offset_ms)} ms)")
            if abs(self.time_offset_ms) > 5000:
                print(f"⚠️  WARNING: Large time offset detected. Please sync system clock.")
        except Exception as e:
            print(f"⚠️  Could not fetch server time: {e}")
            self.time_offset_ms = 0

    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            print(f"Error fetching price: {e}")
            raise

    async def get_quantity_from_quote(self, symbol: str, quote_amount: float) -> float:
        """
        Convert quote asset amount to base asset quantity.
        Respects LOT_SIZE step precision and validates against MIN_QTY/MAX_QTY/MIN_NOTIONAL.
        """
        try:
            price = await self.get_current_price(symbol)
            info = self.client.get_symbol_info(symbol)
            if not info:
                return quote_amount / price

            min_qty = None
            max_qty = None
            step_size = None
            min_notional = None
            
            # Get all filters
            for f in info.get('filters', []):
                if f.get('filterType') == 'LOT_SIZE':
                    step_size = float(f.get('stepSize'))
                    min_qty = float(f.get('minQty', 0))
                    max_qty = float(f.get('maxQty', float('inf')))
                
                if f.get('filterType') == 'MIN_NOTIONAL':
                    min_notional = float(f.get('minNotional') or f.get('notional') or 0)
                
                if f.get('filterType') == 'NOTIONAL':
                    min_notional = float(f.get('minNotional') or 0)
            
            # Check if quote_amount meets MIN_NOTIONAL
            if min_notional and quote_amount < min_notional:
                print(f"⚠️ Quote amount ${quote_amount} below MIN_NOTIONAL ${min_notional}")
                print(f"   Adjusting to MIN_NOTIONAL ${min_notional * 1.01}")
                quote_amount = min_notional * 1.01  # Add 1% buffer
            
            # Calculate base quantity from quote amount
            base_quantity = quote_amount / price
            
            # Helper function to get decimals from step_size
            def get_decimals(step: float) -> int:
                """Get number of decimal places from step size"""
                # Convert to string without scientific notation
                step_str = f"{step:.10f}".rstrip('0')
                if '.' in step_str:
                    return len(step_str.split('.')[1])
                return 0
            
            # Apply LOT_SIZE precision (round to step_size decimals)
            decimals = 0
            if step_size:
                decimals = get_decimals(step_size)
                base_quantity = round(base_quantity, decimals)
            
            print(f"💹 Calculated: {base_quantity} {info.get('baseAsset')} = ${quote_amount:.2f} / ${price:.2f}")
            
            # Validate against MIN_QTY
            if min_qty and base_quantity < min_qty:
                print(f"⚠️ Quantity {base_quantity} < MIN_QTY {min_qty}, using MIN_QTY")
                base_quantity = min_qty
            
            # Validate against MAX_QTY
            if max_qty and base_quantity > max_qty:
                print(f"⚠️ Quantity {base_quantity} > MAX_QTY {max_qty}, using MAX_QTY")
                base_quantity = max_qty
            
            # Final notional check - ensure order value meets minimum
            final_notional = base_quantity * price
            if min_notional and final_notional < min_notional:
                print(f"⚠️ Notional ${final_notional:.2f} < MIN_NOTIONAL ${min_notional}")
                # Calculate new quantity to meet MIN_NOTIONAL
                required_qty = (min_notional * 1.01) / price
                base_quantity = round(required_qty, decimals)
                print(f"   Adjusted to {base_quantity} {info.get('baseAsset')} (notional: ${base_quantity * price:.2f})")
            
            # Verify final quantity is valid
            if base_quantity <= 0:
                raise Exception(f"Invalid quantity calculation: {base_quantity}. Check MIN_NOTIONAL and price.")
            
            print(f"✅ Final quantity: {base_quantity} {info.get('baseAsset')} (${base_quantity * price:.2f})")
            return base_quantity
            
        except Exception as e:
            print(f"Error converting quote to quantity: {e}")
            raise

    async def get_historical_klines(self, symbol: str, interval: str = Client.KLINE_INTERVAL_1HOUR, limit: int = 100) -> pd.DataFrame:
        """
        Get historical kline/candlestick data
        """
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except BinanceAPIException as e:
            print(f"Error fetching klines: {e}")
            raise

    def format_quantity(self, quantity: float, symbol: str) -> str:
        """Format quantity to meet Binance API requirements (no scientific notation)"""
        try:
            # Get symbol info for precision
            info = self.client.get_symbol_info(symbol)
            if not info:
                # Default formatting without scientific notation
                return f"{quantity:.8f}".rstrip('0').rstrip('.')
            
            # Get LOT_SIZE filter for step size
            step_size = None
            for f in info.get('filters', []):
                if f.get('filterType') == 'LOT_SIZE':
                    step_size = f.get('stepSize')
                    break
            
            if step_size:
                # Count decimal places in step_size
                step_size_str = str(step_size).rstrip('0')
                if '.' in step_size_str:
                    precision = len(step_size_str.split('.')[1])
                else:
                    precision = 0
                
                # Format to the required precision
                formatted = f"{quantity:.{precision}f}"
            else:
                # Default: 8 decimal places, strip trailing zeros
                formatted = f"{quantity:.8f}".rstrip('0').rstrip('.')
            
            return formatted
            
        except Exception as e:
            print(f"Error formatting quantity: {e}")
            # Fallback: format without scientific notation
            return f"{quantity:.8f}".rstrip('0').rstrip('.')
    
    async def get_account_balance(self, asset: str = "USDT") -> float:
        """Get account balance for a specific asset"""
        try:
            account = self.client.get_account(recvWindow=10000)
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0.0
        except BinanceAPIException as e:
            print(f"Error fetching balance: {e}")
            raise

    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        """
        Place a market order
        """
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                raise Exception(f"Symbol info not found for {symbol}")
            base_asset = info['baseAsset']
            quote_asset = info['quoteAsset']
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price']) if ticker and 'price' in ticker else None
            
            # Collect all relevant filters
            min_notional = None
            min_qty = None
            max_qty = None
            step_size = None
            
            for f in info.get('filters', []):
                if f.get('filterType') == 'MIN_NOTIONAL':
                    min_notional = float(f.get('minNotional') or f.get('notional') or 0)
                if f.get('filterType') == 'NOTIONAL':
                    min_notional = float(f.get('minNotional') or 0)
                if f.get('filterType') == 'LOT_SIZE':
                    step_size = float(f.get('stepSize'))
                    min_qty = float(f.get('minQty', 0))
                    max_qty = float(f.get('maxQty', float('inf')))
            
            # Validate quantity
            if min_qty and quantity < min_qty:
                raise Exception(f"Quantity {quantity} below MIN_QTY {min_qty} for {symbol}")
            if max_qty and quantity > max_qty:
                raise Exception(f"Quantity {quantity} above MAX_QTY {max_qty} for {symbol}")
            
            # Validate notional value for BUY orders
            if side == 'BUY' and price is not None:
                required_quote = quantity * price
                if min_notional and required_quote < min_notional:
                    raise Exception(
                        f"Order value ${required_quote:.4f} {quote_asset} below MIN_NOTIONAL ${min_notional}. "
                        f"Increase TRADING_AMOUNT_QUOTE in .env to at least ${min_notional * 1.1:.2f}"
                    )
                free_quote = await self.get_account_balance(quote_asset)
                if free_quote < required_quote * 1.01:
                    raise Exception(f"Insufficient {quote_asset} balance: have {free_quote}, need approx {required_quote}")
            
            # Format quantity to avoid scientific notation
            formatted_quantity = self.format_quantity(quantity, symbol)
            
            print(f"📊 Order Validation:")
            print(f"   Symbol: {symbol}")
            print(f"   Side: {side}")
            print(f"   Raw Quantity: {quantity}")
            print(f"   Formatted: {formatted_quantity}")
            print(f"   Filters: MIN_QTY={min_qty}, MAX_QTY={max_qty}, STEP={step_size}")
            print(f"   Price: ${price:.2f}")
            if side == 'BUY' and price:
                print(f"   Notional: ${quantity * price:.4f} (MIN={min_notional})")
            print(f"🚀 Placing order: {side} {formatted_quantity} {symbol}")
            
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=formatted_quantity,
                recvWindow=10000
            )
            return {
                "orderId": order['orderId'],
                "symbol": order['symbol'],
                "side": order['side'],
                "price": float(order.get('price', 0)),
                "executedQty": float(order['executedQty']),
                "status": order['status'],
                "transactTime": order['transactTime']
            }
        except BinanceAPIException as e:
            print(f"Error placing order for {symbol} ({side}): {e}")
            raise
        except Exception as e:
            print(f"Unexpected error placing order for {symbol} ({side}): {e}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Dict:
        """Place a limit order"""
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=str(price),
                recvWindow=10000
            )
            
            return {
                "orderId": order['orderId'],
                "symbol": order['symbol'],
                "side": order['side'],
                "price": float(order['price']),
                "quantity": float(order['origQty']),
                "status": order['status']
            }
        
        except BinanceAPIException as e:
            print(f"Error placing limit order: {e}")
            raise
    
    async def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get all open orders for a symbol"""
        try:
            orders = self.client.get_open_orders(symbol=symbol, recvWindow=10000)
            return orders
        except BinanceAPIException as e:
            print(f"Error fetching open orders: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel a specific order"""
        try:
            result = self.client.cancel_order(
                symbol=symbol,
                orderId=order_id,
                recvWindow=10000
            )
            return result
        except BinanceAPIException as e:
            print(f"Error canceling order: {e}")
            raise
    
    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24 hour price change statistics"""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return {
                "priceChange": float(ticker['priceChange']),
                "priceChangePercent": float(ticker['priceChangePercent']),
                "lastPrice": float(ticker['lastPrice']),
                "highPrice": float(ticker['highPrice']),
                "lowPrice": float(ticker['lowPrice']),
                "volume": float(ticker['volume']),
                "quoteVolume": float(ticker['quoteVolume'])
            }
        except BinanceAPIException as e:
            print(f"Error fetching ticker: {e}")
            raise

    async def get_min_notional(self, symbol: str) -> float:
        """Get minimum notional value for a symbol"""
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                return 10.0  # Default minimum
            
            for f in info.get('filters', []):
                if f.get('filterType') == 'MIN_NOTIONAL':
                    return float(f.get('minNotional', 10.0))
            
            return 10.0  # Default if not found
        except Exception as e:
            print(f"Error fetching min notional: {e}")
            return 10.0

    pass
