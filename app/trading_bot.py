import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import json

from app.binance_client import BinanceClient
from binance.client import Client
from app.deepseek_ai import DeepSeekAI
from app.indicators import TechnicalIndicators
from app.database import SessionLocal, Trade, Portfolio, BotMetrics
from app.config import config


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        self.binance = BinanceClient()
        self.ai = DeepSeekAI()
        self.is_running = False
        # Track position per symbol: {"BTCUSDT": None, "ETHUSDT": "LONG", ...}
        self.positions = {}
        self.last_check = None
        self.trade_count = 0
        self.daily_trades = 0
        self.last_trade_date = None
        # Multiple trading pairs from config
        self.trading_pairs = config.TRADING_PAIRS
        
        # Initialize positions for each pair and sync with database
        self._sync_positions_from_db()
    
    def _sync_positions_from_db(self):
        """Sync position state from database on initialization"""
        db = SessionLocal()
        try:
            for pair in self.trading_pairs:
                # Check Portfolio table for open positions
                portfolio_entry = db.query(Portfolio).filter(Portfolio.pair == pair).first()
                
                if portfolio_entry:
                    self.positions[pair] = "LONG"
                    print(f"📍 Restored position: {pair} = LONG (Qty: {portfolio_entry.quantity} @ ${portfolio_entry.entry_price:.2f})")
                else:
                    self.positions[pair] = None
            
            # Initialize BotMetrics if not exists
            self._get_or_create_metrics(db)
        finally:
            db.close()
    
    def _get_or_create_metrics(self, db):
        """Get or create BotMetrics record"""
        metrics = db.query(BotMetrics).first()
        if not metrics:
            metrics = BotMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit_loss=0.0,
                win_rate=0.0,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(metrics)
            db.commit()
            print("📊 Initialized BotMetrics table")
        return metrics
    
    async def start(self):
        """Start the trading bot"""
        self.is_running = True
        print("🚀 Trading bot started!")
        print(f"📊 Trading pairs: {', '.join(self.trading_pairs)}")
        print(f"⏰ Check interval: {config.CHECK_INTERVAL_SECONDS}s")
        
        while self.is_running:
            try:
                await self.trading_loop()
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)
            except Exception as e:
                print(f"❌ Error in trading loop: {e}")
                await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)
    
    async def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        print("🛑 Trading bot stopped!")
    
    async def trading_loop(self):
        """Main trading loop logic - processes all trading pairs"""
        try:
            # Reset daily trade counter if new day
            self._reset_daily_counter()
            
            # Check if we've exceeded daily trade limit
            if self.daily_trades >= config.MAX_DAILY_TRADES:
                print(f"⚠️ Daily trade limit reached ({config.MAX_DAILY_TRADES})")
                return
            
            # Process each trading pair
            for trading_pair in self.trading_pairs:
                await self._process_trading_pair(trading_pair)
            
            self.last_check = datetime.now(timezone.utc)
        
        except Exception as e:
            print(f"❌ Error in trading loop: {e}")
            import traceback
            traceback.print_exc()
    
    async def _process_trading_pair(self, trading_pair: str):
        """Process a single trading pair with multi-timeframe analysis"""
        try:
            # Get multi-timeframe analysis
            mtf_analysis = await self.get_multi_timeframe_analysis(trading_pair)
            
            # Get portfolio snapshot (for AI context)
            try:
                portfolio_snapshot = await self.get_portfolio()
            except Exception:
                portfolio_snapshot = None

            # Get recent trades (last 3) for context
            recent_trades = []
            db = SessionLocal()
            try:
                rows = db.query(Trade).filter(Trade.pair == trading_pair).order_by(Trade.created_at.desc()).limit(3).all()
                for r in rows:
                    recent_trades.append(f"{r.side} {r.quantity} {r.pair} @ {getattr(r, 'entry_price', getattr(r, 'price', 'N/A'))} on {r.created_at}")
            except Exception:
                recent_trades = []
            finally:
                db.close()

            # Get current position for this pair
            current_position = self.positions.get(trading_pair)

            # Get AI decision with ALL timeframe indicators
            ai_decision = await self.ai.get_trading_decision(
                trading_pair,
                mtf_analysis["indicators"],  # Pass all timeframe indicators
                current_position,
                intraday_signal=None,
                portfolio_snapshot=portfolio_snapshot,
                recent_trades=recent_trades
            )
            
            # Display analysis
            alignment = mtf_analysis["indicators"]["summary"]["timeframe_alignment"]
            print(f"\n{'='*60}")
            print(f"📊 {trading_pair} - Multi-Timeframe Analysis")
            print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"💰 Price: ${mtf_analysis['indicators']['summary']['current_price']:.2f}")
            print(f"\n🔄 Timeframe Alignment: {alignment['alignment']}")
            print(f"   • MACD Bullish: {alignment['macd_bullish_count']}/4 timeframes")
            print(f"   • RSI Suitable: {alignment['rsi_bullish_count']}/4 timeframes")
            print(f"   • EMA Bullish: {alignment['ema_bullish_count']}/4 timeframes")
            print(f"   • Higher TF MACD: {'BULLISH' if alignment['higher_tf_macd_bullish'] else 'BEARISH' if alignment['higher_tf_macd_bearish'] else 'MIXED'}")
            if alignment.get('has_higher_tf_macd_crossover'):
                print(f"   • Higher TF MACD Crossover Detected")
            
            # Show key indicators from each timeframe
            for tf, name in [("5min", "5m"), ("1hour", "1h"), ("4hour", "4h"), ("1day", "1d")]:
                ind = mtf_analysis["indicators"][tf]
                print(f"   {name:4s}: EMA {ind['ema_trend']:8s} | MACD {ind['macd_trend']:8s} | RSI {ind['rsi']:5.1f} ({ind['rsi_zone']})")
            
            print(f"\n🎯 Position: {current_position or 'None'}")
            print(f"🤖 AI Decision: {ai_decision['decision']} (Confidence: {ai_decision['confidence']:.2%})")
            print(f"💭 Reasoning: {ai_decision['reasoning'][:200]}..." if len(ai_decision['reasoning']) > 200 else f"💭 Reasoning: {ai_decision['reasoning']}")
            print(f"{'='*60}\n")
            
            # Execute trade based on AI decision
            await self._execute_decision(trading_pair, ai_decision, mtf_analysis)
        
        except Exception as e:
            print(f"❌ Error processing {trading_pair}: {e}")
            import traceback
            traceback.print_exc()
    
    async def _execute_decision(self, trading_pair: str, ai_decision: Dict, analysis: Dict):
        """Execute trading decision for a specific pair"""
        action = ai_decision["decision"]
        confidence = ai_decision["confidence"]
        current_position = self.positions.get(trading_pair)

        # Execute BUY
        if action == "BUY" and current_position != "LONG":
            # Risk Management Checks before opening new position
            risk_check = await self._check_risk_limits(trading_pair, config.TRADING_AMOUNT_QUOTE)
            if not risk_check["allowed"]:
                print(f"🚫 Trade blocked by risk management: {risk_check['reason']}")
                return
            quantity = await self.binance.get_quantity_from_quote(
                trading_pair,
                config.TRADING_AMOUNT_QUOTE
            )
            # Use 5min indicators for entry price
            indicators_5m = analysis["indicators"]["5min"]
            await self.execute_trade(
                trading_pair,
                "BUY",
                quantity,
                ai_decision["reasoning"],
                confidence,
                indicators_5m
            )
            self.positions[trading_pair] = "LONG"
        
        # Execute SELL (close long)
        elif action == "SELL" and current_position == "LONG":
            # Get actual quantity from portfolio
            db = SessionLocal()
            try:
                portfolio_entry = db.query(Portfolio).filter(Portfolio.pair == trading_pair).first()
                if portfolio_entry:
                    quantity = float(portfolio_entry.quantity)
                    print(f"💼 Selling {quantity} {trading_pair} from portfolio")
                else:
                    print(f"⚠️ No portfolio entry found for {trading_pair}, skipping SELL")
                    return
            finally:
                db.close()
            
            # Use 5min indicators for exit price
            indicators_5m = analysis["indicators"]["5min"]
            await self.execute_trade(
                trading_pair,
                "SELL",
                quantity,
                ai_decision["reasoning"],
                confidence,
                indicators_5m
            )
            self.positions[trading_pair] = None
        
        
        # If none of the above, hold
        else:
            print(f"✋ Holding position (Current: {current_position})")
    
    async def execute_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reasoning: str,
        confidence: float = None,
        indicators: Dict = None
    ):
        """Execute a trade"""
        try:
            # Place market order (spot)
            order = await self.binance.place_market_order(symbol, side, quantity)
            
            # Get current price
            current_price = float(order.get('price') or order.get('fills', [{}])[0].get('price', 0))
            if current_price == 0:
                current_price = await self.binance.get_current_price(symbol)
            
            executed_qty = float(order['executedQty'])
            
            # Log trade to database
            db = SessionLocal()
            try:
                trade = Trade(
                    pair=symbol,
                    side=side,
                    quantity=executed_qty,
                    entry_price=current_price if side == "BUY" else 0,
                    exit_price=current_price if side == "SELL" else None,
                    status="OPEN" if side == "BUY" else "CLOSED",
                    order_id=str(order['orderId']),
                    ai_reasoning=reasoning,
                    confidence=confidence or 0.0
                )
                db.add(trade)
                db.commit()
                
                # Update position tracking
                if side == "BUY":
                    self.positions[symbol] = "LONG"
                    # Create or update portfolio entry
                    portfolio_entry = db.query(Portfolio).filter(Portfolio.pair == symbol).first()
                    if portfolio_entry:
                        # Update existing position (average price if adding to position)
                        old_value = portfolio_entry.quantity * portfolio_entry.entry_price
                        new_value = executed_qty * current_price
                        portfolio_entry.quantity += executed_qty
                        portfolio_entry.entry_price = (old_value + new_value) / portfolio_entry.quantity
                        portfolio_entry.current_price = current_price
                        portfolio_entry.unrealized_pl = (current_price - portfolio_entry.entry_price) * portfolio_entry.quantity
                        portfolio_entry.updated_at = datetime.now(timezone.utc)
                    else:
                        # Create new position
                        portfolio_entry = Portfolio(
                            pair=symbol,
                            quantity=executed_qty,
                            entry_price=current_price,
                            current_price=current_price,
                            unrealized_pl=0.0,
                            updated_at=datetime.now(timezone.utc)
                        )
                        db.add(portfolio_entry)
                    db.commit()
                    print(f"💼 Portfolio updated: {symbol} position opened/increased")
                    
                elif side == "SELL":
                    self.positions[symbol] = None
                    # Remove portfolio entry when position is closed
                    portfolio_entry = db.query(Portfolio).filter(Portfolio.pair == symbol).first()
                    realized_pl = 0.0
                    if portfolio_entry:
                        # Calculate realized P&L before removing
                        realized_pl = (current_price - portfolio_entry.entry_price) * portfolio_entry.quantity
                        
                        # Update trade record with profit/loss
                        trade.profit_loss = realized_pl
                        trade.profit_loss_percent = (realized_pl / (portfolio_entry.entry_price * portfolio_entry.quantity)) * 100
                        trade.entry_price = portfolio_entry.entry_price  # Set entry price from portfolio
                        
                        db.delete(portfolio_entry)
                        db.commit()
                        print(f"💼 Portfolio updated: {symbol} position closed (P&L: ${realized_pl:.2f})")
                        
                        # Update BotMetrics
                        metrics = self._get_or_create_metrics(db)
                        metrics.total_trades += 1
                        metrics.total_profit_loss += realized_pl
                        
                        if realized_pl > 0:
                            metrics.winning_trades += 1
                        elif realized_pl < 0:
                            metrics.losing_trades += 1
                        
                        # Calculate win rate
                        total_completed = metrics.winning_trades + metrics.losing_trades
                        metrics.win_rate = (metrics.winning_trades / total_completed * 100) if total_completed > 0 else 0.0
                        metrics.last_trade_time = datetime.now(timezone.utc)
                        metrics.updated_at = datetime.now(timezone.utc)
                        
                        db.commit()
                        print(f"📊 BotMetrics updated: Win Rate: {metrics.win_rate:.1f}%, Total P&L: ${metrics.total_profit_loss:.2f}")
                
                self.trade_count += 1
                self.daily_trades += 1
                
                print(f"✅ Trade executed: {side} {executed_qty} {symbol} @ ${current_price:.2f}")
                print(f"📝 Order ID: {order['orderId']}")
                
            finally:
                db.close()
            
            return order
        
        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
            raise
    
    async def get_multi_timeframe_analysis(self, symbol: str) -> Dict:
        """Get multi-timeframe market analysis for all timeframes"""
        try:
            # Fetch data for all timeframes
            print(f"📥 Fetching multi-timeframe data for {symbol}...")
            df_5m = await self.binance.get_historical_klines(
                symbol, 
                interval=Client.KLINE_INTERVAL_5MINUTE, 
                limit=200
            )
            df_1h = await self.binance.get_historical_klines(
                symbol, 
                interval=Client.KLINE_INTERVAL_1HOUR, 
                limit=200
            )
            df_4h = await self.binance.get_historical_klines(
                symbol, 
                interval=Client.KLINE_INTERVAL_4HOUR, 
                limit=100
            )
            df_1d = await self.binance.get_historical_klines(
                symbol, 
                interval=Client.KLINE_INTERVAL_1DAY, 
                limit=100
            )
            
            # Calculate indicators for all timeframes
            multi_tf_indicators = TechnicalIndicators.calculate_multi_timeframe_indicators(
                df_5m, df_1h, df_4h, df_1d
            )
            
            return {
                "symbol": symbol,
                "indicators": multi_tf_indicators,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            print(f"❌ Error getting multi-timeframe analysis: {e}")
            raise
    
    async def get_market_analysis(self, symbol: str) -> Dict:
        """Get comprehensive market analysis"""
        try:
            # Get historical data (explicit 1-hour interval for intraday hourly signals)
            df = await self.binance.get_historical_klines(symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=200)
            
            # Calculate all indicators
            indicators = TechnicalIndicators.calculate_all_indicators(df)
            
            # Convert numpy types to Python native types for JSON serialization
            indicators_serializable = {}
            for key, value in indicators.items():
                if hasattr(value, 'item'):  # numpy scalar
                    indicators_serializable[key] = value.item()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    indicators_serializable[key] = value
                else:
                    indicators_serializable[key] = str(value)
            
            # Get 24h ticker
            ticker = await self.binance.get_24hr_ticker(symbol)
            
            return {
                "symbol": symbol,
                "indicators": indicators_serializable,
                "ticker_24h": ticker,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ohlcv": df  # Include DataFrame for intraday signal generation
            }
        
        except Exception as e:
            print(f"❌ Error getting market analysis: {e}")
            raise
    
    async def get_status(self) -> Dict:
        """Get bot status"""
        db = SessionLocal()
        try:
            total_trades = db.query(Trade).count()
            
            status = {
                "is_running": self.is_running,
                "last_check": self.last_check,
                "total_trades": total_trades,
                "positions": self.positions,  # Dict of all positions by pair
                "trading_pairs": config.TRADING_PAIRS,
                "daily_trades": self.daily_trades,
                "max_daily_trades": config.MAX_DAILY_TRADES,
                "risk_limits": {
                    "max_position_per_pair": config.MAX_POSITION_PER_PAIR,
                    "max_open_positions": config.MAX_OPEN_POSITIONS,
                    "max_portfolio_exposure": config.MAX_PORTFOLIO_EXPOSURE
                }
            }
            
            # Add current prices for all trading pairs
            if self.is_running:
                prices = {}
                for pair in config.TRADING_PAIRS:
                    try:
                        prices[pair] = await self.binance.get_current_price(pair)
                    except Exception as e:
                        prices[pair] = f"Error: {e}"
                status["current_prices"] = prices
            
            return status
        
        finally:
            db.close()
    
    async def _check_risk_limits(self, trading_pair: str, trade_amount: float) -> Dict:
        """Check if trade passes risk management limits"""
        db = SessionLocal()
        try:
            # 1. Check Max Open Positions
            open_positions = db.query(Portfolio).count()
            if open_positions >= config.MAX_OPEN_POSITIONS:
                return {
                    "allowed": False,
                    "reason": f"Max open positions reached ({open_positions}/{config.MAX_OPEN_POSITIONS})"
                }
            
            # 2. Check Max Position Per Pair
            pair_position = db.query(Portfolio).filter(Portfolio.pair == trading_pair).first()
            if pair_position:
                current_pair_value = pair_position.quantity * pair_position.current_price
                if current_pair_value + trade_amount > config.MAX_POSITION_PER_PAIR:
                    return {
                        "allowed": False,
                        "reason": f"Max position per pair exceeded for {trading_pair} (${current_pair_value:.2f} + ${trade_amount:.2f} > ${config.MAX_POSITION_PER_PAIR:.2f})"
                    }
            elif trade_amount > config.MAX_POSITION_PER_PAIR:
                return {
                    "allowed": False,
                    "reason": f"Trade amount ${trade_amount:.2f} exceeds max per pair ${config.MAX_POSITION_PER_PAIR:.2f}"
                }
            
            # 3. Check Max Portfolio Exposure
            all_positions = db.query(Portfolio).all()
            total_exposure = sum(p.quantity * p.current_price for p in all_positions)
            if total_exposure + trade_amount > config.MAX_PORTFOLIO_EXPOSURE:
                return {
                    "allowed": False,
                    "reason": f"Max portfolio exposure exceeded (${total_exposure:.2f} + ${trade_amount:.2f} > ${config.MAX_PORTFOLIO_EXPOSURE:.2f})"
                }
            
            return {"allowed": True, "reason": "All risk checks passed"}
            
        except Exception as e:
            print(f"⚠️ Error checking risk limits: {e}")
            return {"allowed": True, "reason": "Risk check error - allowing trade"}
        finally:
            db.close()
    
    async def get_portfolio(self) -> Dict:
        """Get current portfolio using Portfolio table"""
        try:
            # Get account balance
            usdt_balance = await self.binance.get_account_balance("USDT")
            
            # Get portfolio entries and update current prices
            db = SessionLocal()
            try:
                portfolio_entries = db.query(Portfolio).all()
                
                total_invested = 0.0
                total_pnl = 0.0
                open_positions_count = len(portfolio_entries)
                
                # Convert to list of dicts while session is open
                positions_list = []
                
                # Update current prices and calculate P&L
                for entry in portfolio_entries:
                    try:
                        current_price = await self.binance.get_current_price(entry.pair)
                        entry.current_price = current_price
                        entry.unrealized_pl = (current_price - entry.entry_price) * entry.quantity
                        entry.updated_at = datetime.now(timezone.utc)
                        
                        total_invested += entry.entry_price * entry.quantity
                        total_pnl += entry.unrealized_pl
                        
                        # Store data as dict while session is open
                        positions_list.append({
                            "pair": entry.pair,
                            "quantity": entry.quantity,
                            "entry_price": entry.entry_price,
                            "current_price": entry.current_price,
                            "unrealized_pl": entry.unrealized_pl
                        })
                    except Exception as e:
                        print(f"⚠️ Could not update price for {entry.pair}: {e}")
                
                db.commit()
                
                # Calculate win rate from completed trades
                completed_trades = db.query(Trade).filter(Trade.side == "SELL").all()
                winning_trades = sum(1 for t in completed_trades if (getattr(t, 'profit_loss', None) or 0) > 0)
                win_rate = (winning_trades / len(completed_trades) * 100) if completed_trades else 0.0
                
            finally:
                db.close()
            
            # Calculate profit/loss percentage
            pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
            
            return {
                "total_balance": usdt_balance + total_invested + total_pnl,
                "available_balance": usdt_balance,
                "total_invested": total_invested,
                "open_positions": open_positions_count,
                "total_profit_loss": total_pnl,
                "profit_loss_percent": pnl_percent,
                "win_rate": win_rate,
                "positions": positions_list
            }
        
        except Exception as e:
            print(f"❌ Error getting portfolio: {e}")
            raise
    
    def _reset_daily_counter(self):
        """Reset daily trade counter if it's a new day"""
        today = datetime.now(timezone.utc).date()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today

