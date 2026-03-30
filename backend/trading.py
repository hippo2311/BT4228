"""
MACD_BB_ATR Trading Strategy
Faithfully extracted from Group6_FinalTerm.ipynb
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ── Tickers & metadata ────────────────────────────────────────────────────────

TICKERS = ["AAPL", "AMZN", "META", "GOOG", "GOOGL", "NVDA", "MSFT", "AVGO", "TSLA", "BRK-B"]

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms",
    "GOOG": "Alphabet Inc. (C)",
    "GOOGL": "Alphabet Inc. (A)",
    "NVDA": "NVIDIA Corp.",
    "MSFT": "Microsoft Corp.",
    "AVGO": "Broadcom Inc.",
    "TSLA": "Tesla Inc.",
    "BRK-B": "Berkshire Hathaway",
}

SECTOR_MAP = {
    "AAPL": "Technology",
    "AVGO": "Technology",
    "NVDA": "Technology",
    "MSFT": "Technology",
    "META": "Communication",
    "GOOG": "Communication",
    "GOOGL": "Communication",
    "AMZN": "Consumer",
    "TSLA": "Consumer",
    "BRK-B": "Financial",
}

SECTOR_COLORS = {
    "Technology": "#58A6FF",
    "Communication": "#A371F7",
    "Consumer": "#3FB950",
    "Financial": "#D29922",
    "Healthcare": "#F85149",
}

# ── Pre-optimised parameters (within the notebook's Optuna search bounds) ────

DEFAULT_PARAMS = {
    "macd_fast":       12,
    "macd_slow":       38,
    "macd_signal":      7,
    "macd_std_window": 80,
    "macd_k":         1.5,
    "macd_k_mid":    0.75,
    "bb_window":       20,
    "bb_std_dev":     2.0,
    "atr_window":      14,
    "tp_mult_lm":     4.5,
    "sl_mult_lm":     1.5,
    "tp_mult_sm":     4.5,
    "sl_mult_sm":     1.5,
    "tp_mult_lr":    12.0,
    "sl_mult_lr":     3.0,
    "tp_mult_sr":     5.0,
    "sl_mult_sr":     2.0,
    "use_trailing":  True,
    "trail_mult":     2.5,
    "trail_tp":      True,
    "time_stop":       15,
    "cooldown":         2,
    "rebounce_block":   3,
    "rebalance_freq":  90,
}

INITIAL_CAPITAL = 1_000_000
DATA_START      = "2020-01-01"   # include warmup period
SIM_START       = "2021-01-01"   # signals counted from here
BENCHMARK       = "SPY"


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_data(tickers: list, start: str, end: str) -> dict:
    """Download OHLCV from yfinance; returns {ticker: DataFrame}."""
    data = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(start=start, end=end, interval="1d", auto_adjust=True)
            if df.empty:
                logger.warning(f"No data for {ticker}")
                continue
            df.columns = [c.lower() for c in df.columns]
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            data[ticker] = df
            logger.info(f"Fetched {ticker}: {len(df)} bars")
        except Exception as exc:
            logger.warning(f"Failed to fetch {ticker}: {exc}")
    return data


# ── Indicator computation ─────────────────────────────────────────────────────

def compute_indicators(price_data: dict, params: dict) -> dict:
    """Compute MACD histogram, Bollinger Bands (on log price), ATR, and robust scale."""
    from ta.trend import MACD
    from ta.volatility import BollingerBands, AverageTrueRange

    indicators = {}
    for ticker, df in price_data.items():
        close = df["close"]
        high  = df["high"]
        low   = df["low"]
        n     = len(close)

        # MACD histogram  h = MACD_line − Signal_line
        macd_obj = MACD(
            close=close,
            window_slow=params["macd_slow"],
            window_fast=params["macd_fast"],
            window_sign=params["macd_signal"],
            fillna=False,
        )
        h_series = macd_obj.macd_diff()

        # Bollinger Bands on log-price, mapped back to price space
        log_close = pd.Series(np.log(close.values), index=close.index)
        bb = BollingerBands(close=log_close, window=params["bb_window"],
                             window_dev=params["bb_std_dev"], fillna=False)
        upper = np.exp(bb.bollinger_hband().values)
        mid   = np.exp(bb.bollinger_mavg().values)
        lower = np.exp(bb.bollinger_lband().values)

        # ATR
        atr_series = AverageTrueRange(
            high=high, low=low, close=close,
            window=params["atr_window"], fillna=False
        ).average_true_range().values

        # Robust scale: RS(t) = 1.4826 × MAD of h over macd_std_window
        h_arr  = h_series.values
        win    = params["macd_std_window"]
        rs_arr = np.zeros(n)
        for t in range(win, n):
            seg = h_arr[t - win + 1: t + 1]
            seg = seg[~np.isnan(seg)]
            if len(seg) == 0:
                continue
            median = np.median(seg)
            mad    = np.median(np.abs(seg - median))
            rs_arr[t] = 1.4826 * mad

        indicators[ticker] = {
            "h":     h_arr,
            "rs":    rs_arr,
            "upper": upper,
            "mid":   mid,
            "lower": lower,
            "atr":   atr_series,
            "close": close.values,
            "high":  high.values,
            "low":   low.values,
        }
    return indicators


# ── Signal detail generator ───────────────────────────────────────────────────

def _signal_detail(ticker, leg, close, h, z_mid, z_pos, upper, mid, lower, atr, rs):
    if leg == "LM":
        bb_pct = (close - lower) / (upper - lower + 1e-9) * 100
        return (f"Long Momentum – MACD histogram {h:.4f} (0 to {z_mid:.4f} zone). "
                f"Price above mid-band at {bb_pct:.0f}% BB position. ATR {atr:.2f}.")
    if leg == "SM":
        bb_pct = (close - lower) / (upper - lower + 1e-9) * 100
        return (f"Short Momentum – MACD histogram {h:.4f} (-{z_mid:.4f} to 0 zone). "
                f"Price below mid-band at {bb_pct:.0f}% BB position. ATR {atr:.2f}.")
    if leg == "LR":
        return (f"Long Reversion – Extreme negative momentum (MACD {h:.4f} < -{z_pos:.4f}). "
                f"Price below lower Bollinger Band. Oversold; mean-reversion expected. ATR {atr:.2f}.")
    if leg == "SR":
        return (f"Short Reversion – Extreme positive momentum (MACD {h:.4f} > {z_pos:.4f}). "
                f"Price above upper Bollinger Band. Overbought; mean-reversion expected. ATR {atr:.2f}.")
    if leg == "SL":
        return "Stop-loss triggered after price reversal. Volatility spike invalidated entry thesis."
    if leg == "TP":
        return "Take-profit target reached. Position closed with realised gain."
    if leg == "TIME":
        return f"Time-based exit after {DEFAULT_PARAMS['time_stop']} bars."
    if leg == "REBALANCE":
        return "Position closed for scheduled portfolio rebalance."
    return ""


# ── Simulation helpers ────────────────────────────────────────────────────────

def _enter(ticker, direction, leg, close, atr, t_idx, date,
           equity, positions, signals_out, params, z_mid, z_pos, upper, mid, lower):
    shares = max(1, int(equity[ticker] / close))
    tp_key = f"tp_mult_{leg.lower()}"
    sl_key = f"sl_mult_{leg.lower()}"

    if direction == "LONG":
        tp = close + atr * params[tp_key]
        sl = close - atr * params[sl_key]
    else:
        tp = close - atr * params[tp_key]
        sl = close + atr * params[sl_key]

    positions[ticker] = {
        "direction":   direction,
        "leg":         leg,
        "entry_price": close,
        "entry_bar":   t_idx,
        "entry_date":  date,
        "shares":      shares,
        "tp":          tp,
        "sl":          sl,
        "run_max":     close,
        "run_min":     close,
        "equity_at_entry": equity[ticker],
    }

    # Signal strength: how far price is from mid-band normalised by ATR
    strength = min(0.99, abs(close - mid) / (atr * 2 + 1e-9))
    action = "LONG" if direction == "LONG" else "SHORT"
    signals_out.append({
        "date":        date.strftime("%Y-%m-%d"),
        "time":        date.strftime("%b %d"),
        "ticker":      ticker,
        "action":      action,
        "type":        leg,
        "strength":    round(strength, 2),
        "entry_price": round(close, 2),
        "tp":          round(tp, 2),
        "sl":          round(sl, 2),
        "atr":         round(atr, 4),
        "detail":      _signal_detail(ticker, leg, close, close, z_mid, z_pos,
                                       upper, mid, lower, atr, 0),
    })


def _close(ticker, pos, exit_price, date, exit_type, equity, positions,
           trades_out, signals_out, params):
    if pos["direction"] == "LONG":
        pnl = (exit_price - pos["entry_price"]) * pos["shares"]
    else:
        pnl = (pos["entry_price"] - exit_price) * pos["shares"]

    equity[ticker] += pnl

    trades_out.append({
        "ticker":      ticker,
        "direction":   pos["direction"],
        "leg":         pos["leg"],
        "entry_price": round(pos["entry_price"], 2),
        "entry_date":  pos["entry_date"].strftime("%Y-%m-%d"),
        "exit_price":  round(exit_price, 2),
        "exit_date":   date.strftime("%Y-%m-%d"),
        "exit_type":   exit_type,
        "pnl":         round(pnl, 2),
        "pnl_pct":     round(pnl / (pos["entry_price"] * pos["shares"]) * 100, 2),
        "shares":      pos["shares"],
    })

    entry_cost = pos["entry_price"] * pos["shares"]
    signals_out.append({
        "date":        date.strftime("%Y-%m-%d"),
        "time":        date.strftime("%b %d"),
        "ticker":      ticker,
        "action":      "EXIT",
        "type":        exit_type,
        "strength":    None,
        "entry_price": round(pos["entry_price"], 2),
        "exit_price":  round(exit_price, 2),
        "pnl":         round(pnl, 2),
        "detail":      _signal_detail(ticker, exit_type, exit_price, 0, 0, 0,
                                       0, 0, 0, 0, 0),
    })
    del positions[ticker]


# ── Main simulation ───────────────────────────────────────────────────────────

def run_simulation(price_data: dict, indicators: dict, allocations: dict,
                   params: dict, initial_capital: float, sim_start: str):
    """Bar-by-bar strategy simulation. Returns comprehensive results dict."""

    tickers = list(price_data.keys())

    # Common date index (union of all ticker dates)
    all_dates = sorted(set().union(*[set(df.index) for df in price_data.values()]))
    sim_start_dt = pd.Timestamp(sim_start)

    # Per-ticker state
    equity    = {t: initial_capital * allocations.get(t, 1 / len(tickers)) for t in tickers}
    positions = {}
    cooldown  = {t: 0 for t in tickers}
    rebounce  = {t: {"dir": None, "count": 0} for t in tickers}
    lm_count  = {t: 0 for t in tickers}
    sm_count  = {t: 0 for t in tickers}

    trades_out  = []
    signals_out = []
    daily_vals  = []
    last_rebal  = -999

    # Minimum warmup bars needed per ticker
    warmup = (params["macd_slow"] + params["macd_signal"] +
              params["macd_std_window"] + 5)

    for t_idx, date in enumerate(all_dates):

        # ── Rebalance ──────────────────────────────────────────────────────────
        if date >= sim_start_dt and (t_idx - last_rebal) >= params["rebalance_freq"]:
            total_eq = sum(equity.values())
            for ticker in list(positions.keys()):
                if ticker in price_data and date in price_data[ticker].index:
                    bar = price_data[ticker].index.get_loc(date)
                    close_p = indicators[ticker]["close"][bar]
                    pos = positions[ticker]
                    _close(ticker, pos, close_p, date, "REBALANCE",
                           equity, positions, trades_out, signals_out, params)
            # Redistribute
            total_eq = sum(equity.values())
            for ticker in tickers:
                equity[ticker] = total_eq * allocations.get(ticker, 1 / len(tickers))
            last_rebal = t_idx

        # ── Per-ticker processing ──────────────────────────────────────────────
        total_value = 0.0
        for ticker in tickers:
            df = price_data.get(ticker)
            if df is None or date not in df.index:
                total_value += equity[ticker]
                continue

            bar = df.index.get_loc(date)
            if bar < warmup:
                total_value += equity[ticker]
                continue

            ind   = indicators[ticker]
            close = ind["close"][bar]
            high  = ind["high"][bar]
            low   = ind["low"][bar]
            h     = ind["h"][bar]
            rs    = ind["rs"][bar]
            upper = ind["upper"][bar]
            mid   = ind["mid"][bar]
            lower_b = ind["lower"][bar]
            atr   = ind["atr"][bar]

            # Skip bars where indicators haven't warmed up
            if any(np.isnan(v) for v in [h, rs, upper, mid, lower_b, atr]) or rs < 1e-9:
                total_value += equity[ticker]
                continue

            z_pos = params["macd_k"]     * rs
            z_mid = params["macd_k_mid"] * rs
            z_neg = -z_pos

            # ── Exits ─────────────────────────────────────────────────────────
            if ticker in positions:
                pos    = positions[ticker]
                exited = False

                if pos["direction"] == "LONG":
                    if params["use_trailing"]:
                        pos["run_max"] = max(pos["run_max"], high)
                        pos["sl"] = max(pos["sl"], pos["run_max"] - params["trail_mult"] * atr)
                        if params["trail_tp"]:
                            pos["tp"] = max(pos["tp"],
                                            pos["run_max"] - (params["trail_mult"] / 2) * atr)

                    if low <= pos["sl"]:
                        _close(ticker, pos, pos["sl"], date, "SL",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        rebounce[ticker] = {"dir": "LONG", "count": params["rebounce_block"]}
                        lm_count[ticker] = 0
                        exited = True
                    elif high >= pos["tp"]:
                        _close(ticker, pos, pos["tp"], date, "TP",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        rebounce[ticker] = {"dir": "LONG", "count": params["rebounce_block"]}
                        lm_count[ticker] = 0
                        exited = True
                    elif params["time_stop"] > 0 and (t_idx - pos["entry_bar"]) >= params["time_stop"]:
                        _close(ticker, pos, close, date, "TIME",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        lm_count[ticker] = 0
                        exited = True

                elif pos["direction"] == "SHORT":
                    if params["use_trailing"]:
                        pos["run_min"] = min(pos["run_min"], low)
                        pos["sl"] = min(pos["sl"], pos["run_min"] + params["trail_mult"] * atr)
                        if params["trail_tp"]:
                            pos["tp"] = min(pos["tp"],
                                            pos["run_min"] + (params["trail_mult"] / 2) * atr)

                    if high >= pos["sl"]:
                        _close(ticker, pos, pos["sl"], date, "SL",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        rebounce[ticker] = {"dir": "SHORT", "count": params["rebounce_block"]}
                        sm_count[ticker] = 0
                        exited = True
                    elif low <= pos["tp"]:
                        _close(ticker, pos, pos["tp"], date, "TP",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        rebounce[ticker] = {"dir": "SHORT", "count": params["rebounce_block"]}
                        sm_count[ticker] = 0
                        exited = True
                    elif params["time_stop"] > 0 and (t_idx - pos["entry_bar"]) >= params["time_stop"]:
                        _close(ticker, pos, close, date, "TIME",
                               equity, positions, trades_out, signals_out, params)
                        cooldown[ticker] = params["cooldown"]
                        sm_count[ticker] = 0
                        exited = True

            # ── Entries (only after sim_start) ────────────────────────────────
            if date >= sim_start_dt and ticker not in positions:
                if rebounce[ticker]["count"] > 0:
                    rebounce[ticker]["count"] -= 1
                else:
                    rebounce[ticker]["dir"] = None

                if cooldown[ticker] > 0:
                    cooldown[ticker] -= 1

                if cooldown[ticker] <= 0 and equity[ticker] > close * 0.5:
                    can_long  = rebounce[ticker]["dir"] != "LONG"
                    can_short = rebounce[ticker]["dir"] != "SHORT"

                    # Long Momentum
                    if can_long and 0 <= h <= z_mid and close > mid:
                        if lm_count[ticker] < 4:
                            _enter(ticker, "LONG", "LM", close, atr, t_idx, date,
                                   equity, positions, signals_out, params,
                                   z_mid, z_pos, upper, mid, lower_b)
                            lm_count[ticker] += 1

                    # Short Momentum
                    elif can_short and z_neg <= h < 0 and close < mid:
                        if sm_count[ticker] < 4:
                            _enter(ticker, "SHORT", "SM", close, atr, t_idx, date,
                                   equity, positions, signals_out, params,
                                   z_mid, z_pos, upper, mid, lower_b)
                            sm_count[ticker] += 1

                    # Long Reversion
                    elif can_long and h < z_neg and close < lower_b:
                        _enter(ticker, "LONG", "LR", close, atr, t_idx, date,
                               equity, positions, signals_out, params,
                               z_mid, z_pos, upper, mid, lower_b)
                        lm_count[ticker] = 0
                        sm_count[ticker] = 0

                    # Short Reversion
                    elif can_short and h > z_pos and close > upper:
                        _enter(ticker, "SHORT", "SR", close, atr, t_idx, date,
                               equity, positions, signals_out, params,
                               z_mid, z_pos, upper, mid, lower_b)
                        lm_count[ticker] = 0
                        sm_count[ticker] = 0

            # ── Current stock value ───────────────────────────────────────────
            if ticker in positions:
                pos = positions[ticker]
                if pos["direction"] == "LONG":
                    unreal = (close - pos["entry_price"]) * pos["shares"]
                else:
                    unreal = (pos["entry_price"] - close) * pos["shares"]
                stock_val = max(0.0, equity[ticker] + unreal)
            else:
                stock_val = equity[ticker]

            total_value += stock_val

        if date >= sim_start_dt:
            daily_vals.append({"date": date, "portfolio": round(total_value, 2)})

    return {
        "daily_values":    daily_vals,
        "trades":          trades_out,
        "signals":         signals_out,
        "final_positions": dict(positions),
        "final_equity":    dict(equity),
    }


# ── Full strategy runner ──────────────────────────────────────────────────────

def run_full_strategy(params: dict | None = None) -> dict:
    """
    Fetch data, compute indicators, run simulation with equal weights,
    then return everything the API layer needs.
    """
    if params is None:
        params = DEFAULT_PARAMS

    end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info("Fetching price data…")
    price_data = fetch_data(TICKERS, DATA_START, end_date)
    if not price_data:
        raise RuntimeError("No price data returned from yfinance")

    # Benchmark
    bench_data = fetch_data([BENCHMARK], DATA_START, end_date)
    bench_df   = bench_data.get(BENCHMARK)

    logger.info("Computing indicators…")
    indicators = compute_indicators(price_data, params)

    available_tickers = list(price_data.keys())
    equal_alloc = {t: 1 / len(available_tickers) for t in available_tickers}

    logger.info("Running simulation…")
    sim = run_simulation(price_data, indicators, equal_alloc, params,
                         INITIAL_CAPITAL, SIM_START)

    # Attach benchmark to daily_values
    if bench_df is not None:
        bench_series = bench_df["close"]
        bench_start  = bench_series[bench_series.index >= pd.Timestamp(SIM_START)]
        if len(bench_start) > 0:
            bench_init = bench_start.iloc[0]
            for row in sim["daily_values"]:
                d = row["date"]
                if d in bench_series.index:
                    row["benchmark"] = round(
                        bench_series[d] / bench_init * INITIAL_CAPITAL, 2
                    )
                else:
                    row["benchmark"] = None

    # Per-stock equity series for portfolio optimizer
    stock_equity_series = {}
    for ticker in available_tickers:
        df = price_data[ticker]
        sim_dates = [row["date"] for row in sim["daily_values"]]
        eq_series = []
        cur_equity = INITIAL_CAPITAL * equal_alloc[ticker]
        for row_d in sim_dates:
            d = pd.Timestamp(row_d)
            if d in df.index:
                bar = df.index.get_loc(d)
                close = indicators[ticker]["close"][bar]
                # find any position that was open at this bar
                # (simplified: just track equity over time)
            eq_series.append(cur_equity)
        stock_equity_series[ticker] = eq_series

    # Compute per-stock returns from price data (for optimizer)
    stock_returns = {}
    sim_start_ts = pd.Timestamp(SIM_START)
    for ticker, df in price_data.items():
        df_sim = df[df.index >= sim_start_ts]["close"]
        if len(df_sim) > 1:
            stock_returns[ticker] = df_sim.pct_change().dropna()

    # Current prices + 1-day change
    current_prices = {}
    for ticker, df in price_data.items():
        if len(df) >= 2:
            current_prices[ticker] = {
                "price":  round(df["close"].iloc[-1], 2),
                "change": round((df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100, 2),
            }

    # Current ATR per ticker
    current_atr = {}
    for ticker, ind in indicators.items():
        atr_arr = ind["atr"]
        valid = atr_arr[~np.isnan(atr_arr)]
        current_atr[ticker] = round(float(valid[-1]), 4) if len(valid) else 0.0

    return {
        "daily_values":     sim["daily_values"],
        "trades":           sim["trades"],
        "signals":          sim["signals"],
        "final_positions":  sim["final_positions"],
        "final_equity":     sim["final_equity"],
        "stock_returns":    stock_returns,
        "current_prices":   current_prices,
        "current_atr":      current_atr,
        "price_data":       price_data,        # kept for downstream calcs
        "bench_df":         bench_df,
        "initial_capital":  INITIAL_CAPITAL,
        "params":           params,
        "tickers":          available_tickers,
    }
