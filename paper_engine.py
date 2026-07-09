from datetime import datetime, date
from pathlib import Path
import json
import copy

DATA_DIR = Path("/tmp/harold_ai_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "paper_state.json"

STARTING_BALANCE = 10000.00

MAX_TRADES_PER_DAY = 3
MAX_OPEN_POSITIONS = 3
MAX_POSITION_SIZE_PCT = 0.10
MIN_CONFIDENCE = 70

TAKE_PROFIT_PCT = 2.0
STOP_LOSS_PCT = -1.5

DEFAULT_STATE = {
    "cash": STARTING_BALANCE,
    "starting_balance": STARTING_BALANCE,
    "positions": {},
    "trades": [],
    "equity_history": []
}


def _default_state():
    state = copy.deepcopy(DEFAULT_STATE)
    state["equity_history"] = [{
        "time": datetime.now().isoformat(timespec="seconds"),
        "equity": STARTING_BALANCE
    }]
    return state


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
    return sum(
        1 for t in state.get("trades", [])
        if t.get("time", "").startswith(today)
        and t.get("action") == "BUY"
    )


def _calculate_equity(state):
    invested = 0.0

    for p in state.get("positions", {}).values():
        invested += float(p["qty"]) * float(p.get("last_price", p["avg_price"]))

    return float(state["cash"]) + invested


def _record_equity(state):
    state.setdefault("equity_history", [])
    state["equity_history"].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "equity": round(_calculate_equity(state), 2)
    })


def update_position_price(symbol, price):
    state = _load()
    symbol = symbol.upper().strip()

    if symbol in state["positions"]:
        state["positions"][symbol]["last_price"] = float(price)
        _record_equity(state)
        _save(state)

    return portfolio()


