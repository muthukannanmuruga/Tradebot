import httpx
import json
from typing import Dict, Optional
from app.config import config


class DeepSeekAI:
    """DeepSeek AI integration for trading decisions"""
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        # Instruction markdown – default to docs/deepseek_instruction.md if not overridden
        self.instruction_path = getattr(config, "DEEPSEEK_INSTRUCTION_PATH", "") or "deepseek_instruction.md"
        self.instruction_text = self._load_md_instruction(self.instruction_path)
    
    async def get_trading_decision(
        self,
        symbol: str,
        indicators: Dict,
        current_position: Optional[str] = None,
        intraday_signal: Optional[Dict] = None,
        portfolio_snapshot: Optional[Dict] = None,
        recent_trades: Optional[list] = None,
        market: str = "upstox",  # 'upstox' or 'binance'
    ) -> Dict:
        """
        Get trading decision from DeepSeek AI
        
        Args:
            symbol: Trading symbol
            indicators: Dictionary of technical indicators
            current_position: Current position (LONG, SHORT, or None)
        
        Returns:
            Dictionary with decision and reasoning
        """
        prompt = self._create_trading_prompt(
            symbol,
            indicators,
            current_position,
            intraday_signal=intraday_signal,
            portfolio_snapshot=portfolio_snapshot,
            recent_trades=recent_trades,
            market=market,
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": self._build_system_prompt(market=market)
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Parse the AI response
                ai_response = result['choices'][0]['message']['content']
                decision = self._parse_decision(ai_response)

                return {
                    "decision": decision.get("action"),
                    "confidence": decision.get("confidence"),
                    "reasoning": decision.get("reasoning"),
                    "methodology": decision.get("methodology"),
                    "recommended_timeframe": decision.get("recommended_timeframe"),
                    "raw_response": ai_response
                }
        
        except Exception as e:
            print(f"Error getting AI decision: {e}")
            # Return safe default
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error occurred: {str(e)}",
                "methodology": None,
                "recommended_timeframe": None,
                "raw_response": ""
            }
    
    def _get_system_prompt(self, market: str = "upstox") -> str:
        """Get the system prompt for the AI"""
        sl_pct = config.STOP_LOSS_PERCENT
        tp_pct = config.TAKE_PROFIT_PERCENT
        rr_ratio = int(tp_pct / sl_pct) if sl_pct > 0 else 2

        if market == "upstox":
            max_pos_per_pair = config.UPSTOX_MAX_POSITION_PER_PAIR
            max_open_pos     = config.UPSTOX_MAX_OPEN_POSITIONS
            max_portfolio    = config.UPSTOX_MAX_PORTFOLIO_EXPOSURE
            currency         = "₹"
            market_label     = "Indian stock (NSE/BSE) intraday scalping"
            trade_amount     = config.UPSTOX_TRADING_AMOUNT
            risk_block = (
                f"💰 RISK MANAGEMENT CONSTRAINTS (MUST RESPECT):\n"
                f"- Per Pair Limit: {currency}{max_pos_per_pair} INR maximum\n"
                f"- Max Open Positions: {max_open_pos} concurrent trades\n"
                f"- Total Portfolio Exposure: {currency}{max_portfolio} INR maximum\n"
                f"- Trade Amount per signal: {currency}{trade_amount} INR\n"
                f"- Stop Loss: {sl_pct}% from entry\n"
                f"- Take Profit: {tp_pct}% from entry\n"
                f"- Product: Intraday (positions auto-squared at 3:30 PM IST)\n"
                f"- BUY = go LONG, SELL = go SHORT (intraday short allowed)"
            )
        else:
            max_pos_per_pair = config.MAX_POSITION_PER_PAIR
            max_open_pos     = config.BINANCE_MAX_OPEN_POSITIONS
            max_portfolio    = config.MAX_PORTFOLIO_EXPOSURE
            currency         = "$"
            market_label     = "cryptocurrency scalping"
            risk_block = (
                f"💰 RISK MANAGEMENT CONSTRAINTS (MUST RESPECT):\n"
                f"- Per Pair Limit: {currency}{max_pos_per_pair} USDT maximum\n"
                f"- Max Open Positions: {max_open_pos} concurrent trades\n"
                f"- Total Portfolio Exposure: {currency}{max_portfolio} USDT maximum\n"
                f"- Stop Loss: {sl_pct}% from entry\n"
                f"- Take Profit: {tp_pct}% from entry"
            )

        return f"""You are an expert {market_label} AI. Your PRIMARY GOAL is to MAXIMIZE PROFIT while PROTECTING CAPITAL at all costs.

🎯 STRATEGY: Scalping (Quick entries and exits)
⚖️ RISK:REWARD: 1:{rr_ratio} ({sl_pct}% stop / {tp_pct}% profit target)

JSON Response Format:
{{
    "action": "BUY" or "SELL" or "HOLD",
    "confidence": 0.0 to 1.0,
    "reasoning": "Your intelligent analysis",
    "methodology": "SCALP" | "SWING" | "TREND" | "INTRADAY" | "OTHER",
    "recommended_timeframe": "5m" | "15m" | "1h" | "4h" | "1d"
}}

{risk_block}

🧠 YOUR INTELLIGENCE:
You will receive multi-timeframe technical indicators (5m, 1h, 4h, 1d), portfolio data, and recent trades.

Use your expertise to:
1. Identify high-probability scalping opportunities
2. Detect when momentum is shifting against positions
3. Recognize structure breaks, resistance levels, divergences
4. Balance aggression (profit seeking) with capital protection
5. Consider market context from multiple timeframes

🎯 DECISION FRAMEWORK:
- **BUY**: Clear bullish setup with defined risk/reward
- **SELL**: Exit signal (profit target, momentum fade, structure break, resistance)
- **HOLD**: Unclear setup or position still valid

⚡ KEY PRINCIPLES:
✅ Capital preservation is paramount
✅ Quick exits on momentum shifts or structure breaks
✅ Take profits before resistance, not into it
✅ Higher timeframe context matters (don't fight 4h/1d trends)
✅ Volume confirms moves - low volume rallies are suspect
✅ Divergences (price vs indicators) signal reversals

❌ AVOID:
❌ Holding losing trades hoping for recovery
❌ Ignoring clear exit signals
❌ Trading into strong resistance
❌ Fighting higher timeframe trends
❌ Low confidence trades (use confidence scoring honestly)

    Your reasoning should reflect your analysis of the provided indicators and explain why you believe the action will maximize profit or protect capital. Be decisive: when multiple indicators across timeframes align, favor taking action (BUY or SELL) rather than defaulting to HOLD. Avoid paralysis by analysis — do not overthink or miss high-probability opportunities.
"""

    def _load_md_instruction(self, path: str) -> Optional[str]:
        """Load a markdown instruction file. Returns None if not found or empty."""
        try:
            if not path:
                return None
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                return text if text else None
        except Exception as e:
            print(f"Warning: could not load DeepSeek instruction file '{path}': {e}")
            return None

    def _build_system_prompt(self, market: str = "upstox") -> str:
        """Compose the final system prompt: built-in prompt + appended MD instructions (if any).

        The built-in prompt from ``_get_system_prompt()`` is always used as the base.
        If ``docs/deepseek_instruction.md`` (or the path from DEEPSEEK_INSTRUCTION_PATH)
        exists and contains content, it is appended after the base prompt so users can
        add custom rules/context without losing the core trading logic.
        """
        base = self._get_system_prompt(market=market)
        if self.instruction_text:
            return (
                base
                + "\n\n"
                + "─" * 70
                + "\n📋 ADDITIONAL INSTRUCTIONS (from deepseek_instruction.md):\n"
                + "─" * 70
                + "\n"
                + self.instruction_text
            )
        return base

    def _create_trading_prompt(
        self,
        symbol: str,
        indicators: Dict,
        current_position: Optional[str],
        intraday_signal: Optional[Dict] = None,
        portfolio_snapshot: Optional[Dict] = None,
        recent_trades: Optional[list] = None,
        market: str = "upstox",
    ) -> str:
        """Create enriched prompt with multi-timeframe market data."""

        position_text = f"Current Position: {current_position}" if current_position else "Current Position: NONE"

        # Currency symbol for prompt
        curr = "₹" if market == "upstox" else "$"

        # Check if this is multi-timeframe data
        is_multi_tf = "5min" in indicators and "1hour" in indicators
        
        prompt_lines = [
            f"Analyze the following MULTI-TIMEFRAME market data for {symbol} and provide a trading decision:",
            "",
            position_text,
            "",
        ]
        
        if is_multi_tf:
            # Multi-timeframe format
            alignment = indicators["summary"]["timeframe_alignment"]
            prompt_lines += [
                "="*70,
                "TIMEFRAME ALIGNMENT OVERVIEW:",
                f"- Overall Alignment: {alignment['alignment']}",
                f"- MACD Bullish Timeframes: {alignment['macd_bullish_count']}/4",
                f"- RSI Suitable Timeframes: {alignment['rsi_bullish_count']}/4",
                f"- EMA Bullish Timeframes: {alignment['ema_bullish_count']}/4",
                f"- Higher TF MACD Bias: {'BULLISH' if alignment['higher_tf_macd_bullish'] else 'BEARISH' if alignment['higher_tf_macd_bearish'] else 'MIXED'}",
                f"- Higher TF RSI Status: {'OVERBOUGHT' if alignment['higher_tf_rsi_overbought'] else 'OVERSOLD' if alignment['higher_tf_rsi_oversold'] else 'NEUTRAL'}",
                f"- MACD Crossover on 4h/1d: {'YES' if alignment['has_higher_tf_macd_crossover'] else 'No'}",
                f"- Current Price: {curr}{indicators['summary']['current_price']:.2f}",
                "="*70,
                "",
            ]
            
            # Add each timeframe's indicators
            for tf_key, tf_name in [("5min", "5-MINUTE"), ("1hour", "1-HOUR"), ("4hour", "4-HOUR"), ("1day", "1-DAY")]:
                ind = indicators[tf_key]
                prompt_lines += [
                    f"{'─'*70}",
                    f"{tf_name} TIMEFRAME:",
                    f"{'─'*70}",
                    "",
                    "TREND INDICATORS:",
                    f"  • EMA 12: {curr}{ind.get('ema_12', 0):.2f}",
                    f"  • EMA 26: {curr}{ind.get('ema_26', 0):.2f}",
                    f"  • EMA Trend: {ind.get('ema_trend')} ({'Price above EMA12' if ind.get('current_price', 0) > ind.get('ema_12', 0) else 'Price below EMA12'})",
                    "",
                    "MACD ANALYSIS:",
                    f"  • MACD Line: {ind.get('macd', 0):.4f}",
                    f"  • Signal Line: {ind.get('macd_signal', 0):.4f}",
                    f"  • Histogram: {ind.get('macd_histogram', 0):.4f}",
                    f"  • Trend: {ind.get('macd_trend')}",
                    f"  • Crossover: {ind.get('macd_crossover')}",
                    "",
                    "MOMENTUM:",
                    f"  • RSI: {ind.get('rsi', 0):.2f} ({ind.get('rsi_zone')})",
                    "",
                    "VOLATILITY:",
                    f"  • Bollinger Upper: {curr}{ind.get('bb_upper', 0):.2f}",
                    f"  • Bollinger Middle: {curr}{ind.get('bb_middle', 0):.2f}",
                    f"  • Bollinger Lower: {curr}{ind.get('bb_lower', 0):.2f}",
                    f"  • ATR: {ind.get('atr', 0):.4f}",
                    f"  • Volume: {ind.get('volume', 0):.2f}",
                    "",
                ]
        else:
            # Single timeframe format (fallback)
            prompt_lines += [
                "CURRENT MARKET DATA:",
                f"- Price: {curr}{indicators.get('current_price', 0):.2f}",
                "",
                "TREND INDICATORS:",
                f"- EMA short: {curr}{indicators.get('ema_12', 0):.2f}",
                f"- EMA long: {curr}{indicators.get('ema_26', 0):.2f}",
                f"- EMA Trend: {indicators.get('ema_trend')}",
                "",
                "MACD ANALYSIS:",
                f"- MACD Line: {indicators.get('macd', 0):.2f}",
                f"- Signal Line: {indicators.get('macd_signal', 0):.2f}",
                f"- Histogram: {indicators.get('macd_histogram', 0):.2f}",
                f"- Crossover: {indicators.get('macd_crossover')}",
                "",
                "MOMENTUM INDICATORS:",
                f"- RSI: {indicators.get('rsi', 0):.2f}",
                f"- RSI Zone: {indicators.get('rsi_zone')}",
                "",
            ]

        # Add intraday signal block if provided
        if intraday_signal:
            prompt_lines += [
                "INTRADAY SIGNAL (auxiliary):",
                f"- Signal: {intraday_signal.get('signal')}",
                f"- Confidence: {intraday_signal.get('confidence')}",
                f"- Reasoning: {intraday_signal.get('reasoning')}",
                "",
            ]

        # Add portfolio snapshot if provided
        if portfolio_snapshot:
            if market == "upstox":
                balance_label = "Available Balance (INR)"
                balance_value = portfolio_snapshot.get('available_balance', 0)
            else:
                balance_label = "USDT Balance"
                balance_value = portfolio_snapshot.get('usdt_balance', 0)
            prompt_lines += [
                "PORTFOLIO SNAPSHOT:",
                f"- {balance_label}: {balance_value}",
                f"- Open Positions: {len(portfolio_snapshot.get('positions', []))}",
                "",
            ]

        # Recent trades summary (most recent 3)
        if recent_trades:
            prompt_lines += [
                "="*70,
                "RECENT TRADES HISTORY:",
            ]
            for t in recent_trades[:3]:
                prompt_lines.append(f"  • {t}")
            prompt_lines.append("")

        prompt_lines += [
            "="*70,
            "",
            "📊 ANALYZE THE ABOVE DATA AND MAKE YOUR INTELLIGENT DECISION:",
            "",
            "Consider:",
            "• Multi-timeframe trend alignment",
            "• Momentum strength and direction",
            "• Entry/exit timing for scalping",
            "• Risk/reward for this specific setup",
            "• Current position status and portfolio exposure",
            "",
            "Your goal: Maximize profit while protecting capital.",
            "Be decisive when you see opportunity. If multiple indicators across timeframes align (strong setup), prefer action and assign a confidence >= 0.6. Avoid overthinking — do not default to HOLD when evidence supports a trade.",
            "Explain your reasoning with the data provided."
        ]

        return "\n".join(prompt_lines)
    
    def _parse_decision(self, ai_response: str) -> Dict:
        """Parse the AI response to extract decision"""
        try:
            # Try to parse as JSON
            # Remove any markdown code blocks
            response = ai_response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            decision = json.loads(response)
            
            # Validate and normalize
            action = decision.get("action", "HOLD").upper()
            if action not in ["BUY", "SELL", "HOLD"]:
                action = "HOLD"
            
            confidence = float(decision.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            
            reasoning = decision.get("reasoning", "No reasoning provided")
            # optional fields
            methodology = decision.get("methodology")
            # accept either 'recommended_timeframe' or 'timeframe'
            timeframe = decision.get("recommended_timeframe") or decision.get("timeframe")
            
            return {
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning,
                "methodology": methodology,
                "recommended_timeframe": timeframe
            }
        
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails
            response_upper = ai_response.upper()
            
            if "BUY" in response_upper:
                action = "BUY"
            elif "SELL" in response_upper:
                action = "SELL"
            else:
                action = "HOLD"
            
            return {
                "action": action,
                "confidence": 0.5,
                "reasoning": ai_response,
                "methodology": None,
                "recommended_timeframe": None
            }

    # ────────────────────────────────────────────────────────────────────
    # Market Sentiment / News Analysis
    # ────────────────────────────────────────────────────────────────────

    async def get_market_sentiment(self, market: str = "indian_stocks") -> Dict:
        """Ask DeepSeek to analyse recent market sentiment, news & geopolitical
        events and return actionable trade ideas.

        Args:
            market: 'crypto' or 'indian_stocks'

        Returns:
            Dict with sentiment, analysis, and suggested tickers.
        """
        if market == "crypto":
            system_prompt = (
                "You are a world-class cryptocurrency market analyst. "
                "Analyse the latest crypto news, macro events, regulatory developments, "
                "on-chain metrics signals, and geopolitical factors that could move the "
                "crypto market in the next 1-7 days. "
                "Suggest up to 10 specific crypto tokens/coins that look attractive right now "
                "along with a brief reason for each.\n\n"
                "Return JSON:\n"
                "{\n"
                '  "overall_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",\n'
                '  "confidence": 0.0-1.0,\n'
                '  "analysis": "your detailed reasoning",\n'
                '  "key_events": ["event1", "event2", ...],\n'
                '  "suggested_trades": [\n'
                '    {"symbol": "BTC", "direction": "LONG"|"SHORT", "reason": "..."},\n'
                "    ...\n"
                "  ]\n"
                "}"
            )
            user_prompt = (
                "Provide your latest sentiment analysis for the cryptocurrency market. "
                "Cover Bitcoin, Ethereum, major altcoins and any trending tokens. "
                "Include macro factors (Fed policy, DXY, US equities correlation) and "
                "any upcoming events (ETF decisions, unlocks, halvings, upgrades). "
                "Give me 5-10 actionable trade ideas with direction and reasoning."
            )
        else:
            system_prompt = (
                "You are a world-class Indian equity & derivatives market analyst. "
                "Analyse the latest Indian stock market news, RBI policy outlook, "
                "FII/DII flows, sector rotation, global cues, crude oil impact, INR trends, "
                "and geopolitical developments (India-specific and global) that could move "
                "NSE/BSE in the next 1-7 days. "
                "Suggest up to 10 specific NSE-listed stocks or indices that look attractive "
                "for intraday or short-term swing trades, along with a brief reason for each.\n\n"
                "IMPORTANT: For each stock, provide the ISIN code (12-character alphanumeric, starts with INE).\n"
                "Common examples: RELIANCE = INE002A01018, TCS = INE467B01029, INFY = INE009A01021, "
                "HDFCBANK = INE040A01034, ICICIBANK = INE090A01021, SBIN = INE062A01020, ITC = INE154A01025\n\n"
                "Return JSON:\n"
                "{\n"
                '  "overall_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",\n'
                '  "confidence": 0.0-1.0,\n'
                '  "analysis": "your detailed reasoning",\n'
                '  "key_events": ["event1", "event2", ...],\n'
                '  "suggested_trades": [\n'
                '    {"symbol": "RELIANCE", "isin": "INE002A01018", "direction": "LONG"|"SHORT", "reason": "..."},\n'
                "    ...\n"
                "  ]\n"
                "}"
            )
            user_prompt = (
                "Provide your latest sentiment analysis for the Indian stock market (NSE/BSE). "
                "Cover Nifty 50, Bank Nifty, and sector-specific trends. "
                "Include macro factors (RBI rate decision, inflation, FII flows, crude oil, INR). "
                "Mention any upcoming events (earnings, policy announcements, global cues). "
                "Give me 5-10 actionable trade ideas for NSE stocks with ISIN codes, direction and reasoning."
            )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.4,
                        "max_tokens": 1500,
                    },
                )
                response.raise_for_status()
                result = response.json()
                raw = result["choices"][0]["message"]["content"]

                # Try to parse as JSON
                cleaned = raw.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
                elif cleaned.startswith("```"):
                    cleaned = cleaned.replace("```", "").strip()

                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError:
                    parsed = {
                        "overall_sentiment": "UNKNOWN",
                        "confidence": 0.0,
                        "analysis": raw,
                        "key_events": [],
                        "suggested_trades": [],
                    }

                parsed["market"] = market
                parsed["raw_response"] = raw
                return parsed

        except Exception as e:
            print(f"Error getting market sentiment ({market}): {e}")
            return {
                "market": market,
                "overall_sentiment": "ERROR",
                "confidence": 0.0,
                "analysis": f"Failed to fetch sentiment: {str(e)}",
                "key_events": [],
                "suggested_trades": [],
                "raw_response": "",
            }
