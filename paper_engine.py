from datetime import datetime, date
import sqlite3

DB = "paper_trades.db"

STARTING_BALANCE = 10000
MAX_TRADES_PER_DAY = 3
MAX_POSITION_SIZE_PCT = 0.10
DAILY_LOSS_LIMIT_PCT = 0.03


def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS account (
        id INTEGER PRIMARY KEY,
        cash REAL,
        equity REAL,
        starting_balance REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        symbol TEXT PRIMARY KEY,
        qty REAL,
        avg_price REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        symbol TEXT,
        action TEXT,
        qty REAL,
        price REAL,
        reason TEXT
    )
    """)

    cur.execute("SELECT COUNT(*) FROM account")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO account (id, cash, equity, starting_balance) VALUES (1, ?, ?, ?)",
            (STARTING_BALANCE, STARTING_BALANCE, STARTING_BALANCE)
        )

    con.commit()
    con.close()


def get_account():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT cash, equity, starting_balance FROM account WHERE id=1")
    row = cur.fetchone()
    con.close()
    return {
        "cash": row[0],
        "equity": row[1],
        "starting_balance": row[2]
    }


def trades_today():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    today = date.today().isoformat()
    cur.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (today + "%",))
    count = cur.fetchone()[0]
    con.close()
    return count


def place_paper_trade(symbol, action, price, confidence, reason="AI signal"):
    init_db()

    symbol = symbol.upper()
    action = action.upper()
    acct = get_account()

    if trades_today() >= MAX_TRADES_PER_DAY:
        return {"status": "blocked", "reason": "Max trades per day reached"}

    if confidence < 70:
        return {"status": "blocked", "reason": "Confidence below 70"}

    max_dollars = acct["equity"] * MAX_POSITION_SIZE_PCT
    qty = int(max_dollars // price)

    if qty <= 0:
        return {"status": "blocked", "reason": "Not enough buying power"}

    con = sqlite3.connect(DB)
    cur = con.cursor()

    if action == "BUY":
        cost = qty * price
        if cost > acct["cash"]:
            con.close()
            return {"status": "blocked", "reason": "Insufficient cash"}

        cur.execute("SELECT qty, avg_price FROM positions WHERE symbol=?", (symbol,))
        pos = cur.fetchone()

        if pos:
            old_qty, old_avg = pos
            new_qty = old_qty + qty
            new_avg = ((old_qty * old_avg) + cost) / new_qty
            cur.execute(
                "UPDATE positions SET qty=?, avg_price=? WHERE symbol=?",
                (new_qty, new_avg, symbol)
            )
        else:
            cur.execute(
                "INSERT INTO positions (symbol, qty, avg_price) VALUES (?, ?, ?)",
                (symbol, qty, price)
            )

        cur.execute("UPDATE account SET cash=cash-? WHERE id=1", (cost,))

    elif action == "SELL":
        cur.execute("SELECT qty, avg_price FROM positions WHERE symbol=?", (symbol,))
        pos = cur.fetchone()

        if not pos:
            con.close()
            return {"status": "blocked", "reason": "No position to sell"}

        held_qty, avg_price = pos
        sell_qty = min(qty, held_qty)
        proceeds = sell_qty * price

        if sell_qty == held_qty:
            cur.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
        else:
            cur.execute(
                "UPDATE positions SET qty=? WHERE symbol=?",
                (held_qty - sell_qty, symbol)
            )

        cur.execute("UPDATE account SET cash=cash+? WHERE id=1", (proceeds,))

    else:
        con.close()
        return {"status": "error", "reason": "Invalid action"}

    cur.execute(
        "INSERT INTO trades (ts, symbol, action, qty, price, reason) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), symbol, action, qty, price, reason)
    )

    con.commit()
    con.close()

    return {
        "status": "executed",
        "mode": "PAPER",
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "price": price,
        "confidence": confidence
    }


def portfolio():
    init_db()
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("SELECT cash, equity, starting_balance FROM account WHERE id=1")
    account = cur.fetchone()

    cur.execute("SELECT symbol, qty, avg_price FROM positions")
    positions = cur.fetchall()

    cur.execute("SELECT ts, symbol, action, qty, price, reason FROM trades ORDER BY id DESC LIMIT 25")
    trades = cur.fetchall()

    con.close()

    return {
        "account": {
            "cash": account[0],
            "equity": account[1],
            "starting_balance": account[2]
        },
        "positions": [
            {"symbol": p[0], "qty": p[1], "avg_price": p[2]}
            for p in positions
        ],
        "recent_trades": [
            {
                "time": t[0],
                "symbol": t[1],
                "action": t[2],
                "qty": t[3],
                "price": t[4],
                "reason": t[5]
            }
            for t in trades
        ]
    }
