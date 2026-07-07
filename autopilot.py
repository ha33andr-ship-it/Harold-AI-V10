from paper_engine import portfolio, place_paper_trade, signal
from market_scanner import scan_market, get_quote, analyze_symbol

MIN_BUY_CONFIDENCE = 80


def manage_positions():
    port = portfolio()
    actions = []

    for position in port.get("positions", []):
        symbol = position["symbol"]

        quote = get_quote(symbol)
        if quote.get("error"):
            actions.append({
                "symbol": symbol,
                "status": "skipped",
                "reason": quote.get("error")
            })
            continue

        current_price = float(quote["price"])
        position_signal = signal(symbol, current_price)
        market_analysis = analyze_symbol(symbol)

        should_sell = False
        sell_reason = ""

        if position_signal.get("action") == "SELL":
            should_sell = True
            sell_reason = position_signal.get("reason", "Sell signal")

        elif market_analysis.get("signal") == "AVOID":
            should_sell = True
            sell_reason = "Trend weakened: " + market_analysis.get("reason", "")

        elif market_analysis.get("rsi", 0) >= 75:
            should_sell = True
            sell_reason = "RSI overbought"

        if should_sell:
            trade = place_paper_trade(
                symbol=symbol,
                action="SELL",
                price=current_price,
                confidence=position_signal.get("confidence", 85),
                reason="Auto SELL: " + sell_reason
            )

            actions.append({
                "symbol": symbol,
                "action": "SELL",
                "price": current_price,
                "reason": sell_reason,
                "trade_result": trade
            })

        else:
            actions.append({
                "symbol": symbol,
                "action": "HOLD",
                "price": current_price,
                "signal": position_signal,
                "analysis": market_analysis
            })

    return {
        "status": "managed",
        "actions": actions,
        "portfolio": portfolio()
    }


def run_autopilot():
    managed = manage_positions()
    scan = scan_market()

    buys = [
        r for r in scan
        if r.get("signal") == "BUY" and r.get("confidence", 0) >= MIN_BUY_CONFIDENCE
    ]

    current_positions = {
        p["symbol"] for p in portfolio().get("positions", [])
    }

    best = None

    for candidate in buys:
        if candidate["symbol"] not in current_positions:
            best = candidate
            break

    if best is None:
        return {
            "status": "completed",
            "managed": managed,
            "buy_attempt": None,
            "reason": "No new BUY candidate available",
            "portfolio": portfolio()
        }

    trade = place_paper_trade(
        symbol=best["symbol"],
        action="BUY",
        price=float(best["price"]),
        confidence=float(best["confidence"]),
        reason="Autopilot BUY: " + best.get("reason", "")
    )

    return {
        "status": "completed",
        "managed": managed,
        "buy_attempt": {
            "selected": best,
            "trade_result": trade
        },
        "portfolio": portfolio()
    }
