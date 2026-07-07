import yfinance as yf
import pandas as pd


WATCHLIST = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "SPY", "QQQ"]


def get_quote(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")

    if hist.empty:
        return {"symbol": symbol.upper(), "error": "No market data"}

    last = float(hist["Close"].iloc[-1])

    return {
        "symbol": symbol.upper(),
        "price": round(last, 2)
    }


def analyze_symbol(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="6mo")

    if df.empty or len(df) < 50:
        return {
            "symbol": symbol.upper(),
            "signal": "NO DATA",
            "confidence": 0,
            "reason": "Not enough market data"
        }

    df["ema9"] = df["Close"].ewm(span=9).mean()
    df["ema20"] = df["Close"].ewm(span=20).mean()
    df["ema50"] = df["Close"].ewm(span=50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    latest = df.iloc[-1]

    price = float(latest["Close"])
    ema9 = float(latest["ema9"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    rsi = float(latest["rsi"])

    score = 0
    reasons = []

    if price > ema20:
        score += 25
        reasons.append("Price above 20 EMA")

    if ema9 > ema20:
        score += 25
        reasons.append("9 EMA above 20 EMA")

    if price > ema50:
        score += 20
        reasons.append("Price above 50 EMA")

    if 45 <= rsi <= 70:
        score += 20
        reasons.append("RSI healthy")

    if rsi > 70:
        reasons.append("RSI overbought")

    if score >= 80:
        signal = "BUY"
    elif score >= 60:
        signal = "WATCH"
    else:
        signal = "AVOID"

    return {
        "symbol": symbol.upper(),
        "price": round(price, 2),
        "signal": signal,
        "confidence": score,
        "rsi": round(rsi, 2),
        "ema9": round(ema9, 2),
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "reason": ", ".join(reasons)
    }


def scan_market():
    results = []

    for symbol in WATCHLIST:
        try:
            results.append(analyze_symbol(symbol))
        except Exception as e:
            results.append({
                "symbol": symbol,
                "signal": "ERROR",
                "confidence": 0,
                "reason": str(e)
            })

    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results
