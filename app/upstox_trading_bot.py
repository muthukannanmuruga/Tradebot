"""
Upstox Trading Bot – mirrors TradingBot logic for Indian stock market.
Uses UpstoxClient for data + orders, reuses DeepSeekAI and TechnicalIndicators.
Stores trades in the same database with a 'market' column to distinguish.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import json

from app.upstox_client import UpstoxClient
from app.deepseek_ai import DeepSeekAI
from app.indicators import TechnicalIndicators
from app.database import SessionLocal, Trade, Portfolio, BotMetrics
from app.config import config


class UpstoxTradingBot:
    """Trading bot for Indian stock market via Upstox API"""

    def __init__(self):
        self.upstox = UpstoxClient()
        self.ai = DeepSeekAI()
        self.is_running = False
        # Track position per instrument: {"NSE_EQ|INE...": None, "LONG", or "SHORT"}
        self.positions: Dict[str, Optional[str]] = {}
        self.last_check = None
        self.trade_count = 0
        self.daily_trades = 0
        self.last_trade_date = None
        # Upstox trading pairs - will be set in start() if auto-select enabled
        self.auto_select_enabled = config.UPSTOX_AUTO_SELECT_PAIRS
        self.trading_pairs = config.UPSTOX_TRADING_PAIRS  # Default to config
        
        self.product_type = config.UPSTOX_PRODUCT_TYPE  # I, D, MTF
        # Margin utilization % for intraday (default 100%)
        self.margin_percent = config.UPSTOX_MARGIN_PERCENT
        # Background task for auto square-off sync
        self._sync_task = None

        # Initialize positions and sync from DB
        self._sync_positions_from_db()
    
    def _get_ai_selected_pairs(self) -> list:
        """Legacy sync wrapper - kept for compatibility."""
        return config.UPSTOX_TRADING_PAIRS
    
    async def _get_ai_selected_pairs_async(self) -> list:
        """Get trading pairs from AI sentiment analysis for Indian stocks (async version)."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get("http://localhost:8000/ai/indian-market-sentiment")
                result = response.json()
            
            suggested_trades = result.get("suggested_trades", [])
            
            if not suggested_trades:
                print("⚠️  AI returned no trade suggestions, using config pairs")
                return config.UPSTOX_TRADING_PAIRS
            
            # Extract ISINs and format as NSE_EQ|ISIN instrument tokens
            instruments = []
            for trade in suggested_trades[:10]:  # Limit to top 10
                symbol = trade.get("symbol", "")
                isin = trade.get("isin", "")
                
                if isin and isin.startswith("INE") and len(isin) == 12:
                    # Format as Upstox instrument token: NSE_EQ|ISIN
                    instrument = f"NSE_EQ|{isin}"
                    instruments.append(instrument)
                    print(f"  • {symbol} ({isin}) -> {instrument}")
                elif symbol:
                    print(f"  ⚠️  {symbol}: No valid ISIN provided by AI")
            
            if not instruments:
                print("⚠️  Could not extract valid ISINs from AI, using config pairs")
                return config.UPSTOX_TRADING_PAIRS
            
            print(f"🎯 AI selected {len(instruments)} NSE stocks")
            return instruments
            
        except Exception as e:
            print(f"❌ Error fetching AI sentiment: {e}, using config pairs")
            import traceback
            traceback.print_exc()
            return config.UPSTOX_TRADING_PAIRS

    def _sync_positions_from_db(self):
        """Sync position state from database on initialization."""
        db = SessionLocal()
        try:
            is_sandbox = config.UPSTOX_SANDBOX
            for pair in self.trading_pairs:
                portfolio_entry = (
                    db.query(Portfolio).filter(
                        Portfolio.pair == pair,
                        Portfolio.product_type == self.product_type,
                        Portfolio.is_sandbox == is_sandbox
                    ).first()
                )
                if portfolio_entry:
                    if portfolio_entry.quantity < 0:
                        self.positions[pair] = "SHORT"
                        print(
                            f"📍 Restored Upstox position: {pair} = SHORT "
                            f"(Qty: {portfolio_entry.quantity} @ ₹{portfolio_entry.entry_price:.2f})"
                        )
                    else:
                        self.positions[pair] = "LONG"
                        print(
                            f"📍 Restored Upstox position: {pair} = LONG "
                            f"(Qty: {portfolio_entry.quantity} @ ₹{portfolio_entry.entry_price:.2f})"
                        )
                else:
                    self.positions[pair] = None
            self._get_or_create_metrics(db)
        finally:
            db.close()

    def _get_or_create_metrics(self, db):
        """Get or create BotMetrics record for Upstox."""
        is_sandbox = config.UPSTOX_SANDBOX
        metrics = db.query(BotMetrics).filter(
            BotMetrics.market == "upstox",
            BotMetrics.product_type == self.product_type,
            BotMetrics.is_sandbox == is_sandbox
        ).first()
        if not metrics:
            metrics = BotMetrics(
                market="upstox",
                product_type=self.product_type,
                is_sandbox=is_sandbox,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit_loss=0.0,
                win_rate=0.0,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(metrics)
            db.commit()
            print(f"📊 Initialized BotMetrics table (upstox, {self.product_type})")
        return metrics

    # ── Bot lifecycle ──────────────────────────────────────────────────

    async def start(self):
        """Start the Upstox trading bot."""
        # ── Pre-flight: token check ──────────────────────────────────
        if not self.upstox.access_token or not self.upstox.access_token.strip():
            print("\n" + "="*60)
            print("⛔  Cannot start Upstox bot – access token is missing!")
            print("="*60)
            print("  1. Open: GET http://localhost:8000/upstox/auth-url")
            print("  2. Visit the URL in a browser and log in with Upstox.")
            print("  3. The callback will auto-save UPSTOX_ACCESS_TOKEN to .env.")
            print("  4. POST /upstox/start again.")
            print("="*60 + "\n")
            self.is_running = False
            return
        
        # ── Fetch AI-selected pairs if enabled ───────────────────────────
        if self.auto_select_enabled:
            print("🤖 AI Auto-pair selection ENABLED for Upstox")
            ai_pairs = await self._get_ai_selected_pairs_async()
            if ai_pairs:
                self.trading_pairs = ai_pairs
                # Re-sync positions for new pairs
                self._sync_positions_from_db()

        self.is_running = True
        print("🚀 Upstox Trading bot started!")
        print(f"📊 Trading instruments: {', '.join(self.trading_pairs)}")
        print(f"📦 Product type: {self.product_type}")
        print(f"⏰ Check interval: {config.CHECK_INTERVAL_SECONDS}s")
        
        # Always run a startup sync regardless of product type.
        # Uses get_positions() (intraday) + get_holdings() (delivery) as truth.
        print("⚡ Running startup position sync (clearing any stale DB entries)...")
        asyncio.create_task(self._sync_auto_squareoffs())

        # Schedule daily 3:30 PM sync for intraday auto-squareoff cleanup
        if self.product_type == "I":
            self._sync_task = asyncio.create_task(self._schedule_sync_task())
            print("📅 Auto square-off sync task scheduled for 3:30 PM IST")

        while self.is_running:
            try:
                await self.trading_loop()
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)
            except Exception as e:
                print(f"❌ Error in Upstox trading loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)

    async def stop(self):
        """Stop the trading bot."""
        self.is_running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        print("🛑 Upstox Trading bot stopped!")

    # ── Auto square-off sync ───────────────────────────────────────────

    async def _schedule_sync_task(self):
        """Background task that runs daily at 3:30 PM IST to sync auto square-offs."""
        while self.is_running:
            try:
                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                target_time = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)

                # If already past 3:30 PM today (catch-up may have already run),
                # always push to tomorrow so we never double-fire on the same day.
                if now_ist >= target_time:
                    target_time += timedelta(days=1)

                # Skip weekends — advance to Monday if target falls on Sat/Sun
                while target_time.weekday() >= 5:
                    target_time += timedelta(days=1)

                wait_seconds = (target_time - now_ist).total_seconds()
                print(f"⏰ Next auto square-off sync at {target_time.strftime('%Y-%m-%d %H:%M IST')}")

                await asyncio.sleep(wait_seconds)

                # Run the sync
                if self.is_running:
                    await self._sync_auto_squareoffs()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in sync task scheduler: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def _sync_auto_squareoffs(self):
        """Sync DB positions against Upstox live positions.

        Uses ``get_positions()`` as the source of truth:
        - If an instrument has net-zero quantity in Upstox it is flat (squared off).
        - We also try to enrich with the closing order price from order-book/trades.
        - Falls back to entry_price (₹0 P&L) if no closing order is findable
          (e.g. cross-session restart where order history has already rolled off).
        """
        try:
            print("\n" + "="*60)
            print("🔄 Syncing positions: DB vs Upstox live positions...")
            print("="*60)

            db = SessionLocal()
            try:
                is_sandbox = config.UPSTOX_SANDBOX

                # ── 1. Get DB open positions ────────────────────────────
                open_positions = db.query(Portfolio).filter(
                    Portfolio.is_sandbox == is_sandbox
                ).all()

                if not open_positions:
                    print("✅ No open positions in DB – nothing to sync")
                    return

                print(f"📋 Found {len(open_positions)} open position(s) in DB")

                # ── 2. Get LIVE positions from Upstox ───────────────────
                # Check both short-term (intraday) and long-term (delivery/holdings)
                # so both product types are handled correctly.
                # sandbox always returns [] so all sandbox DB entries will be cleaned.
                try:
                    intraday_positions = await self.upstox.get_positions()
                except Exception as e:
                    print(f"⚠️  Could not fetch intraday positions ({e}) – skipping sync to avoid false closes")
                    return

                try:
                    delivery_holdings = await self.upstox.get_holdings()
                except Exception as e:
                    print(f"⚠️  Could not fetch delivery holdings ({e}) – will only check intraday positions")
                    delivery_holdings = []

                # Build set of instruments still open (non-zero qty) in either category
                live_open = {
                    pos["instrument_token"]
                    for pos in intraday_positions
                    if pos.get("quantity", 0) != 0
                } | {
                    h["instrument_token"]
                    for h in delivery_holdings
                    if h.get("quantity", 0) != 0
                }
                print(f"📡 Upstox live open: intraday={len(intraday_positions)} delivery={len(delivery_holdings)} → open instruments: {live_open or 'none'}")

                # ── 3. Also fetch today's orders/trades for exit price ──
                orders = await self.upstox.get_order_book()
                trades = await self.upstox.get_trades()

                # ── 4. Process each DB position ─────────────────────────
                for portfolio_entry in open_positions:
                    instrument  = portfolio_entry.pair
                    db_qty      = portfolio_entry.quantity
                    is_short    = db_qty < 0
                    abs_qty     = abs(db_qty)
                    entry_price = portfolio_entry.entry_price
                    expected_side = "BUY" if is_short else "SELL"
                    position_type = "SHORT" if is_short else "LONG"

                    # ── 4a. If position is still live in Upstox → skip ──
                    if instrument in live_open:
                        print(f"ℹ️  {instrument} still open in Upstox – leaving in DB")
                        continue

                    # ── 4b. Position is flat in Upstox → close in DB ────
                    print(f"🔍 {instrument} {position_type} is flat in Upstox – closing in DB...")

                    # Try to find closing order for P&L (same-day order history).
                    closing_order_id = None
                    exit_price = None

                    for trade in trades:
                        if (
                            trade.get("instrument_token") == instrument
                            and trade.get("transaction_type") == expected_side
                        ):
                            exit_price = float(trade.get("price", 0) or 0)
                            closing_order_id = str(trade.get("order_id", ""))
                            break

                    if not exit_price:
                        for order in orders:
                            if (
                                order.get("instrument_token") == instrument
                                and order.get("transaction_type") == expected_side
                                and order.get("status") == "complete"
                            ):
                                exit_price = float(order.get("average_price", 0) or 0)
                                closing_order_id = str(order.get("order_id", ""))
                                break

                    # ── 4c. Duplicate guard: trade already recorded ──────
                    if closing_order_id and db.query(Trade).filter(
                        Trade.order_id == closing_order_id
                    ).first():
                        print(f"⚠️  order_id {closing_order_id} already in trades table – removing stale portfolio entry")
                        db.delete(portfolio_entry)
                        self.positions[instrument] = None
                        db.commit()
                        continue

                    # ── 4d. Calculate P&L ────────────────────────────────
                    if not exit_price:
                        # Cross-session: order history gone. Use entry_price → ₹0 P&L.
                        exit_price = entry_price
                        note = "[Stale Sync] Position flat in Upstox; no price data available"
                        print(f"⚠️  No exit price found for {instrument} – recording ₹0 P&L stale close")
                    else:
                        note = f"[Auto Square-off] Closed at ₹{exit_price:.2f}"

                    if is_short:
                        realized_pl = (entry_price - exit_price) * abs_qty
                    else:
                        realized_pl = (exit_price - entry_price) * abs_qty

                    # ── 4e. Insert Trade record ──────────────────────────
                    trade_record = Trade(
                        pair=instrument,
                        product_type=portfolio_entry.product_type,  # Preserve product type from portfolio
                        side=expected_side,
                        quantity=abs_qty,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        status="CLOSED",
                        closed_at=datetime.now(timezone.utc),
                        is_sandbox=is_sandbox,
                        order_id=closing_order_id or f"sync-{instrument}-{int(datetime.now().timestamp())}",
                        ai_reasoning=note,
                        confidence=0.0,
                        profit_loss=realized_pl,
                        profit_loss_percent=(
                            (realized_pl / (entry_price * abs_qty)) * 100
                        ) if entry_price else 0.0,
                    )
                    db.add(trade_record)
                    db.delete(portfolio_entry)
                    self.positions[instrument] = None
                    self._update_metrics(db, realized_pl)
                    db.commit()

                    print(f"✅ Closed {instrument} {position_type} @ ₹{exit_price:.2f} | P&L: ₹{realized_pl:.2f}")

                print("="*60)
                print("✅ Position sync complete")
                print("="*60 + "\n")

            finally:
                db.close()

        except Exception as e:
            print(f"❌ Error syncing positions: {e}")
            import traceback
            traceback.print_exc()

    # ── Core trading loop ──────────────────────────────────────────────

    async def trading_loop(self):
        """Main trading loop – processes all Upstox trading instruments."""
        try:
            self._reset_daily_counter()

            if self.daily_trades >= config.UPSTOX_MAX_DAILY_TRADES:
                print(f"⚠️ Upstox daily trade limit reached ({self.daily_trades}/{config.UPSTOX_MAX_DAILY_TRADES})")
                return

            # NSE market hours: 9:15 AM – 3:30 PM IST (UTC+5:30)
            now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            market_open  = now_ist.replace(hour=9,  minute=15, second=0, microsecond=0)
            market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
            if not (market_open <= now_ist <= market_close):
                print(
                    f"⏸️  NSE market closed – current IST time "
                    f"{now_ist.strftime('%H:%M')} (open 09:15–15:30). Skipping."
                )
                return

            for instrument in self.trading_pairs:
                await self._process_trading_pair(instrument)

            self.last_check = datetime.now(timezone.utc)

        except Exception as e:
            print(f"❌ Error in Upstox trading loop: {e}")
            import traceback
            traceback.print_exc()

    async def _process_trading_pair(self, instrument_token: str):
        """Process a single Upstox instrument with multi-timeframe analysis."""
        try:
            # Multi-timeframe analysis
            mtf_analysis = await self.get_multi_timeframe_analysis(instrument_token)

            # Portfolio snapshot
            try:
                portfolio_snapshot = await self.get_portfolio()
            except Exception:
                portfolio_snapshot = None

            # Recent trades (last 3) for context
            recent_trades = []
            db = SessionLocal()
            try:
                rows = (
                    db.query(Trade)
                    .filter(
                        Trade.pair == instrument_token,
                        Trade.is_sandbox == config.UPSTOX_SANDBOX,
                    )
                    .order_by(Trade.created_at.desc())
                    .limit(3)
                    .all()
                )
                for r in rows:
                    recent_trades.append(
                        f"{r.side} {r.quantity} {r.pair} @ "
                        f"{getattr(r, 'entry_price', 'N/A')} on {r.created_at}"
                    )
            except Exception:
                recent_trades = []
            finally:
                db.close()

            current_position = self.positions.get(instrument_token)

            # AI decision
            ai_decision = await self.ai.get_trading_decision(
                instrument_token,
                mtf_analysis["indicators"],
                current_position,
                intraday_signal=None,
                portfolio_snapshot=portfolio_snapshot,
                recent_trades=recent_trades,
                market="upstox",
            )

            # Display
            alignment = mtf_analysis["indicators"]["summary"]["timeframe_alignment"]
            print(f"\n{'='*60}")
            print(f"📊 {instrument_token} - Upstox Multi-Timeframe Analysis")
            print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(
                f"💰 Price: ₹{mtf_analysis['indicators']['summary']['current_price']:.2f}"
            )
            print(f"\n🔄 Timeframe Alignment: {alignment['alignment']}")
            print(
                f"   • MACD Bullish: {alignment['macd_bullish_count']}/4 timeframes"
            )
            print(
                f"   • RSI Suitable: {alignment['rsi_bullish_count']}/4 timeframes"
            )
            print(
                f"   • EMA Bullish: {alignment['ema_bullish_count']}/4 timeframes"
            )

            for tf, name in [
                ("5min", "5m"),
                ("1hour", "1h"),
                ("4hour", "4h"),
                ("1day", "1d"),
            ]:
                ind = mtf_analysis["indicators"][tf]
                print(
                    f"   {name:4s}: EMA {ind['ema_trend']:8s} | "
                    f"MACD {ind['macd_trend']:8s} | "
                    f"RSI {ind['rsi']:5.1f} ({ind['rsi_zone']})"
                )

            print(f"\n🎯 Position: {current_position or 'None'}")
            print(
                f"🤖 AI Decision: {ai_decision['decision']} "
                f"(Confidence: {ai_decision['confidence']:.2%})"
            )
            reasoning = ai_decision["reasoning"]
            print(
                f"💭 Reasoning: {reasoning[:200]}..."
                if len(reasoning) > 200
                else f"💭 Reasoning: {reasoning}"
            )
            print(f"{'='*60}\n")

            # Confidence gate - skip low-confidence BUY/SELL signals
            if ai_decision["decision"] in ("BUY", "SELL") and \
               ai_decision.get("confidence", 0.0) < config.AI_CONFIDENCE_THRESHOLD:
                print(
                    f"⚠️ Skipping {ai_decision['decision']} – confidence "
                    f"{ai_decision['confidence']:.2%} below threshold {config.AI_CONFIDENCE_THRESHOLD:.2%}"
                )
                return

            # Execute
            await self._execute_decision(instrument_token, ai_decision, mtf_analysis)

        except Exception as e:
            print(f"❌ Error processing Upstox {instrument_token}: {e}")
            import traceback
            traceback.print_exc()

    async def _execute_decision(
        self, instrument_token: str, ai_decision: Dict, analysis: Dict
    ):
        """Execute trading decision for an Upstox instrument.
        Supports both LONG and SHORT (intraday only) positions.
        """
        action = ai_decision["decision"]
        confidence = ai_decision["confidence"]
        current_position = self.positions.get(instrument_token)
        is_intraday = self.product_type == "I"

        # Calculate trade amount adjusted by margin %
        trade_amount = config.UPSTOX_TRADING_AMOUNT * (self.margin_percent / 100.0)

        if action == "BUY":
            # ── Close SHORT first if open ────────────────────────────
            if current_position == "SHORT":
                db = SessionLocal()
                try:
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(
                            Portfolio.pair == instrument_token,
                            Portfolio.is_sandbox == config.UPSTOX_SANDBOX,
                        )
                        .first()
                    )
                    if portfolio_entry:
                        quantity = int(abs(portfolio_entry.quantity))
                        print(f"📈 Closing SHORT: BUY {quantity} {instrument_token}")
                        indicators_5m = analysis["indicators"]["5min"]
                        await self.execute_trade(
                            instrument_token, "BUY", quantity,
                            f"[Close SHORT] {ai_decision['reasoning']}",
                            confidence, indicators_5m,
                        )
                finally:
                    db.close()
                self.positions[instrument_token] = None
                current_position = None

            # ── Open LONG ────────────────────────────────────────────
            if current_position != "LONG":
                risk_check = await self._check_risk_limits(instrument_token, trade_amount)
                if not risk_check["allowed"]:
                    print(f"🚫 Trade blocked by risk management: {risk_check['reason']}")
                    return

                quantity = await self.upstox.get_quantity_from_quote(
                    instrument_token, trade_amount
                )
                indicators_5m = analysis["indicators"]["5min"]
                await self.execute_trade(
                    instrument_token, "BUY", quantity,
                    ai_decision["reasoning"], confidence, indicators_5m,
                )
                self.positions[instrument_token] = "LONG"

        elif action == "SELL":
            # ── Close LONG first if open ─────────────────────────────
            if current_position == "LONG":
                db = SessionLocal()
                try:
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(
                            Portfolio.pair == instrument_token,
                            Portfolio.is_sandbox == config.UPSTOX_SANDBOX,
                        )
                        .first()
                    )
                    if portfolio_entry:
                        quantity = int(portfolio_entry.quantity)
                        print(f"📉 Closing LONG: SELL {quantity} {instrument_token}")
                        indicators_5m = analysis["indicators"]["5min"]
                        await self.execute_trade(
                            instrument_token, "SELL", quantity,
                            f"[Close LONG] {ai_decision['reasoning']}",
                            confidence, indicators_5m,
                        )
                    else:
                        print(f"⚠️ No portfolio entry for {instrument_token}, skipping close")
                finally:
                    db.close()
                self.positions[instrument_token] = None
                current_position = None

            # ── Open SHORT (intraday only) ───────────────────────────
            if is_intraday and current_position != "SHORT":
                risk_check = await self._check_risk_limits(instrument_token, trade_amount)
                if not risk_check["allowed"]:
                    print(f"🚫 Short blocked by risk management: {risk_check['reason']}")
                    return

                quantity = await self.upstox.get_quantity_from_quote(
                    instrument_token, trade_amount
                )
                print(f"📉 Opening SHORT: SELL {quantity} {instrument_token} (margin {self.margin_percent}%)")
                indicators_5m = analysis["indicators"]["5min"]
                await self.execute_trade(
                    instrument_token, "SELL", quantity,
                    f"[Short] {ai_decision['reasoning']}",
                    confidence, indicators_5m,
                )
                self.positions[instrument_token] = "SHORT"
            elif not is_intraday and current_position is None:
                print(f"✋ SELL signal but product is Delivery – shorting not allowed")

        else:
            print(f"✋ Holding position (Current: {current_position})")

    # ── Trade execution ────────────────────────────────────────────────

    async def execute_trade(
        self,
        instrument_token: str,
        side: str,
        quantity: int,
        reasoning: str,
        confidence: float = None,
        indicators: Dict = None,
    ):
        """Execute an Upstox trade and log to database.

        Position state is managed by _execute_decision; this method only
        places the order and persists Trade / Portfolio / Metrics rows.
        """
        try:
            order = await self.upstox.place_market_order(
                instrument_token, side, quantity, product=self.product_type
            )

            current_price = await self.upstox.get_current_price(instrument_token)
            executed_qty = int(order.get("quantity", quantity))

            is_opening_short = reasoning.startswith("[Short]")
            is_closing_short = reasoning.startswith("[Close SHORT]")
            is_closing_long = reasoning.startswith("[Close LONG]")

            db = SessionLocal()
            try:
                is_sandbox = config.UPSTOX_SANDBOX
                trade = Trade(
                    pair=instrument_token,
                    product_type=self.product_type,
                    side=side,
                    quantity=executed_qty,
                    entry_price=current_price if side == "BUY" and not is_closing_short else 0,
                    exit_price=current_price if (side == "SELL" and not is_opening_short) else None,
                    status="OPEN" if not (is_closing_short or is_closing_long) else "CLOSED",
                    order_id=str(order.get("orderId", "")),
                    ai_reasoning=reasoning,
                    confidence=confidence or 0.0,
                    is_sandbox=is_sandbox,
                )
                db.add(trade)
                db.commit()

                # ── Opening a new LONG ─────────────────────────────────
                if side == "BUY" and not is_closing_short:
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(
                            Portfolio.pair == instrument_token,
                            Portfolio.product_type == self.product_type,
                            Portfolio.is_sandbox == is_sandbox,
                        )
                        .first()
                    )
                    if portfolio_entry:
                        old_value = portfolio_entry.quantity * portfolio_entry.entry_price
                        new_value = executed_qty * current_price
                        portfolio_entry.quantity += executed_qty
                        portfolio_entry.entry_price = (
                            (old_value + new_value) / portfolio_entry.quantity
                        )
                        portfolio_entry.current_price = current_price
                        portfolio_entry.total_invested = portfolio_entry.entry_price * portfolio_entry.quantity
                        portfolio_entry.current_value = current_price * portfolio_entry.quantity
                        portfolio_entry.unrealized_pl = (
                            (current_price - portfolio_entry.entry_price)
                            * portfolio_entry.quantity
                        )
                        portfolio_entry.updated_at = datetime.now(timezone.utc)
                    else:
                        portfolio_entry = Portfolio(
                            pair=instrument_token,
                            product_type=self.product_type,
                            quantity=executed_qty,
                            entry_price=current_price,
                            current_price=current_price,
                            total_invested=current_price * executed_qty,
                            current_value=current_price * executed_qty,
                            unrealized_pl=0.0,
                            updated_at=datetime.now(timezone.utc),
                            is_sandbox=is_sandbox,
                        )
                        db.add(portfolio_entry)
                    db.commit()
                    print(f"💼 Portfolio updated: {instrument_token} LONG opened")

                # ── Opening a new SHORT (sell to open) ──────────────────
                elif side == "SELL" and is_opening_short:
                    portfolio_entry = Portfolio(
                        pair=instrument_token,
                        product_type=self.product_type,
                        quantity=-executed_qty,  # negative = short
                        entry_price=current_price,
                        current_price=current_price,
                        total_invested=current_price * executed_qty,
                        current_value=current_price * executed_qty,
                        unrealized_pl=0.0,
                        updated_at=datetime.now(timezone.utc),
                        is_sandbox=is_sandbox,
                    )
                    db.add(portfolio_entry)
                    db.commit()
                    print(f"💼 Portfolio updated: {instrument_token} SHORT opened @ ₹{current_price:.2f}")

                # ── Closing a LONG (sell to close) ──────────────────────
                elif side == "SELL" and not is_opening_short:
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(
                            Portfolio.pair == instrument_token,
                            Portfolio.product_type == self.product_type,
                            Portfolio.is_sandbox == is_sandbox
                        )
                        .first()
                    )
                    realized_pl = 0.0
                    if portfolio_entry:
                        realized_pl = (
                            (current_price - portfolio_entry.entry_price)
                            * abs(portfolio_entry.quantity)
                        )
                        trade.profit_loss = realized_pl
                        trade.profit_loss_percent = (
                            (realized_pl / (portfolio_entry.entry_price * abs(portfolio_entry.quantity)))
                            * 100
                        ) if portfolio_entry.entry_price else 0.0
                        trade.entry_price = portfolio_entry.entry_price
                        # mark trade as closed and timestamp it
                        trade.closed_at = datetime.now(timezone.utc)
                        trade.status = "CLOSED"
                        db.delete(portfolio_entry)
                        db.commit()
                        print(
                            f"💼 Portfolio: {instrument_token} LONG closed (P&L: ₹{realized_pl:.2f})"
                        )
                        self._update_metrics(db, realized_pl)

                # ── Closing a SHORT (buy to cover) ──────────────────────
                elif side == "BUY" and is_closing_short:
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(
                            Portfolio.pair == instrument_token,
                            Portfolio.product_type == self.product_type,
                            Portfolio.is_sandbox == is_sandbox,
                        )
                        .first()
                    )
                    realized_pl = 0.0
                    if portfolio_entry:
                        # Short P&L = (entry - exit) * qty
                        realized_pl = (
                            (portfolio_entry.entry_price - current_price)
                            * abs(portfolio_entry.quantity)
                        )
                        trade.profit_loss = realized_pl
                        trade.profit_loss_percent = (
                            (realized_pl / (portfolio_entry.entry_price * abs(portfolio_entry.quantity)))
                            * 100
                        ) if portfolio_entry.entry_price else 0.0
                        trade.entry_price = portfolio_entry.entry_price
                        # mark trade as closed and timestamp it
                        trade.closed_at = datetime.now(timezone.utc)
                        trade.status = "CLOSED"
                        db.delete(portfolio_entry)
                        db.commit()
                        print(
                            f"💼 Portfolio: {instrument_token} SHORT closed (P&L: ₹{realized_pl:.2f})"
                        )
                        self._update_metrics(db, realized_pl)

                self.trade_count += 1
                # Only count opening trades toward daily limit (not closings)
                # Opening = BUY new LONG or SELL new SHORT
                # Closing = SELL existing LONG or BUY existing SHORT
                is_opening = (side == "BUY" and not is_closing_short) or (side == "SELL" and is_opening_short)
                if is_opening:
                    self.daily_trades += 1
                
                print(
                    f"✅ Upstox trade: {side} {executed_qty} {instrument_token} @ ₹{current_price:.2f}"
                )
                print(f"📝 Order ID: {order.get('orderId')}")

            finally:
                db.close()

            return order

        except Exception as e:
            print(f"❌ Upstox trade execution failed: {e}")
            raise

    def _update_metrics(self, db, realized_pl: float):
        """Update BotMetrics after closing a position."""
        metrics = self._get_or_create_metrics(db)
        metrics.total_trades += 1
        metrics.total_profit_loss += realized_pl
        if realized_pl > 0:
            metrics.winning_trades += 1
        elif realized_pl < 0:
            metrics.losing_trades += 1
        total_completed = metrics.winning_trades + metrics.losing_trades
        metrics.win_rate = (
            (metrics.winning_trades / total_completed * 100)
            if total_completed > 0
            else 0.0
        )
        metrics.last_trade_time = datetime.now(timezone.utc)
        metrics.updated_at = datetime.now(timezone.utc)
        db.commit()
        print(
            f"📊 Metrics: Win Rate {metrics.win_rate:.1f}%, "
            f"Total P&L: ₹{metrics.total_profit_loss:.2f}"
        )

    # ── Multi-timeframe analysis ───────────────────────────────────────

    async def get_multi_timeframe_analysis(self, instrument_token: str) -> Dict:
        """Get multi-timeframe market analysis."""
        try:
            print(f"📥 Fetching Upstox multi-timeframe data for {instrument_token}...")
            # 400 * 5m = 2000 min ≈ 33 hrs → always covers last 2 NSE sessions
            df_5m = await self.upstox.get_historical_klines(
                instrument_token, interval="5m", limit=400
            )
            df_1h = await self.upstox.get_historical_klines(
                instrument_token, interval="1h", limit=200
            )
            df_4h = await self.upstox.get_historical_klines(
                instrument_token, interval="4h", limit=100
            )
            df_1d = await self.upstox.get_historical_klines(
                instrument_token, interval="1d", limit=100
            )

            multi_tf_indicators = (
                TechnicalIndicators.calculate_multi_timeframe_indicators(
                    df_5m, df_1h, df_4h, df_1d
                )
            )

            return {
                "symbol": instrument_token,
                "indicators": multi_tf_indicators,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"❌ Error getting Upstox multi-TF analysis: {e}")
            raise

    async def get_market_analysis(self, instrument_token: str) -> Dict:
        """Get single-timeframe market analysis."""
        try:
            df = await self.upstox.get_historical_klines(
                instrument_token, interval="1h", limit=200
            )
            indicators = TechnicalIndicators.calculate_all_indicators(df)

            indicators_serializable = {}
            for key, value in indicators.items():
                if hasattr(value, "item"):
                    indicators_serializable[key] = value.item()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    indicators_serializable[key] = value
                else:
                    indicators_serializable[key] = str(value)

            return {
                "symbol": instrument_token,
                "indicators": indicators_serializable,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"❌ Error getting Upstox market analysis: {e}")
            raise

    # ── Status and portfolio ───────────────────────────────────────────

    async def get_status(self) -> Dict:
        """Get Upstox bot status."""
        db = SessionLocal()
        try:
            total_trades = db.query(Trade).count()
            status = {
                "is_running": self.is_running,
                "last_check": self.last_check,
                "total_trades": total_trades,
                "positions": self.positions,
                "trading_pairs": self.trading_pairs,
                "daily_trades": self.daily_trades,
                "max_daily_trades": config.UPSTOX_MAX_DAILY_TRADES,
                "market": "upstox",
                "product_type": self.product_type,
            }
            if self.is_running:
                prices = {}
                for pair in self.trading_pairs:
                    try:
                        prices[pair] = await self.upstox.get_current_price(pair)
                    except Exception as e:
                        prices[pair] = f"Error: {e}"
                status["current_prices"] = prices
            return status
        finally:
            db.close()

    async def get_portfolio(self) -> Dict:
        """Get current portfolio status from DB + live prices."""
        try:
            try:
                available_balance = await self.upstox.get_account_balance()
            except Exception as e:
                print(f"⚠️ Balance unavailable (sandbox/inactive segments): {e}")
                available_balance = 0.0
            db = SessionLocal()
            try:
                is_sandbox = config.UPSTOX_SANDBOX
                portfolio_entries = db.query(Portfolio).filter(Portfolio.is_sandbox == is_sandbox).all()
                total_invested = 0.0
                total_pnl = 0.0
                positions_list = []

                # Only update Upstox instruments (contain '|')
                for entry in portfolio_entries:
                    if "|" not in entry.pair:
                        continue  # Skip Binance pairs
                    try:
                        current_price = await self.upstox.get_current_price(entry.pair)
                        entry.current_price = current_price
                        entry.total_invested = round(entry.entry_price * entry.quantity, 2)
                        entry.current_value  = round(current_price * entry.quantity, 2)
                        entry.unrealized_pl = (
                            (current_price - entry.entry_price) * entry.quantity
                        )
                        entry.updated_at = datetime.now(timezone.utc)

                        total_invested += entry.total_invested
                        total_pnl += entry.unrealized_pl

                        positions_list.append(
                            {
                                "pair": entry.pair,
                                "product_type": entry.product_type,
                                "quantity": entry.quantity,
                                "entry_price": entry.entry_price,
                                "current_price": entry.current_price,
                                "total_invested": entry.total_invested,
                                "current_value": entry.current_value,
                                "unrealized_pl": entry.unrealized_pl,
                            }
                        )
                    except Exception as e:
                        print(f"⚠️ Could not update price for {entry.pair}: {e}")

                db.commit()

                completed_trades = (
                    db.query(Trade).filter(Trade.side == "SELL").all()
                )
                winning = sum(
                    1 for t in completed_trades if (getattr(t, "profit_loss", None) or 0) > 0
                )
                win_rate = (
                    (winning / len(completed_trades) * 100) if completed_trades else 0.0
                )

            finally:
                db.close()

            pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
            return {
                "total_balance": available_balance + total_invested + total_pnl,
                "available_balance": available_balance,
                "total_invested": total_invested,
                "open_positions": len(positions_list),
                "total_profit_loss": total_pnl,
                "profit_loss_percent": pnl_percent,
                "win_rate": win_rate,
                "positions": positions_list,
            }

        except Exception as e:
            print(f"❌ Error getting Upstox portfolio: {e}")
            raise

    # ── Risk management ────────────────────────────────────────────────

    async def _check_risk_limits(
        self, instrument_token: str, trade_amount: float
    ) -> Dict:
        """Check if trade passes risk management limits (Upstox INR-based)."""
        db = SessionLocal()
        try:
            is_sandbox = config.UPSTOX_SANDBOX
            open_positions = db.query(Portfolio).filter(Portfolio.is_sandbox == is_sandbox).count()
            if open_positions >= config.UPSTOX_MAX_OPEN_POSITIONS:
                return {
                    "allowed": False,
                    "reason": f"Max open positions reached ({open_positions}/{config.UPSTOX_MAX_OPEN_POSITIONS})",
                }

            pair_position = (
                db.query(Portfolio).filter(
                    Portfolio.pair == instrument_token,
                    Portfolio.is_sandbox == is_sandbox
                ).first()
            )
            if pair_position:
                current_value = abs(pair_position.quantity) * pair_position.current_price
                if current_value + trade_amount > config.UPSTOX_MAX_POSITION_PER_PAIR:
                    return {
                        "allowed": False,
                        "reason": (
                            f"Max position per pair exceeded for {instrument_token} "
                            f"(₹{current_value:.2f} + ₹{trade_amount:.2f} > "
                            f"₹{config.UPSTOX_MAX_POSITION_PER_PAIR:.2f})"
                        ),
                    }
            elif trade_amount > config.UPSTOX_MAX_POSITION_PER_PAIR:
                return {
                    "allowed": False,
                    "reason": f"Trade ₹{trade_amount:.2f} exceeds max ₹{config.UPSTOX_MAX_POSITION_PER_PAIR:.2f}",
                }

            all_positions = db.query(Portfolio).filter(Portfolio.is_sandbox == is_sandbox).all()
            total_exposure = sum(abs(p.quantity) * p.current_price for p in all_positions)
            if total_exposure + trade_amount > config.UPSTOX_MAX_PORTFOLIO_EXPOSURE:
                return {
                    "allowed": False,
                    "reason": (
                        f"Portfolio exposure exceeded "
                        f"(₹{total_exposure:.2f} + ₹{trade_amount:.2f} > "
                        f"₹{config.UPSTOX_MAX_PORTFOLIO_EXPOSURE:.2f})"
                    ),
                }

            return {"allowed": True, "reason": "All risk checks passed"}

        except Exception as e:
            print(f"⚠️ Error checking risk limits: {e}")
            return {"allowed": True, "reason": "Risk check error – allowing trade"}
        finally:
            db.close()

    def _reset_daily_counter(self):
        """Reset daily trade counter if it's a new day."""
        today = datetime.now(timezone.utc).date()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
