import sqlite3
from datetime import datetime

DB = "paper_trading.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        action TEXT,
        qty REAL,
        price REAL,
        confidence REAL,
        reason TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()


def place_paper_trade(symbol, action, price, confidence, reason):
    qty = 1

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO trades
        (symbol, action, qty, price, confidence, reason, time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol,
        action,
        qty,
        price,
        confidence,
        reason,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}


def portfolio():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT symbol, action, qty, price,
               confidence, reason, time
        FROM trades
        ORDER BY id DESC
    """)

    rows = c.fetchall()
    conn.close()

    trades = []

    for r in rows:
        trades.append({
            "symbol": r[0],
            "action": r[1],
            "qty": r[2],
            "price": r[3],
            "confidence": r[4],
            "reason": r[5],
            "time": r[6]
        })

    return {
        "recent_trades": trades
    }
