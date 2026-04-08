"""
Interactive Brokers paper-trading bridge for the notebook-faithful strategy.

Requirements:
- TWS or IB Gateway must be running and logged into Paper Trading.
- API access must be enabled.
- Python package `ib_insync` must be installed.

Default mode is dry-run. Use --execute to place market orders.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from ib_insync import IB, MarketOrder, Stock
except ImportError:  # pragma: no cover
    IB = None
    MarketOrder = None
    Stock = None


ROOT_DIR = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(ROOT_DIR / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trading import run_full_strategy


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ibkr_paper")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync current strategy positions to an IBKR paper account.")
    parser.add_argument("--execute", action="store_true", help="Place orders. Without this flag the script is dry-run only.")
    parser.add_argument("--close-extra", action="store_true", help="Close IBKR positions not required by the strategy.")
    parser.add_argument("--allow-short", action="store_true", help="Allow short targets from the strategy.")
    parser.add_argument("--max-orders", type=int, default=20, help="Safety limit for submitted orders.")
    return parser.parse_args()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _require_ib_insync() -> None:
    if IB is None or Stock is None or MarketOrder is None:
        raise RuntimeError(
            "Missing dependency `ib_insync`. Install it with `.venv/bin/pip install ib_insync`."
        )


def _get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else default


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got: {raw}") from exc


def _connect_ib() -> IB:
    _require_ib_insync()
    host = _get_env_str("IBKR_HOST", "127.0.0.1")
    port = _get_env_int("IBKR_PORT", 7497)
    client_id = _get_env_int("IBKR_CLIENT_ID", 1)

    ib = IB()
    try:
        ib.connect(host=host, port=port, clientId=client_id, readonly=False, timeout=15)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            f"Failed to connect to IBKR at {host}:{port} with clientId={client_id}. "
            "Make sure TWS or IB Gateway is running in Paper mode and API access is enabled."
        ) from exc
    return ib


def _account_equity(ib: IB) -> float:
    for row in ib.accountSummary():
        if row.tag == "NetLiquidation" and row.currency == "USD":
            return _safe_float(row.value, 0.0)
    raise RuntimeError("Could not read IBKR NetLiquidation from account summary.")


def build_target_positions(results: dict, account_equity: float, allow_short: bool) -> dict[str, int]:
    final_positions = results.get("final_positions") or {}
    allocations = results.get("optimizer_allocations") or {}
    current_prices = results.get("current_prices") or {}

    targets: dict[str, int] = {}
    for symbol, position in final_positions.items():
        allocation = _safe_float(allocations.get(symbol), 0.0)
        price = _safe_float(current_prices.get(symbol, {}).get("price"), 0.0)
        direction = position.get("direction")
        if allocation <= 0 or price <= 0 or direction not in {"LONG", "SHORT"}:
            continue

        qty = math.floor((account_equity * allocation) / price)
        if qty <= 0:
            continue

        if direction == "SHORT":
            if not allow_short:
                continue
            qty *= -1

        targets[symbol] = qty

    return targets


def current_position_map(ib: IB) -> dict[str, int]:
    out: dict[str, int] = {}
    for position in ib.positions():
        contract = position.contract
        if getattr(contract, "secType", "") != "STK":
            continue
        out[contract.symbol] = int(position.position)
    return out


def build_orders(current_positions: dict[str, int], target_positions: dict[str, int], close_extra: bool) -> list[dict]:
    orders: list[dict] = []
    symbols = set(target_positions)
    if close_extra:
        symbols |= set(current_positions)

    for symbol in sorted(symbols):
        current_qty = current_positions.get(symbol, 0)
        target_qty = target_positions.get(symbol, 0)
        delta = target_qty - current_qty
        if delta == 0:
            continue

        orders.append(
            {
                "symbol": symbol,
                "side": "BUY" if delta > 0 else "SELL",
                "qty": abs(delta),
                "target_qty": target_qty,
                "current_qty": current_qty,
            }
        )

    return orders


def submit_orders(ib: IB, orders: list[dict]) -> list[dict]:
    submitted: list[dict] = []
    for order in orders:
        contract = Stock(order["symbol"], "SMART", "USD")
        ib.qualifyContracts(contract)
        trade = ib.placeOrder(contract, MarketOrder(order["side"], order["qty"]))
        submitted.append(
            {
                "symbol": order["symbol"],
                "side": order["side"],
                "qty": order["qty"],
                "status": trade.orderStatus.status,
                "order_id": trade.order.orderId,
            }
        )
        logger.info(
            "Submitted %s %s x%s -> order_id=%s status=%s",
            order["side"],
            order["symbol"],
            order["qty"],
            trade.order.orderId,
            trade.orderStatus.status,
        )
    return submitted


def main() -> int:
    args = parse_args()

    logger.info("Running strategy to compute current target positions")
    results = run_full_strategy()
    ib = _connect_ib()

    try:
        account_equity = _account_equity(ib)
        current_positions = current_position_map(ib)
        target_positions = build_target_positions(results, account_equity, allow_short=args.allow_short)
        orders = build_orders(current_positions, target_positions, close_extra=args.close_extra)

        summary = {
            "account_equity": round(account_equity, 2),
            "selected_tickers": results.get("selected_tickers"),
            "target_positions": target_positions,
            "current_positions": current_positions,
            "orders": orders,
            "mode": "execute" if args.execute else "dry-run",
        }
        print(json.dumps(summary, indent=2))

        if not args.execute:
            logger.info("Dry-run only. Re-run with --execute to place orders.")
            return 0

        if len(orders) > args.max_orders:
            raise RuntimeError(f"Refusing to submit {len(orders)} orders; exceeds --max-orders={args.max_orders}")

        submit_orders(ib, orders)
        return 0
    finally:
        ib.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
