from datetime import datetime, date
from pathlib import Path
import json

DATA_DIR = Path("/tmp/harold_ai_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "paper_state.json"

STARTING_BALANCE = 10000.00
MAX_TRADES_PER_DAY = 3
MAX_POSITION_SIZE_PCT = 0.10
MIN_CONFIDENCE = 70

DEFAULT_STATE = {
    "cash": STARTING_BALANCE,
    "starting_balance": STARTING_BALANCE,
    "positions": {},
    "trades": []
}


def _save(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load():
    if not STATE_FILE.exists():
        _save(DEFAULT_STATE.copy())
    return json.loads(STATE_FILE.read_text())


def _today_trade_count(state):
    today = date.today().isoformat()
    return sum(1 for t in state["trades"] if t["time"].startswith(today))


def portfolio():
    state = _load()
    positions = []
    invested = 0

    for symbol, p in state["positions"].items():
        market_price = float(p.get("last_price", p["avg_price"]))
        market_value = float(p["qty"]) * market_price
        cost = float(p["qty"]) * float(p["avg_price"])
        invested += market_value

        positions.append({
            "symbol": symbol,
            "qty": p["qty"],
            "avg_price": round(p["avg_price"], 2),
            "last_price": round(market_price, 2),
            "market_value": round(market_value, 2),
            "unrealized_pl": round(market_value - cost, 2)
        })

    equity = float(state["cash"]) + invested

    return {
        "account": {
            "cash": round(float(state["cash"]), 2),
            "equity": round(equity, 2),
            "starting_balance": STARTING_BALANCE,
            "total_pl": round(equity - STARTING_BALANCE, 2),
            "trades_today": _today_trade_count(state),
            "max_trades_per_day": MAX_TRADES_PER_DAY
        },
        "positions": positions,
        "recent_trades": list(reversed(state["trades"][-25:]))
    }


def place_paper_trade(symbol, action, price, confidence, reason="Harold AI signal"):
    symbol = symbol.upper().strip()
    action = action.upper().strip()
    price = float(price)
    confidence = float(confidence)

    if price <= 0:
        return {"status": "blocked", "reason": "Price must be greater than 0"}

    if confidence < MIN_CONFIDENCE:
        return {"status": "blocked", "reason": "Confidence below minimum"}

    state = _load()

    if _today_trade_count(state) >= MAX_TRADES_PER_DAY:
        return {"status": "blocked", "reason": "Max trades per day reached"}

    acct = portfolio()["account"]
    max_dollars = acct["equity"] * MAX_POSITION_SIZE_PCT
    qty = int(max_dollars // price)

    if qty <= 0:
        return {"status": "blocked", "reason": "Not enough buying power"}

    if action == "BUY":
        cost = qty * price

        if cost > state["cash"]:
            return {"status": "blocked", "reason": "Insufficient paper cash"}

        pos = state["positions"].get(symbol)

        if pos:
            old_qty = float(pos["qty"])
            old_avg = float(pos["avg_price"])
            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + cost) / new_qty
            pos.update({"qty": new_qty, "avg_price": new_avg, "last_price": price})
        else:
            state["positions"][symbol] = {
                "qty": qty,
                "avg_price": price,
                "last_price": price
            }

        state["cash"] = float(state["cash"]) - cost

    elif action == "SELL":
        pos = state["positions"].get(symbol)

        if not pos:
            return {"status": "blocked", "reason": "No position to sell"}

        sell_qty = min(qty, float(pos["qty"]))
        proceeds = sell_qty * price
        remaining = float(pos["qty"]) - sell_qty

        if remaining <= 0:
            del state["positions"][symbol]
        else:
            pos["qty"] = remaining
            pos["last_price"] = price

        state["cash"] = float(state["cash"]) + proceeds
        qty = sell_qty

    else:
        return {"status": "blocked", "reason": "Action must be BUY or SELL"}

    trade = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "price": round(price, 2),
        "confidence": confidence,
        "reason": reason
    }

    state["trades"].append(trade)
    _save(state)

    return {
        "status": "executed",
        "mode": "PAPER",
        **trade,
        "portfolio": portfolio()["account"]
    }
