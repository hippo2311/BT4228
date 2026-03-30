"""
AI-Assisted Explanations using OpenAI GPT.
API key loaded from OPENAI_API in project .env file.
Falls back to template responses if the key is not available.
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"   # fast + cheap; swap to "gpt-4o" for higher quality

# ── Load .env ─────────────────────────────────────────────────────────────────

def _load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    val = val.strip().strip("'\"")
                    os.environ.setdefault(key.strip(), val)

_load_env()


# ── Client ────────────────────────────────────────────────────────────────────

def _client():
    api_key = os.getenv("OPENAI_API", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as exc:
        logger.warning(f"Could not initialise OpenAI client: {exc}")
        return None


def _call(messages: list, max_tokens: int = 600) -> str | None:
    client = _client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning(f"OpenAI API call failed: {exc}")
        return None


# ── Trade Explainer ───────────────────────────────────────────────────────────

def explain_trade(signal: dict) -> dict:
    action = signal.get("action", "")
    ticker = signal.get("ticker", "")
    leg    = signal.get("type", "")
    entry  = signal.get("entry_price") or signal.get("exit_price", 0)
    tp     = signal.get("tp")
    sl     = signal.get("sl")
    atr    = signal.get("atr", 0)
    detail = signal.get("detail", "")

    strategy_names = {
        "LM": "Long Momentum (LM)",
        "SM": "Short Momentum (SM)",
        "LR": "Long Reversion (LR)",
        "SR": "Short Reversion (SR)",
        "SL": "Stop-Loss (SL)",
        "TP": "Take-Profit (TP)",
        "TIME": "Time-Stop Exit",
        "REBALANCE": "Portfolio Rebalance",
    }
    strategy_name = strategy_names.get(leg, leg)

    system = (
        "You are an expert quantitative trading analyst for a MACD + Bollinger Bands + ATR "
        "strategy on large-cap US equities. Be concise, technical, and data-driven."
    )
    user = f"""Explain this trading signal in structured JSON.

Signal:
- Action: {action} {ticker}
- Strategy: {strategy_name}
- Entry/Exit Price: ${entry}
- Take Profit: ${tp}
- Stop Loss: ${sl}
- ATR: {atr}
- Technical detail: {detail}

Return ONLY valid JSON (no markdown) with these exact keys:
{{
  "why": ["reason 1", "reason 2", "reason 3"],
  "risk": "one paragraph about risk/reward",
  "confidence_note": "one sentence about signal confidence"
}}

Use the actual numbers. Be specific."""

    raw = _call([{"role": "system", "content": system},
                 {"role": "user",   "content": user}], max_tokens=500)

    if raw:
        import json, re
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
                return {
                    "action":    action,
                    "ticker":    ticker,
                    "time":      signal.get("time", signal.get("date", "")),
                    "strategy":  strategy_name,
                    "why":       parsed.get("why", [detail]),
                    "risk":      parsed.get("risk", ""),
                    "confidence": signal.get("strength"),
                }
        except Exception:
            pass

    # Fallback templates
    if action == "LONG":
        why = [
            "MACD histogram entered the momentum zone (0 to mid threshold), confirming bullish impulse.",
            f"Price (${entry}) is above the Bollinger mid-band, supporting the upward trend.",
            f"ATR ({atr}) is within normal range – breakout occurring in stable volatility.",
        ]
        rr = round(abs((tp - entry) / (entry - sl)), 1) if tp and sl and entry != sl else "N/A"
        risk = f"Stop-loss at ${sl}, take-profit at ${tp}. Risk-reward ratio 1:{rr}."
    elif action == "SHORT":
        why = [
            f"MACD histogram in extreme zone beyond the reversion threshold.",
            f"Price (${entry}) is {'above upper' if leg == 'SR' else 'below lower'} Bollinger Band.",
            f"Mean-reversion conditions detected. ATR ({atr}) confirms the setup.",
        ]
        risk = f"Stop-loss at ${sl}, take-profit at ${tp}. Short position with bounded downside."
    else:
        why = [
            f"{'Stop-loss' if leg == 'SL' else 'Take-profit' if leg == 'TP' else 'Time-stop'} triggered.",
            f"Exit at ${entry}.",
            "Position closed to protect capital / lock in gains.",
        ]
        risk = "Position fully closed. No remaining exposure."

    return {
        "action":     action,
        "ticker":     ticker,
        "time":       signal.get("time", signal.get("date", "")),
        "strategy":   strategy_name,
        "why":        why,
        "risk":       risk,
        "confidence": signal.get("strength"),
    }


# ── Market Summary ────────────────────────────────────────────────────────────

def market_summary(metrics: dict, positions: dict, tickers: list) -> str:
    n_long  = sum(1 for p in positions.values() if p.get("direction") == "LONG")
    n_short = sum(1 for p in positions.values() if p.get("direction") == "SHORT")

    system = "You are a quantitative portfolio manager writing a daily market briefing."
    user = f"""Summarise the current state of this algorithmic trading portfolio in 3 short paragraphs.

Portfolio Statistics:
- Total Return: {metrics.get('totalReturn', 0):.1f}%
- CAGR: {metrics.get('cagr', 0):.1f}%
- Sharpe Ratio: {metrics.get('sharpe', 0):.2f}
- Max Drawdown: {metrics.get('maxDrawdown', 0):.1f}%
- Current Drawdown: {metrics.get('currentDrawdown', 0):.1f}%
- Annualised Volatility: {metrics.get('volatility', 0):.1f}%
- Win Rate: {metrics.get('winRate', 0):.1f}%
- Active Positions: {n_long} long, {n_short} short
- Universe: {', '.join(tickers)}

