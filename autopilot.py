from paper_engine import portfolio, place_paper_trade, signal
from market_scanner import scan_market, get_quote


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
        decision = signal(symbol, current_price)

        if decision.get("action") == "SELL":
            trade = place_paper_trade(
                symbol=symbol,
                action="SELL",
                price=current_price,
                confidence=decision.get("confidence", 85),
                reason="Auto manage: " + decision.get("reason", "")
            )

            actions.append({
                "symbol": symbol,
                "decision": decision,
                "trade_result": trade
            })
        else:
            actions.append({
                "symbol": symbol,
                "decision": decision,
                "trade_result": None
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

    if not buys:
        return {
            "status": "completed",
            "managed": managed,
            "buy_attempt": None,
            "reason": "No BUY signal above threshold",
            "portfolio": portfolio()
        }

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
            "reason": "All top BUY candidates already held",
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
