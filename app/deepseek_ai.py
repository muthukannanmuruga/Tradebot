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
        # Optional instruction markdown
        self.instruction_path = getattr(config, "DEEPSEEK_INSTRUCTION_PATH", "")
        self.instruction_text = self._load_md_instruction(self.instruction_path) if self.instruction_path else None
    
    async def get_trading_decision(
        self,
        symbol: str,
        indicators: Dict,
        current_position: Optional[str] = None,
        intraday_signal: Optional[Dict] = None,
        portfolio_snapshot: Optional[Dict] = None,
        recent_trades: Optional[list] = None
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
            recent_trades=recent_trades
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
                                "content": self.instruction_text or self._get_system_prompt()
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
                    "decision": decision["action"],
                    "confidence": decision["confidence"],
                    "reasoning": decision["reasoning"],
                    "raw_response": ai_response
                }
        
        except Exception as e:
            print(f"Error getting AI decision: {e}")
            # Return safe default
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Error occurred: {str(e)}",
                "raw_response": ""
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI"""
        # Calculate dynamic values from config
        sl_pct = config.STOP_LOSS_PERCENT
        tp_pct = config.TAKE_PROFIT_PERCENT
        rr_ratio = int(tp_pct / sl_pct) if sl_pct > 0 else 2
        max_pos_per_pair = config.MAX_POSITION_PER_PAIR
        max_open_pos = config.MAX_OPEN_POSITIONS
        max_portfolio = config.MAX_PORTFOLIO_EXPOSURE
        
        return f"""You are an expert cryptocurrency scalping AI. Your PRIMARY GOAL is to MAXIMIZE PROFIT while PROTECTING CAPITAL at all costs.

🎯 STRATEGY: Scalping (Quick entries and exits)
⚖️ RISK:REWARD: 1:{rr_ratio} ({sl_pct}% stop / {tp_pct}% profit target)

JSON Response Format:
{{
    "action": "BUY" or "SELL" or "HOLD",
    "confidence": 0.0 to 1.0,
    "reasoning": "Your intelligent analysis"
}}

💰 RISK MANAGEMENT CONSTRAINTS (MUST RESPECT):
- Per Pair Limit: ${max_pos_per_pair} USDT maximum
- Max Open Positions: {max_open_pos} concurrent trades
- Total Portfolio Exposure: ${max_portfolio} USDT maximum
- Stop Loss: {sl_pct}% from entry
- Take Profit: {tp_pct}% from entry

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

Your reasoning should reflect your analysis of the provided indicators and explain why you believe the action will maximize profit or protect capital. Be decisive but prudent.
"""

    def _load_md_instruction(self, path: str) -> Optional[str]:
        """Load a markdown instruction file to use as the system prompt. Returns None if not found or empty."""
        try:
            if not path:
                return None
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                return text if text else None
        except Exception as e:
            print(f"Warning: could not load DeepSeek instruction file '{path}': {e}")
            return None
    
    def _create_trading_prompt(
        self,
        symbol: str,
        indicators: Dict,
        current_position: Optional[str],
        intraday_signal: Optional[Dict] = None,
        portfolio_snapshot: Optional[Dict] = None,
        recent_trades: Optional[list] = None,
    ) -> str:
        """Create enriched prompt with multi-timeframe market data."""

        position_text = f"Current Position: {current_position}" if current_position else "Current Position: NONE"

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
                f"- Current Price: ${indicators['summary']['current_price']:.2f}",
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
                    f"  • EMA 12: ${ind.get('ema_12', 0):.2f}",
                    f"  • EMA 26: ${ind.get('ema_26', 0):.2f}",
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
                    f"  • Bollinger Upper: ${ind.get('bb_upper', 0):.2f}",
                    f"  • Bollinger Middle: ${ind.get('bb_middle', 0):.2f}",
                    f"  • Bollinger Lower: ${ind.get('bb_lower', 0):.2f}",
                    f"  • ATR: {ind.get('atr', 0):.4f}",
                    f"  • Volume: {ind.get('volume', 0):.2f}",
                    "",
                ]
        else:
            # Single timeframe format (fallback)
            prompt_lines += [
                "CURRENT MARKET DATA:",
                f"- Price: ${indicators.get('current_price', 0):.2f}",
                "",
                "TREND INDICATORS:",
                f"- EMA short: ${indicators.get('ema_12', 0):.2f}",
                f"- EMA long: ${indicators.get('ema_26', 0):.2f}",
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
            prompt_lines += [
                "PORTFOLIO SNAPSHOT:",
                f"- USDT Balance: {portfolio_snapshot.get('usdt_balance', 0)}",
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
            "Be decisive when you see opportunity. Be cautious when unclear.",
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
            
            return {
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning
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
                "reasoning": ai_response
            }
