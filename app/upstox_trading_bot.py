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
        # Track position per instrument: {"NSE_EQ|INE...": None or "LONG"}
        self.positions: Dict[str, Optional[str]] = {}
        self.last_check = None
        self.trade_count = 0
        self.daily_trades = 0
        self.last_trade_date = None
        # Upstox trading pairs from config
        self.trading_pairs = config.UPSTOX_TRADING_PAIRS
        self.product_type = config.UPSTOX_PRODUCT_TYPE  # I, D, MTF

        # Initialize positions and sync from DB
        self._sync_positions_from_db()

    def _sync_positions_from_db(self):
        """Sync position state from database on initialization."""
        db = SessionLocal()
        try:
            for pair in self.trading_pairs:
                portfolio_entry = (
                    db.query(Portfolio).filter(Portfolio.pair == pair).first()
                )
                if portfolio_entry:
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
        """Get or create BotMetrics record."""
        metrics = db.query(BotMetrics).first()
        if not metrics:
            metrics = BotMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit_loss=0.0,
                win_rate=0.0,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(metrics)
            db.commit()
            print("📊 Initialized BotMetrics table")
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

        self.is_running = True
        print("🚀 Upstox Trading bot started!")
        print(f"📊 Trading instruments: {', '.join(self.trading_pairs)}")
        print(f"📦 Product type: {self.product_type}")
        print(f"⏰ Check interval: {config.CHECK_INTERVAL_SECONDS}s")

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
        print("🛑 Upstox Trading bot stopped!")

    # ── Core trading loop ──────────────────────────────────────────────

    async def trading_loop(self):
        """Main trading loop – processes all Upstox trading instruments."""
        try:
            self._reset_daily_counter()

            if self.daily_trades >= config.MAX_DAILY_TRADES:
                print(f"⚠️ Daily trade limit reached ({config.MAX_DAILY_TRADES})")
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
                    .filter(Trade.pair == instrument_token)
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

            # Execute
            await self._execute_decision(instrument_token, ai_decision, mtf_analysis)

        except Exception as e:
            print(f"❌ Error processing Upstox {instrument_token}: {e}")
            import traceback
            traceback.print_exc()

    async def _execute_decision(
        self, instrument_token: str, ai_decision: Dict, analysis: Dict
    ):
        """Execute trading decision for an Upstox instrument."""
        action = ai_decision["decision"]
        confidence = ai_decision["confidence"]
        current_position = self.positions.get(instrument_token)

        if action == "BUY" and current_position != "LONG":
            # Risk check
            risk_check = await self._check_risk_limits(
                instrument_token, config.UPSTOX_TRADING_AMOUNT
            )
            if not risk_check["allowed"]:
                print(f"🚫 Trade blocked by risk management: {risk_check['reason']}")
                return

            quantity = await self.upstox.get_quantity_from_quote(
                instrument_token, config.UPSTOX_TRADING_AMOUNT
            )
            indicators_5m = analysis["indicators"]["5min"]
            await self.execute_trade(
                instrument_token,
                "BUY",
                quantity,
                ai_decision["reasoning"],
                confidence,
                indicators_5m,
            )
            self.positions[instrument_token] = "LONG"

        elif action == "SELL" and current_position == "LONG":
            db = SessionLocal()
            try:
                portfolio_entry = (
                    db.query(Portfolio)
                    .filter(Portfolio.pair == instrument_token)
                    .first()
                )
                if portfolio_entry:
                    quantity = int(portfolio_entry.quantity)
                    print(f"💼 Selling {quantity} {instrument_token} from portfolio")
                else:
                    print(
                        f"⚠️ No portfolio entry for {instrument_token}, skipping SELL"
                    )
                    return
            finally:
                db.close()

            indicators_5m = analysis["indicators"]["5min"]
            await self.execute_trade(
                instrument_token,
                "SELL",
                quantity,
                ai_decision["reasoning"],
                confidence,
                indicators_5m,
            )
            self.positions[instrument_token] = None

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
        """Execute an Upstox trade and log to database."""
        try:
            order = await self.upstox.place_market_order(
                instrument_token, side, quantity, product=self.product_type
            )

            # get_current_price() returns 0.0 cleanly in sandbox (no exception raised)
            current_price = await self.upstox.get_current_price(instrument_token)

            executed_qty = int(order.get("quantity", quantity))

            # Log to DB
            db = SessionLocal()
            try:
                trade = Trade(
                    pair=instrument_token,
                    side=side,
                    quantity=executed_qty,
                    entry_price=current_price if side == "BUY" else 0,
                    exit_price=current_price if side == "SELL" else None,
                    status="OPEN" if side == "BUY" else "CLOSED",
                    order_id=str(order.get("orderId", "")),
                    ai_reasoning=reasoning,
                    confidence=confidence or 0.0,
                )
                db.add(trade)
                db.commit()

                if side == "BUY":
                    self.positions[instrument_token] = "LONG"
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(Portfolio.pair == instrument_token)
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
                            quantity=executed_qty,
                            entry_price=current_price,
                            current_price=current_price,
                            total_invested=current_price * executed_qty,
                            current_value=current_price * executed_qty,
                            unrealized_pl=0.0,
                            updated_at=datetime.now(timezone.utc),
                        )
                        db.add(portfolio_entry)
                    db.commit()
                    print(f"💼 Portfolio updated: {instrument_token} position opened")

                elif side == "SELL":
                    self.positions[instrument_token] = None
                    portfolio_entry = (
                        db.query(Portfolio)
                        .filter(Portfolio.pair == instrument_token)
                        .first()
                    )
                    realized_pl = 0.0
                    if portfolio_entry:
                        realized_pl = (
                            (current_price - portfolio_entry.entry_price)
                            * portfolio_entry.quantity
                        )
                        trade.profit_loss = realized_pl
                        trade.profit_loss_percent = (
                            (realized_pl / (portfolio_entry.entry_price * portfolio_entry.quantity))
                            * 100
                        )
                        trade.entry_price = portfolio_entry.entry_price
                        db.delete(portfolio_entry)
                        db.commit()
                        print(
                            f"💼 Portfolio: {instrument_token} closed (P&L: ₹{realized_pl:.2f})"
                        )

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

                self.trade_count += 1
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
                "max_daily_trades": config.MAX_DAILY_TRADES,
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
                portfolio_entries = db.query(Portfolio).all()
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
        """Check if trade passes risk management limits."""
        db = SessionLocal()
        try:
            open_positions = db.query(Portfolio).count()
            if open_positions >= config.MAX_OPEN_POSITIONS:
                return {
                    "allowed": False,
                    "reason": f"Max open positions reached ({open_positions}/{config.MAX_OPEN_POSITIONS})",
                }

            pair_position = (
                db.query(Portfolio).filter(Portfolio.pair == instrument_token).first()
            )
            if pair_position:
                current_value = pair_position.quantity * pair_position.current_price
                if current_value + trade_amount > config.MAX_POSITION_PER_PAIR:
                    return {
                        "allowed": False,
                        "reason": (
                            f"Max position per pair exceeded for {instrument_token} "
                            f"(₹{current_value:.2f} + ₹{trade_amount:.2f} > "
                            f"₹{config.MAX_POSITION_PER_PAIR:.2f})"
                        ),
                    }
            elif trade_amount > config.MAX_POSITION_PER_PAIR:
                return {
                    "allowed": False,
                    "reason": f"Trade ₹{trade_amount:.2f} exceeds max ₹{config.MAX_POSITION_PER_PAIR:.2f}",
                }

            all_positions = db.query(Portfolio).all()
            total_exposure = sum(p.quantity * p.current_price for p in all_positions)
            if total_exposure + trade_amount > config.MAX_PORTFOLIO_EXPOSURE:
                return {
                    "allowed": False,
                    "reason": (
                        f"Portfolio exposure exceeded "
                        f"(₹{total_exposure:.2f} + ₹{trade_amount:.2f} > "
                        f"₹{config.MAX_PORTFOLIO_EXPOSURE:.2f})"
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
