from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request

from paper_engine import (
    portfolio,
    place_paper_trade,
    performance,
    reset_paper_account,
    signal,
)
from market_scanner import get_quote, analyze_symbol, scan_market
from autopilot import manage_positions, run_autopilot

app = Flask(__name__)


def market_is_open():
    now = datetime.now(ZoneInfo("America/New_York"))

    # Monday = 0, Friday = 4
    if now.weekday() > 4:
        return False

    current_minutes = now.hour * 60 + now.minute
    open_minutes = 9 * 60 + 30
    close_minutes = 16 * 60

    return open_minutes <= current_minutes <= close_minutes


@app.route("/")
def home():
    return jsonify({
        "status": "Harold AI V11.3 running",
        "mode": "PAPER",
        "dashboard": "/dashboard",
        "portfolio_url": "/paper/portfolio",
        "performance_url": "/paper/performance",
        "scan_url": "/scan",
        "auto_trade_url": "/auto-trade",
        "manage_url": "/manage",
        "autopilot_url": "/autopilot",
        "market_hours_guard": True
    })


@app.route("/paper/portfolio")
def paper_portfolio():
    return jsonify(portfolio())


@app.route("/paper/performance")
def paper_performance():
    return jsonify(performance())


@app.route("/signal/<symbol>")
def trade_signal(symbol):
    price = request.args.get("price")
    return jsonify(signal(symbol, price))


@app.route("/quote/<symbol>")
def quote(symbol):
    return jsonify(get_quote(symbol))


@app.route("/analyze/<symbol>")
def analyze(symbol):
    return jsonify(analyze_symbol(symbol))


@app.route("/scan")
def scan():
    return jsonify(scan_market())


@app.route("/auto-trade")
def auto_trade():
    results = scan_market()

    buys = [
        r for r in results
        if r.get("signal") == "BUY" and r.get("confidence", 0) >= 80
    ]

    if not buys:
        return jsonify({
            "status": "no_trade",
            "reason": "No BUY signal above confidence threshold",
            "scan": results
        })

    best = buys[0]

    trade = place_paper_trade(
        symbol=best["symbol"],
        action="BUY",
        price=float(best["price"]),
        confidence=float(best["confidence"]),
        reason="Auto trade: " + best.get("reason", "")
    )

    return jsonify({
        "status": "auto_trade_attempted",
        "selected": best,
        "trade_result": trade
    })


@app.route("/manage")
def manage():
    return jsonify(manage_positions())


@app.route("/autopilot")
def autopilot():
    if not market_is_open():
        return jsonify({
            "status": "market_closed",
            "market": "NYSE / NASDAQ",
            "timezone": "America/New_York",
            "message": "Autopilot is waiting for the next market session."
        })

    return jsonify(run_autopilot())


@app.route("/paper/trade", methods=["POST"])
def paper_trade():
    data = request.get_json()

    return jsonify(place_paper_trade(
        symbol=data.get("symbol"),
        action=data.get("action"),
        price=float(data.get("price")),
        confidence=float(data.get("confidence")),
        reason=data.get("reason", "API Trade")
    ))


@app.route("/paper/trade-form", methods=["POST"])
def trade_form():
    return jsonify(place_paper_trade(
        symbol=request.form.get("symbol"),
        action=request.form.get("action"),
        price=float(request.form.get("price")),
        confidence=float(request.form.get("confidence")),
        reason=request.form.get("reason", "Dashboard Trade")
    ))


@app.route("/paper/reset", methods=["POST"])
def reset_account():
    return jsonify(reset_paper_account())


@app.route("/dashboard")
def dashboard():
    return """
    <html>
    <head>
        <title>Harold AI V11.3 Dashboard</title>
    </head>

    <body style="font-family:Arial;padding:40px;max-width:900px;">

        <h1>🚀 Harold AI V11.3</h1>
        <h2>Autonomous Paper Trading Dashboard</h2>

        <hr>

        <h3>Portfolio</h3>
        <p><a href="/paper/portfolio">📁 Portfolio</a></p>
        <p><a href="/paper/performance">📈 Performance</a></p>

        <hr>

        <h3>Market Scanner</h3>
        <p><a href="/scan">🔍 Scan Market</a></p>
        <p><a href="/quote/AAPL">💲 Live Quote AAPL</a></p>
        <p><a href="/analyze/AAPL">📊 Analyze AAPL</a></p>
        <p><a href="/signal/AAPL?price=240">📡 Check AAPL Position Signal</a></p>

        <hr>

        <h3>Automation</h3>
        <p><a href="/auto-trade">🤖 Auto Buy Best Stock</a></p>
        <p><a href="/manage">🛡 Manage Open Positions</a></p>
        <p><a href="/autopilot">🚀 Run Full AutoPilot</a></p>

        <p><b>Note:</b> Full AutoPilot only trades during normal U.S. market hours.</p>

        <hr>

        <h3>Manual Trade</h3>

        <form action="/paper/trade-form" method="post">

            Symbol<br>
            <input name="symbol" value="AAPL"><br><br>

            Action<br>
            <select name="action">
                <option>BUY</option>
                <option>SELL</option>
            </select><br><br>

            Price<br>
            <input name="price" value="225"><br><br>

            Confidence<br>
            <input name="confidence" value="85"><br><br>

            Reason<br>
            <input name="reason" value="Dashboard Trade"><br><br>

            <button type="submit">Execute Paper Trade</button>

        </form>

        <hr>

        <h3>Reset Paper Account</h3>
        <form action="/paper/reset" method="post">
            <button type="submit">Reset Account</button>
        </form>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