Paragraph 1: Market regime and portfolio positioning.
Paragraph 2: Performance highlights and risk assessment.
Paragraph 3: Outlook and key risks to monitor.

Be concise and data-driven."""

    result = _call([{"role": "system", "content": system},
                    {"role": "user",   "content": user}], max_tokens=400)
    if result:
        return result

    regime = "trending bullish" if metrics.get("rollingSharpe", 0) > 1.0 else "mixed"
    return (
        f"The portfolio is operating in a {regime} market regime with {n_long} long "
        f"and {n_short} short positions across {len(tickers)} large-cap US equities.\n\n"
        f"Total Return: {metrics.get('totalReturn', 0):.1f}% | Sharpe: {metrics.get('sharpe', 0):.2f} | "
        f"Max Drawdown: {abs(metrics.get('maxDrawdown', 0)):.1f}% | "
        f"Volatility: {metrics.get('volatility', 0):.1f}%.\n\n"
        f"Key risks: drawdown at {abs(metrics.get('currentDrawdown', 0)):.1f}%, "
        f"potential volatility spikes during earnings, and correlation breakdown between strategy legs."
    )


# ── Risk Alerts ───────────────────────────────────────────────────────────────

def generate_alerts(metrics: dict, positions: dict, trades: list,
                    current_atr: dict) -> list[dict]:
    from datetime import datetime
    now    = datetime.now().strftime("%I:%M %p")
    alerts = []

    cur_dd = abs(metrics.get("currentDrawdown", 0))
    if cur_dd > 3.0:
        sev = "critical" if cur_dd > 5 else "warning"
        alerts.append({
            "severity": sev, "time": now, "title": "DRAWDOWN WARNING",
            "message":  (f"Portfolio drawdown reached -{cur_dd:.1f}% from peak. "
                         f"Max historical: {abs(metrics.get('maxDrawdown', 0)):.1f}%."),
            "recommendation": "Consider reducing position sizes if drawdown exceeds 7%." if sev == "critical" else None,
        })

    win_rate = metrics.get("winRate", 0)
    if win_rate > 60:
        alerts.append({
            "severity": "info", "time": now, "title": "STRONG WIN RATE",
            "message":  f"Strategy win rate at {win_rate:.1f}% – above the 60% threshold. Both momentum and reversion legs performing within expected parameters.",
            "recommendation": None,
        })

    if not positions:
        alerts.append({
            "severity": "info", "time": now, "title": "NO ACTIVE POSITIONS",
            "message":  "No open positions. Strategy is in cash, awaiting entry signals.",
            "recommendation": None,
        })

    alerts.append({
        "severity": "info", "time": now, "title": "STRATEGY STATUS",
        "message":  (f"MACD-BB-ATR regime-adaptive strategy active. "
                     f"Total Return: {metrics.get('totalReturn', 0):.1f}% | "
                     f"Sharpe: {metrics.get('sharpe', 0):.2f} | "
                     f"Drawdown: {metrics.get('currentDrawdown', 0):.1f}%."),
        "recommendation": None,
    })

    return alerts[:4]


# ── Chat ──────────────────────────────────────────────────────────────────────

def chat_response(message: str, history: list,
                  context: Optional[dict] = None) -> str:
    system = (
        "You are an AI trading assistant for a quantitative trading system using a "
        "MACD + Bollinger Bands + ATR strategy on large-cap US equities "
        "(AAPL, AMZN, META, GOOG, GOOGL, NVDA, MSFT, AVGO, TSLA, BRK-B). "
        "Four strategy legs: Long Momentum (LM), Short Momentum (SM), "
        "Long Reversion (LR), Short Reversion (SR). "
        "Portfolio optimised via Modern Portfolio Theory (Ledoit-Wolf + tangent portfolio). "
        "Be concise, data-driven, and helpful."
    )
    if context and context.get("metrics"):
        m = context["metrics"]
        system += (f"\n\nCurrent metrics — Return: {m.get('totalReturn',0):.1f}%, "
                   f"Sharpe: {m.get('sharpe',0):.2f}, "
                   f"Drawdown: {m.get('currentDrawdown',0):.1f}%.")

    messages = [{"role": "system", "content": system}]
    for h in history[-8:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    result = _call(messages, max_tokens=600)
    if result:
        return result

    # Fallback
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["macd", "indicator", "signal"]):
        return ("The strategy uses MACD histogram thresholds scaled by robust MAD. "
                "Moderate zones trigger momentum trades (LM/SM); extreme zones trigger reversion (LR/SR). "
                "Bollinger Bands on log-price confirm signal direction.")
    if any(w in msg_lower for w in ["portfolio", "allocation", "weight"]):
        return ("Allocation uses Modern Portfolio Theory: Ledoit-Wolf shrinkage covariance "
                "+ max-Sharpe tangent portfolio (long-only). Rebalances every 90 days.")
    if any(w in msg_lower for w in ["risk", "drawdown", "stop"]):
        return ("Risk managed via ATR-scaled stop-losses and take-profits. "
                "Trailing stops tighten as positions move in favour. "
                "A time-stop closes positions after 15 bars if neither TP nor SL is hit.")
    return ("I can help with trading signals, portfolio allocation, risk management, "
            "or performance metrics. What would you like to know?")
