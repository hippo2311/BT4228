from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.optimizer import optimize_portfolio
from backend.performance import compute_metrics, trade_stats
from backend.snapshot_cache import write_snapshot, snapshot_path
from backend.trading import run_full_strategy


APP_START = pd.Timestamp("2025-01-01")


def main():
    print("Running full strategy locally to build snapshot...")
    results = run_full_strategy()
    opt = optimize_portfolio(results["optimizer_history"])

    app_daily_values = [
        row for row in results.get("daily_values", [])
        if pd.Timestamp(row["date"]) >= APP_START
    ]
    bench_df = results.get("bench_df")
    if isinstance(bench_df, pd.Series):
        app_benchmark = bench_df[bench_df.index >= APP_START]
    elif hasattr(bench_df, "loc"):
        app_benchmark = bench_df.loc[bench_df.index >= APP_START]
    else:
        app_benchmark = bench_df

    initial_capital = (
        float(app_daily_values[0]["portfolio"])
        if app_daily_values else results["initial_capital"]
    )
    metrics = compute_metrics(app_daily_values, initial_capital, app_benchmark)
    tstats = trade_stats(results.get("trades", []))
    metrics.update(tstats)

    loaded_at = datetime.now().isoformat()
    path = write_snapshot(
        results=results,
        opt=opt,
        metrics=metrics,
        tstats=tstats,
        loaded_at=loaded_at,
    )

    print(f"Snapshot written to {path}")
    print(f"Set APP_SNAPSHOT_PATH to override the default path ({snapshot_path()}).")


if __name__ == "__main__":
    main()
