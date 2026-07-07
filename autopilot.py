from paper_engine import portfolio, place_paper_trade, signal, close_position, update_position_price
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
                "action": "SKIPPED",
                "reason": quote.get("error")
            })
            continue

        current_price = float(quote["price"])
        update_position_price(symbol, current_price)

        position_signal = signal(symbol, current_price)
        market_analysis = analyze_symbol(symbol)

        should_sell = False
        reason = ""

        if position_signal["action"] == "SELL":
            should_sell = True
            reason = position_signal["reason"]

        elif market_analysis.get("signal") == "AVOID":
            should_sell = True
            reason = "Trend weakened"

        elif market_analysis.get("rsi", 0) >= 75:
            should_sell = True
            reason = "RSI overbought"

        if should_sell:
            trade = close_position(
                symbol=symbol,
                price=current_price,
                confidence=position_signal.get("confidence", 90),
                reason="Auto SELL: " + reason
            )

            actions.append({
                "symbol": symbol,
                "action": "SELL",
                "price": current_price,
                "reason": reason,
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

    port = portfolio()
    acct = port["account"]

    if acct["open_positions"] >= acct["max_open_positions"]:
        return {
            "status": "completed",
            "managed": managed,
            "buy_attempt": None,
            "reason": "Maximum open positions reached",
            "portfolio": portfolio()
        }

    scan = scan_market()

    buys = [
        r for r in scan
        if r.get("signal") == "BUY" and r.get("confidence", 0) >= MIN_BUY_CONFIDENCE
    ]

    current_positions = {p["symbol"] for p in portfolio().get("positions", [])}

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
