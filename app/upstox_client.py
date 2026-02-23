"""
Upstox API client wrapper for Indian stock market trading.
Mirrors the BinanceClient interface for consistency.
Uses Upstox REST API v2/v3 directly via httpx.
"""

import httpx
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.config import config
import json


class UpstoxClient:
    """Wrapper for Upstox API operations (Indian stock market)"""

    BASE_URL = "https://api.upstox.com/v2"
    BASE_URL_V3 = "https://api.upstox.com/v3"
    HFT_URL = "https://api-hft.upstox.com/v3"
    SANDBOX_URL = "https://api-sandbox.upstox.com/v3"
    SANDBOX_URL_V2 = "https://api-sandbox.upstox.com/v2"

    # Interval mapping: Binance-style -> Upstox (unit, interval) for historical endpoint
    INTERVAL_MAP = {
        "5m":  ("minutes", "5"),
        "15m": ("minutes", "15"),
        "30m": ("minutes", "30"),
        "1h":  ("hours", "1"),
        "4h":  ("hours", "4"),
        "1d":  ("days", "1"),
        "1w":  ("weeks", "1"),
        "1M":  ("months", "1"),
    }

    # Intraday endpoint uses different interval names (current day only)
    INTRADAY_INTERVAL_MAP = {
        "5m":  "5minute",
        "15m": "15minute",
        "30m": "30minute",
    }

    # Intervals that require intraday endpoint (historical endpoint returns empty for these)
    INTRADAY_INTERVALS = {"5m", "15m", "30m"}

    def __init__(self):
        self.use_sandbox = getattr(config, "UPSTOX_SANDBOX", False)
        self.redirect_uri = config.UPSTOX_REDIRECT_URI

        # Always load both tokens:
        #   live_token  → UPSTOX_ACCESS_TOKEN      (market data – api.upstox.com)
        #   order_token → UPSTOX_SANDBOX_ACCESS_TOKEN in sandbox mode, else live token
        self.live_token    = (config.UPSTOX_ACCESS_TOKEN or "").strip()
        self.sandbox_token = (getattr(config, "UPSTOX_SANDBOX_ACCESS_TOKEN", "") or "").strip()

        # API keys: sandbox keys when sandbox mode is active
        sandbox_key    = getattr(config, "UPSTOX_SANDBOX_API_KEY", "")
        sandbox_secret = getattr(config, "UPSTOX_SANDBOX_API_SECRET", "")
        if self.use_sandbox and sandbox_key:
            self.api_key    = sandbox_key
            self.api_secret = sandbox_secret
            print("🧪 Upstox client using SANDBOX credentials")
        else:
            self.api_key    = config.UPSTOX_API_KEY
            self.api_secret = config.UPSTOX_API_SECRET

        # Legacy compat alias (kept so any direct references still work)
        self.access_token = self.live_token or self.sandbox_token

        mode = "SANDBOX" if self.use_sandbox else "LIVE"
        if not self.live_token and not self.sandbox_token:
            print(f"⚠️  No Upstox access tokens set. Run auth flow first.")
        elif not self.live_token and self.use_sandbox:
            print(f"⚠️  UPSTOX_ACCESS_TOKEN (live) not set – LTP market-data will fall back to kline price.")
            print(f"✅ Upstox client initialized (SANDBOX) – order token ready")
        else:
            print(f"✅ Upstox client initialized ({mode}) with access token")
    @property
    def _v2_base(self) -> str:
        """Market data always uses live URL – sandbox only supports order APIs."""
        return self.BASE_URL

    @property
    def _v3_base(self) -> str:
        """Market data always uses live URL – sandbox only supports order APIs."""
        return self.BASE_URL_V3

    @property
    def _order_base(self) -> str:
        """v3 order base – used for place/modify/cancel."""
        return self.SANDBOX_URL if self.use_sandbox else self.HFT_URL

    @property
    def _order_base_v2(self) -> str:
        """v2 order base – used for retrieve-all / history / trades GETs."""
        return self.SANDBOX_URL_V2 if self.use_sandbox else self.BASE_URL
    # ── Auth helpers ───────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Return the OAuth2 authorization URL the user must visit."""
        # safe='' ensures ALL special chars (including / : @) are percent-encoded
        # so the redirect_uri parameter is unambiguous to Upstox's parser
        encoded_redirect = quote(self.redirect_uri, safe="")
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={self.api_key}"
            f"&redirect_uri={encoded_redirect}"
        )

    async def exchange_code_for_token(self, auth_code: str) -> Dict:
        """
        Exchange the authorization code for an access token.
        The token must be stored in .env as UPSTOX_ACCESS_TOKEN.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/login/authorization/token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "code": auth_code,
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text
                print(f"❌ Upstox token exchange failed [{resp.status_code}]: {err_body}")
                print(f"   client_id used  : {self.api_key}")
                print(f"   redirect_uri    : {self.redirect_uri}")
                resp.raise_for_status()
            data = resp.json()
            self.live_token   = data.get("access_token", "")
            self.access_token = self.live_token  # legacy alias
            print(f"✅ Upstox access token obtained successfully")
            return data

    # ── Private request helpers ────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        """
        Headers for **market-data** requests (api.upstox.com).
        Always uses the live token.  If the live token is not set yet
        (sandbox-only setup) we fall back to the sandbox token so that
        endpoints that tolerate it (e.g. historical candles) still work.
        """
        token = self.live_token or self.sandbox_token
        if not token:
            raise RuntimeError(
                "UPSTOX_ACCESS_TOKEN is empty.\n"
                "  1. Visit GET /upstox/auth-url to get a login link.\n"
                "  2. Log in with Upstox – the callback will auto-save the token to .env.\n"
                "  3. Restart the bot (POST /upstox/start)."
            )
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _headers_order(self) -> Dict[str, str]:
        """
        Headers for **order** requests.
        Uses sandbox token in sandbox mode, live token in live mode.
        """
        token = self.sandbox_token if self.use_sandbox else self.live_token
        if not token:
            raise RuntimeError(
                "No Upstox order token available. "
                "Set UPSTOX_SANDBOX_ACCESS_TOKEN (sandbox) or UPSTOX_ACCESS_TOKEN (live)."
            )
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def _get(self, url: str, params: Dict = None) -> Dict:
        """GET for market-data endpoints – uses live token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def _get_order(self, url: str, params: Dict = None) -> Dict:
        """GET for order/trade endpoints – always uses sandbox/order token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._headers_order(), params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, url: str, payload: Dict) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers_order(), json=payload)
            if not resp.is_success:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text
                print(f"❌ POST {url} [{resp.status_code}]: {err_body}")
            resp.raise_for_status()
            return resp.json()

    # ── Market data ────────────────────────────────────────────────────

    async def get_current_price(self, instrument_token: str) -> float:
        """
        Get last traded price for an instrument.
        Uses LIVE API endpoint regardless of sandbox mode.
        instrument_token example: 'NSE_EQ|INE848E01016'
        """
        try:
            encoded = quote(instrument_token, safe="")
            url = f"{self._v2_base}/market-quote/ltp?instrument_key={encoded}"
            data = await self._get(url)
            # Response: { data: { "NSE_EQ|INE...": { "last_price": 123.45 } } }
            quotes = data.get("data", {})
            for key, val in quotes.items():
                return float(val.get("last_price", 0))
            return 0.0
        except Exception as e:
            print(f"❌ Error fetching Upstox price for {instrument_token}: {e}")
            # Return fallback price for sandbox
            if self.use_sandbox:
                print(f"⚠️  Using fallback price 10.0 for sandbox")
                return 10.0
            raise

    async def get_historical_klines(
        self,
        instrument_token: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Get historical OHLCV candle data from Upstox.

        Args:
            instrument_token: e.g. 'NSE_EQ|INE848E01016'
            interval: one of '5m','15m','30m','1h','4h','1d','1w','1M'
            limit: approximate number of candles (controls date range)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            if interval not in self.INTERVAL_MAP:
                raise ValueError(
                    f"Unsupported interval '{interval}'. Use one of {list(self.INTERVAL_MAP.keys())}"
                )

            unit, interval_val = self.INTERVAL_MAP[interval]
            encoded_token = quote(instrument_token, safe="")

            # Minute intervals: use intraday endpoint during market hours,
            # fall back to historical endpoint outside market hours
            if interval in self.INTRADAY_INTERVALS:
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                market_open  = now_ist.replace(hour=9,  minute=15, second=0, microsecond=0)
                market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
                is_market_open = market_open <= now_ist <= market_close

                if is_market_open:
                    # Use intraday endpoint for live today's candles
                    intraday_interval = self.INTRADAY_INTERVAL_MAP[interval]
                    url = (
                        f"{self._v3_base}/historical-candle/intraday/"
                        f"{encoded_token}/{intraday_interval}"
                    )
                    try:
                        data = await self._get(url)
                        candles = data.get("data", {}).get("candles", [])
                    except Exception as intraday_err:
                        print(f"⚠️ Intraday ({interval}) unavailable for {instrument_token}: {intraday_err}")
                        return pd.DataFrame(
                            columns=["timestamp", "open", "high", "low", "close", "volume"]
                        )
                else:
                    # Outside market hours: use historical endpoint (returns previous session data)
                    to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    from_date = self._calculate_from_date(interval, limit)
                    url = (
                        f"{self._v3_base}/historical-candle/"
                        f"{encoded_token}/{unit}/{interval_val}/{to_date}/{from_date}"
                    )
                    data = await self._get(url)
                    candles = data.get("data", {}).get("candles", [])
            else:
                # 1h, 4h, 1d etc — always use historical endpoint
                to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                from_date = self._calculate_from_date(interval, limit)
                url = (
                    f"{self._v3_base}/historical-candle/"
                    f"{encoded_token}/{unit}/{interval_val}/{to_date}/{from_date}"
                )
                data = await self._get(url)
                candles = data.get("data", {}).get("candles", [])

            if not candles:
                print(f"⚠️ No candle data returned for {instrument_token} ({interval})")
                return pd.DataFrame(
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )

            # Candle format: [timestamp, open, high, low, close, volume, oi]
            rows = []
            for c in candles:
                rows.append(
                    {
                        "timestamp": pd.to_datetime(c[0]),
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5]),
                    }
                )

            df = pd.DataFrame(rows)
            # Upstox returns newest first; sort ascending
            df.sort_values("timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)

            # Trim to requested limit
            if len(df) > limit:
                df = df.tail(limit).reset_index(drop=True)

            return df

        except Exception as e:
            print(f"❌ Error fetching Upstox klines: {e}")
            raise

    def _calculate_from_date(self, interval: str, limit: int) -> str:
        """Calculate from_date string based on interval and desired candle count."""
        now = datetime.now(timezone.utc)
        if interval == "5m":
            delta = timedelta(minutes=5 * limit)
        elif interval == "15m":
            delta = timedelta(minutes=15 * limit)
        elif interval == "30m":
            delta = timedelta(minutes=30 * limit)
        elif interval == "1h":
            delta = timedelta(hours=limit)
        elif interval == "4h":
            delta = timedelta(hours=4 * limit)
        elif interval == "1d":
            delta = timedelta(days=limit)
        elif interval == "1w":
            delta = timedelta(weeks=limit)
        elif interval == "1M":
            delta = timedelta(days=30 * limit)
        else:
            delta = timedelta(days=limit)

        from_dt = now - delta
        return from_dt.strftime("%Y-%m-%d")

    # ── Account / Funds ────────────────────────────────────────────────

    async def get_account_balance(self, segment: str = "SEC") -> float:
        """
        Get available margin for trading.
        In sandbox mode: returns mock balance (from UPSTOX_MOCK_BALANCE) for testing.
        In live mode: fetches real balance from Upstox API.
        segment: 'SEC' for equity, 'COM' for commodity
        """
        if self.use_sandbox:
            from app.config import config
            mock_balance = config.UPSTOX_MOCK_BALANCE
            print(f"💰 [Sandbox] Mock available margin: ₹{mock_balance:.2f}")
            return mock_balance
        
        try:
            url = f"{self._v2_base}/user/get-funds-and-margin"
            params = {"segment": segment} if segment else {}
            data = await self._get(url, params=params)

            equity = data.get("data", {}).get("equity", {})
            available = float(equity.get("available_margin", 0))
            print(f"💰 Upstox available margin: ₹{available:.2f}")
            return available
        except Exception as e:
            print(f"❌ Error fetching Upstox balance: {e}")
            raise

    # ── Portfolio ──────────────────────────────────────────────────────

    async def get_positions(self) -> List[Dict]:
        """Get current day positions. NOT supported in sandbox – returns []."""
        if self.use_sandbox:
            print("⚠️  [Sandbox] Positions endpoint not supported, returning []")
            return []
        try:
            url = f"{self._v2_base}/portfolio/short-term-positions"
            data = await self._get(url)
            return data.get("data", []) or []
        except Exception as e:
            print(f"❌ Error fetching Upstox positions: {e}")
            raise

    async def get_holdings(self) -> List[Dict]:
        """Get long-term holdings. NOT supported in sandbox – returns []."""
        if self.use_sandbox:
            print("⚠️  [Sandbox] Holdings endpoint not supported, returning []")
            return []
        try:
            url = f"{self._v2_base}/portfolio/long-term-holdings"
            data = await self._get(url)
            return data.get("data", []) or []
        except Exception as e:
            print(f"❌ Error fetching Upstox holdings: {e}")
            raise

    # ── Order placement ────────────────────────────────────────────────

    async def place_market_order(
        self,
        instrument_token: str,
        side: str,
        quantity: int,
        product: str = "I",
    ) -> Dict:
        """
        Place a market order via Upstox V3 API.

        Args:
            instrument_token: e.g. 'NSE_EQ|INE848E01016'
            side: 'BUY' or 'SELL'
            quantity: number of shares/lots
            product: 'I' (Intraday), 'D' (Delivery), 'MTF'
        """
        try:
            order_url = f"{self._order_base}/order/place"

            payload = {
                "quantity": int(quantity),
                "product": product,
                "validity": "DAY",
                "price": 0,
                "tag": "tradebot",
                "instrument_token": instrument_token,
                "order_type": "MARKET",
                "transaction_type": side.upper(),
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
                "slice": True,
            }

            print(f"🚀 Upstox order: {side} {quantity} {instrument_token} ({product})")
            data = await self._post(order_url, payload)

            order_ids = data.get("data", {}).get("order_ids", [])
            print(f"✅ Upstox order placed. IDs: {order_ids}")

            return {
                "orderId": order_ids[0] if order_ids else "unknown",
                "order_ids": order_ids,
                "symbol": instrument_token,
                "side": side.upper(),
                "quantity": quantity,
                "status": data.get("status", "success"),
            }
        except Exception as e:
            print(f"❌ Error placing Upstox order: {e}")
            raise

    async def place_limit_order(
        self,
        instrument_token: str,
        side: str,
        quantity: int,
        price: float,
        product: str = "I",
    ) -> Dict:
        """Place a limit order via Upstox V3 API."""
        try:
            order_url = f"{self._order_base}/order/place"

            payload = {
                "quantity": int(quantity),
                "product": product,
                "validity": "DAY",
                "price": float(price),
                "tag": "tradebot",
                "instrument_token": instrument_token,
                "order_type": "LIMIT",
                "transaction_type": side.upper(),
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
                "slice": False,
            }

            data = await self._post(order_url, payload)
            order_ids = data.get("data", {}).get("order_ids", [])
            return {
                "orderId": order_ids[0] if order_ids else "unknown",
                "order_ids": order_ids,
                "symbol": instrument_token,
                "side": side.upper(),
                "quantity": quantity,
                "price": price,
                "status": data.get("status", "success"),
            }
        except Exception as e:
            print(f"❌ Error placing Upstox limit order: {e}")
            raise

    # ── Order management ───────────────────────────────────────────────

    async def get_order_book(self) -> List[Dict]:
        """Get all orders placed during the day. Sandbox ✅ (returns [] on any server error)"""
        try:
            url = f"{self._order_base_v2}/order/retrieve-all"
            data = await self._get_order(url)
            return data.get("data", []) or []
        except Exception as e:
            print(f"⚠️  Could not fetch Upstox order book ({e.__class__.__name__}: {e}). Returning [].")
            return []

    async def get_order_details(self, order_id: str) -> Dict:
        """Get details for a specific order. Sandbox ✅"""
        try:
            url = f"{self._order_base_v2}/order/history"
            data = await self._get_order(url, params={"order_id": order_id})
            orders = data.get("data", [])
            return orders[-1] if orders else {}
        except Exception as e:
            print(f"❌ Error fetching Upstox order details: {e}")
            raise

    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel an open order. Sandbox ✅"""
        try:
            url = f"{self._order_base}/order/cancel"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    url,
                    headers=self._headers_order(),
                    params={"order_id": order_id},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            print(f"❌ Error cancelling Upstox order: {e}")
            raise

    async def get_trades(self) -> List[Dict]:
        """Get today's trade history. Sandbox ✅"""
        try:
            url = f"{self._order_base_v2}/order/trades"
            data = await self._get_order(url)
            return data.get("data", []) or []
        except Exception as e:
            print(f"⚠️  Could not fetch Upstox trades ({e.__class__.__name__}: {e}). Returning [].")
            return []

    # ── Utility ────────────────────────────────────────────────────────

    async def get_quantity_from_quote(
        self, instrument_token: str, quote_amount: float
    ) -> int:
        """
        Convert a rupee amount into share quantity.
        Returns integer quantity (Upstox requires whole numbers for equities).
        """
        try:
            price = await self.get_current_price(instrument_token)
            if price <= 0:
                raise ValueError(f"Invalid price {price} for {instrument_token}")

            qty = int(quote_amount / price)
            if qty < 1:
                qty = 1
            print(f"💹 Upstox: ₹{quote_amount:.2f} / ₹{price:.2f} = {qty} shares")
            return qty
        except Exception as e:
            print(f"❌ Error calculating Upstox quantity: {e}")
            raise

    def format_quantity(self, quantity: float, instrument_token: str) -> str:
        """Format quantity – Upstox uses integer quantities for equities."""
        return str(int(quantity))