def portfolio():
    state = _load()
    positions = []
    invested = 0.0

    for symbol, p in state.get("positions", {}).items():
        qty = float(p["qty"])
        avg = float(p["avg_price"])
        last = float(p.get("last_price", avg))

        value = qty * last
        cost = qty * avg
        invested += value

        positions.append({
            "symbol": symbol,
            "qty": qty,
            "avg_price": round(avg, 2),
            "last_price": round(last, 2),
            "market_value": round(value, 2),
            "unrealized_pl": round(value - cost, 2),
            "unrealized_pl_pct": round(((last - avg) / avg) * 100, 2) if avg else 0
        })

    equity = float(state["cash"]) + invested

    return {
        "account": {
            "cash": round(float(state["cash"]), 2),
            "equity": round(equity, 2),
            "starting_balance": STARTING_BALANCE,
            "total_pl": round(equity - STARTING_BALANCE, 2),
            "total_return_pct": round(((equity - STARTING_BALANCE) / STARTING_BALANCE) * 100, 2),
            "trades_today": _today_trade_count(state),
            "max_trades_per_day": MAX_TRADES_PER_DAY,
            "open_positions": len(state.get("positions", {})),
            "max_open_positions": MAX_OPEN_POSITIONS
        },
        "positions": positions,
        "recent_trades": list(reversed(state.get("trades", [])[-25:]))
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

    if action == "BUY":
        if symbol not in state["positions"] and len(state["positions"]) >= MAX_OPEN_POSITIONS:
            return {
                "status": "blocked",
                "reason": f"Maximum open positions ({MAX_OPEN_POSITIONS}) reached"
            }

        if _today_trade_count(state) >= MAX_TRADES_PER_DAY:
            return {"status": "blocked", "reason": "Max BUY trades per day reached"}

        equity = _calculate_equity(state)
        qty = int((equity * MAX_POSITION_SIZE_PCT) // price)

        if qty <= 0:
            return {"status": "blocked", "reason": "Not enough buying power"}

        cost = qty * price

        if cost > float(state["cash"]):
            return {"status": "blocked", "reason": "Insufficient cash"}

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
        realized_pl = 0.0

    elif action == "SELL":
        return close_position(symbol, price, confidence, reason)

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


def close_position(symbol, price, confidence=90, reason="Auto exit"):
    state = _load()
    symbol = symbol.upper().strip()
    price = float(price)

    pos = state["positions"].get(symbol)

    if not pos:
        return {"status": "blocked", "reason": "No position to sell"}

    qty = float(pos["qty"])
    avg = float(pos["avg_price"])
    proceeds = qty * price
    realized_pl = (price - avg) * qty

    state["cash"] = float(state["cash"]) + proceeds
    del state["positions"][symbol]

    trade = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "action": "SELL",
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


def signal(symbol, price=None):
    state = _load()
    symbol = symbol.upper().strip()
    pos = state.get("positions", {}).get(symbol)

    if not pos:
        return {
            "symbol": symbol,
            "action": "WATCH",
            "confidence": 60,
            "reason": "No position yet"
        }

    avg = float(pos["avg_price"])
    last = float(price) if price else float(pos.get("last_price", avg))
    gain_pct = ((last - avg) / avg) * 100 if avg else 0

    if gain_pct >= TAKE_PROFIT_PCT:
        return {
            "symbol": symbol,
            "action": "SELL",
            "confidence": 90,
            "avg_price": round(avg, 2),
            "last_price": round(last, 2),
            "gain_pct": round(gain_pct, 2),
            "take_profit_pct": TAKE_PROFIT_PCT,
            "stop_loss_pct": STOP_LOSS_PCT,
            "reason": f"Take profit target reached: {TAKE_PROFIT_PCT}%"
        }

    if gain_pct <= STOP_LOSS_PCT:
        return {
            "symbol": symbol,
            "action": "SELL",
            "confidence": 95,
            "avg_price": round(avg, 2),
            "last_price": round(last, 2),
            "gain_pct": round(gain_pct, 2),
            "take_profit_pct": TAKE_PROFIT_PCT,
            "stop_loss_pct": STOP_LOSS_PCT,
            "reason": f"Stop loss triggered: {STOP_LOSS_PCT}%"
        }

    return {
        "symbol": symbol,
        "action": "HOLD",
        "confidence": 75,
        "avg_price": round(avg, 2),
        "last_price": round(last, 2),
        "gain_pct": round(gain_pct, 2),
        "take_profit_pct": TAKE_PROFIT_PCT,
        "stop_loss_pct": STOP_LOSS_PCT,
        "reason": "Position is still inside hold range"
    }


def performance():
    state = _load()
    trades = state.get("trades", [])
    sells = [t for t in trades if t.get("action") == "SELL"]

    wins = [float(t["realized_pl"]) for t in sells if float(t["realized_pl"]) > 0]
    losses = [abs(float(t["realized_pl"])) for t in sells if float(t["realized_pl"]) < 0]

    closed = len(sells)
    realized = sum(float(t.get("realized_pl", 0)) for t in sells)

    win_rate = round((len(wins) / closed) * 100, 2) if closed else 0
    profit_factor = round(sum(wins) / sum(losses), 2) if sum(losses) > 0 else 0

    acct = portfolio()["account"]

    return {
        "total_trades": len(trades),
        "closed_trades": closed,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": win_rate,
        "realized_pl": round(realized, 2),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "profit_factor": profit_factor,
        "cash": acct["cash"],
        "equity": acct["equity"],
        "total_pl": acct["total_pl"],
        "total_return_pct": acct["total_return_pct"],
        "open_positions": acct["open_positions"],
        "max_open_positions": acct["max_open_positions"],
        "buys_today": acct["trades_today"],
        "max_buys_per_day": acct["max_trades_per_day"],
        "take_profit_pct": TAKE_PROFIT_PCT,
        "stop_loss_pct": STOP_LOSS_PCT
    }


def reset_paper_account():
    state = _default_state()
    _save(state)

    return {
        "status": "reset",
        "message": "Paper account reset to starting balance",
        "portfolio": portfolio()
    }
