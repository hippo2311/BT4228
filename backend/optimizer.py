"""
Modern Portfolio Theory optimizer
Replicates ModernPortfolioOptimizerPro from the notebook using
Ledoit-Wolf shrinkage + analytical tangent portfolio + scipy frontier.
"""

import numpy as np
import pandas as pd
import logging
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

try:
    from sklearn.covariance import LedoitWolf
    _HAS_LW = True
except ImportError:
    _HAS_LW = False
    logger.warning("scikit-learn not available; falling back to sample covariance")


# ── Portfolio math ────────────────────────────────────────────────────────────

def _ledoit_wolf_cov(returns_df: pd.DataFrame) -> np.ndarray:
    """Ledoit-Wolf shrinkage covariance (annualised)."""
    if _HAS_LW:
        lw = LedoitWolf()
        lw.fit(returns_df.dropna())
        return lw.covariance_ * 252
    return returns_df.cov().values * 252


def tangent_portfolio(mu: np.ndarray, cov: np.ndarray,
                      risk_free: float = 0.04,
                      ridge_alpha: float = 1e-5) -> np.ndarray:
    """Analytical max-Sharpe (long-only) weights."""
    n = len(mu)
    trace = np.trace(cov)
    cov_reg = cov + ridge_alpha * (trace / n) * np.eye(n)

    excess = mu - risk_free
    cov_inv = np.linalg.pinv(cov_reg)
    z = cov_inv @ excess
    z = np.maximum(z, 0)          # long-only

    if z.sum() < 1e-10:
        return np.ones(n) / n     # equal-weight fallback
    return z / z.sum()


def efficient_frontier(mu: np.ndarray, cov: np.ndarray,
                       n_points: int = 30,
                       risk_free: float = 0.04) -> list[dict]:
    """Efficient frontier via scipy SLSQP."""
    n = len(mu)
    ret_min = mu.min()
    ret_max = mu.max() * 0.95
    targets = np.linspace(ret_min, ret_max, n_points)

    def portfolio_var(w):
        return w @ cov @ w

    frontier = []
    w0 = np.ones(n) / n
    for r_target in targets:
        constraints = [
            {"type": "eq", "fun": lambda w: w.sum() - 1},
            {"type": "eq", "fun": lambda w, r=r_target: w @ mu - r},
        ]
        bounds = [(0, 1)] * n
        res = minimize(portfolio_var, w0, method="SLSQP",
                       bounds=bounds, constraints=constraints,
                       options={"ftol": 1e-9, "disp": False, "maxiter": 200})
        if res.success:
            vol = np.sqrt(res.fun) * 100
            ret = r_target * 100
            sharpe = (r_target - risk_free) / np.sqrt(res.fun) if res.fun > 0 else 0
            frontier.append({"volatility": round(vol, 2),
                              "return":     round(ret, 2),
                              "sharpe":     round(sharpe, 3)})
    return frontier


# ── Risk contribution ─────────────────────────────────────────────────────────

def marginal_risk_contribution(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Percentage contribution of each asset to total portfolio variance."""
    port_var = w @ cov @ w
    if port_var < 1e-12:
        return np.ones(len(w)) / len(w) * 100
    mrc = (cov @ w) * w / port_var
    return (mrc / mrc.sum() * 100).round(1)


# ── Public entry point ────────────────────────────────────────────────────────

def optimize_portfolio(stock_returns: dict[str, pd.Series],
                       risk_free: float = 0.04) -> dict:
    """
    Parameters
    ----------
    stock_returns : {ticker: daily_returns_Series}

    Returns
    -------
    dict with allocations, frontier, portfolio metrics, individual metrics
    """
    # Align returns into a DataFrame
    df = pd.DataFrame(stock_returns).dropna(how="all")
    # Drop near-zero variance columns
    df = df[[c for c in df.columns if df[c].std() > 1e-8]]
    df = df.dropna()

    if df.empty or len(df) < 30:
        logger.warning("Not enough return data for optimization; using equal weights")
        tickers_out = list(stock_returns.keys())
        n = len(tickers_out)
        w = {t: round(1 / n, 4) for t in tickers_out}
        return {"allocations": w, "frontier": [], "portfolio_metrics": {},
                "individual_metrics": {}}

    tickers = list(df.columns)
    n = len(tickers)

    mu  = df.mean().values * 252          # annualised mean returns
    cov = _ledoit_wolf_cov(df)            # annualised cov

    # Tangent portfolio
    w_opt = tangent_portfolio(mu, cov, risk_free=risk_free)

    # Round and normalise to sum to 100 %
    rounded = np.round(w_opt, 4)
    rounded = rounded / rounded.sum()

    allocations = {t: round(float(rounded[i]), 4) for i, t in enumerate(tickers)}

    # Efficient frontier
    try:
        frontier = efficient_frontier(mu, cov, n_points=30, risk_free=risk_free)
    except Exception as exc:
        logger.warning(f"Efficient frontier failed: {exc}")
        frontier = []

    # Portfolio-level metrics (annualised)
    p_ret = float(w_opt @ mu)
    p_vol = float(np.sqrt(w_opt @ cov @ w_opt))
    p_sharpe = (p_ret - risk_free) / p_vol if p_vol > 0 else 0

    # Risk contribution
    mrc = marginal_risk_contribution(w_opt, cov)
    risk_contrib = [{"ticker": t, "risk": round(float(mrc[i]), 1)}
                    for i, t in enumerate(tickers)]

    # Individual stock metrics
    individual = {}
    for i, t in enumerate(tickers):
        individual[t] = {
            "return":     round(float(mu[i]) * 100, 2),
            "volatility": round(float(np.sqrt(cov[i, i])) * 100, 2),
        }

    # Correlation of each stock to optimised portfolio
    port_ret_series = df @ w_opt
    corr_to_port = {}
    for t in tickers:
        r = np.corrcoef(df[t].values, port_ret_series.values)[0, 1]
        corr_to_port[t] = round(float(r), 3)

    return {
        "allocations":      allocations,
        "frontier":         frontier,
        "risk_contribution": risk_contrib,
        "portfolio_metrics": {
            "return":     round(p_ret * 100, 2),
            "volatility": round(p_vol * 100, 2),
            "sharpe":     round(p_sharpe, 3),
        },
        "individual_metrics": individual,
        "corr_to_port":    corr_to_port,
    }
