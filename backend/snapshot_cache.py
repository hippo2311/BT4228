"""
Snapshot utilities for caching precomputed backend state to JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "cache" / "app_snapshot.json"


def snapshot_path() -> Path:
    raw = os.getenv("APP_SNAPSHOT_PATH", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_SNAPSHOT_PATH


def _json_ready(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return {"__type__": "timestamp", "value": value.isoformat()}
    if isinstance(value, pd.Series):
        return {
            "__type__": "series",
            "name": value.name,
            "index": [_json_ready(v) for v in value.index.tolist()],
            "values": [_json_ready(v) for v in value.tolist()],
        }
    if isinstance(value, pd.DataFrame):
        split = value.to_dict(orient="split")
        return {
            "__type__": "dataframe",
            "columns": [_json_ready(v) for v in split["columns"]],
            "index": [_json_ready(v) for v in split["index"]],
            "data": [[_json_ready(cell) for cell in row] for row in split["data"]],
        }
    if isinstance(value, np.ndarray):
        return {"__type__": "ndarray", "values": [_json_ready(v) for v in value.tolist()]}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def _restore(value: Any) -> Any:
    if isinstance(value, list):
        return [_restore(v) for v in value]
    if not isinstance(value, dict):
        return value

    value_type = value.get("__type__")
    if value_type == "timestamp":
        return pd.Timestamp(value["value"])
    if value_type == "series":
        index = [_restore(v) for v in value["index"]]
        data = [_restore(v) for v in value["values"]]
        return pd.Series(data=data, index=index, name=value.get("name"))
    if value_type == "dataframe":
        columns = [_restore(v) for v in value["columns"]]
        index = [_restore(v) for v in value["index"]]
        data = [[_restore(cell) for cell in row] for row in value["data"]]
        return pd.DataFrame(data=data, index=index, columns=columns)
    if value_type == "ndarray":
        return np.array([_restore(v) for v in value["values"]])
    return {k: _restore(v) for k, v in value.items()}


def _snapshot_results(results: dict) -> dict:
    keys = [
        "daily_values",
        "trades",
        "signals",
        "final_positions",
        "final_equity",
        "price_returns",
        "current_prices",
        "current_atr",
        "fees",
        "bench_df",
        "initial_capital",
        "params",
        "tickers",
        "selected_tickers",
        "optimizer_allocations",
    ]
    return {key: results.get(key) for key in keys}


def build_snapshot_payload(*, results: dict, opt: dict, metrics: dict, tstats: dict, loaded_at: str) -> dict:
    return {
        "version": 1,
        "loaded_at": loaded_at,
        "results": _json_ready(_snapshot_results(results)),
        "opt": _json_ready(opt),
        "metrics": _json_ready(metrics),
        "tstats": _json_ready(tstats),
    }


def write_snapshot(*, results: dict, opt: dict, metrics: dict, tstats: dict, loaded_at: str) -> Path:
    path = snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_snapshot_payload(
        results=results,
        opt=opt,
        metrics=metrics,
        tstats=tstats,
        loaded_at=loaded_at,
    )
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return path


def read_snapshot() -> dict | None:
    path = snapshot_path()
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "version": payload.get("version", 1),
        "loaded_at": payload.get("loaded_at"),
        "results": _restore(payload.get("results", {})),
        "opt": _restore(payload.get("opt", {})),
        "metrics": _restore(payload.get("metrics", {})),
        "tstats": _restore(payload.get("tstats", {})),
    }
