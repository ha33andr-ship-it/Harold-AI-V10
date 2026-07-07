from datetime import datetime, date
from pathlib import Path
import json
import copy

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
    "trades": [],
    "equity_history": [
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "equity": STARTING_BALANCE
        }
    ]
}


def _default_state():
    return copy.deepcopy(DEFAULT_STATE)


def _save(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load():
    if not STATE_FILE.exists():
        state = _default_state()
        _save(state)
        return state

    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        state = _default_state()
        _save(state)
        return state


def _today_trade_count(state):
    today = date.today().isoformat()
    return sum(1 for t in state["trades"] if t["time"].startswith(today))


def _calculate_equity(state):
    invested = 0.0

    for _, p in state["positions"].items():
        market_price = float(p.get("last_price", p["avg_price"]))
        invested += float(p["qty"]) * market_price

    return float(state["cash"]) + invested


def _record_equity(state):
    equity = _calculate_equity(state)
    state.setdefault("equity_history", [])
    state["equity_history"].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "equity": round(equity, 2)
    })


def portfolio():
    state = _load()
    positions = []
    invested = 0.0

    for symbol, p in state["positions"].items():
        market_price = float(p.get("last_price", p["avg_price"]))
        market_value = float(p["qty"]) * market_price
        cost = float(p["qty"]) * float(p["avg_price"])
        invested += market_value

        positions.append({
            "symbol": symbol,
            "qty": p["qty"],
            "avg_price": round(float(p["avg_price"]), 2),
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

    equity = _calculate_equity(state)
    max_dollars = equity * MAX_POSITION_SIZE_PCT
    qty = int(max_dollars // price)

    if qty <= 0:
        return {"status": "blocked", "reason": "Not enough buying power"}

    realized_pl = 0.0

    if action == "BUY":
        cost = qty * price

        if cost > float(state["cash"]):
            return {"status": "blocked", "reason": "Insufficient paper cash"}

        pos = state["positions"].get(symbol)

        if pos:
            old_qty = float(pos["qty"])
            old_avg = float(pos["avg_price"])
            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + cost) / new_qty

            pos["qty"] = new_qty
            pos["avg_price"] = new_avg
            pos["last_price"] = price
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
        avg_price = float(pos["avg_price"])
        realized_pl = (price - avg_price) * sell_qty
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
        "reason": reason,
        "realized_pl": round(realized_pl, 2)
    }

    state["trades"].append(trade)
    _record_equity(state)
    _save(state)

    return {
        "status": "executed",
        "mode": "PAPER",
        **trade,
        "portfolio": portfolio()["account"]
    }


def performance():
    state = _load()
    trades = state.get("trades", [])

    sell_trades = [t for t in trades if t.get("action") == "SELL"]
    closed_trades = len(sell_trades)

    wins = [float(t.get("realized_pl", 0)) for t in sell_trades if float(t.get("realized_pl", 0)) > 0]
    losses = [abs(float(t.get("realized_pl", 0))) for t in sell_trades if float(t.get("realized_pl", 0)) < 0]

    realized_pl = sum(float(t.get("realized_pl", 0)) for t in sell_trades)

    win_rate = round((len(wins) / closed_trades) * 100, 2) if closed_trades else 0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
    profit_factor = round(sum(wins) / sum(losses), 2) if sum(losses) > 0 else None

    equity_history = state.get("equity_history", [])
    max_drawdown = 0.0
    peak = STARTING_BALANCE

    for point in equity_history:
        equity = float(point["equity"])
        if equity > peak:
            peak = equity
        drawdown = ((peak - equity) / peak) * 100 if peak else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    acct = portfolio()["account"]

    return {
        "total_trades": len(trades),
        "closed_trades": closed_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": win_rate,
        "realized_pl": round(realized_pl, 2),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_drawdown, 2),
        "cash": acct["cash"],
        "equity": acct["equity"],
        "total_pl": acct["total_pl"]
    }


def reset_paper_account():
    state = _default_state()
    _save(state)

    return {
        "status": "reset",
        "message": "Paper account reset to starting balance",
        "portfolio": portfolio()
    }
