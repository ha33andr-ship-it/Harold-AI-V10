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
    if now.weekday() > 4:
        return False
    mins = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= mins <= (16 * 60)


@app.route("/")
def home():
    return jsonify({
        "status": "Harold AI V12 running",
        "dashboard": "/dashboard",
        "mode": "PAPER"
    })


@app.route("/paper/portfolio")
def paper_portfolio():
    return jsonify(portfolio())


@app.route("/paper/performance")
def paper_performance():
    return jsonify(performance())


@app.route("/signal/<symbol>")
def trade_signal(symbol):
    return jsonify(signal(symbol, request.args.get("price")))


@app.route("/quote/<symbol>")
def quote(symbol):
    return jsonify(get_quote(symbol))


@app.route("/analyze/<symbol>")
def analyze(symbol):
    return jsonify(analyze_symbol(symbol))


@app.route("/scan")
def scan():
    return jsonify(scan_market())


@app.route("/manage")
def manage():
    return jsonify(manage_positions())


@app.route("/autopilot")
def autopilot():
    if not market_is_open():
        return jsonify({
            "status": "market_closed",
            "message": "Autopilot is waiting for the next market session.",
            "timezone": "America/New_York"
        })
    return jsonify(run_autopilot())


@app.route("/autopilot-force")
def autopilot_force():
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
<!DOCTYPE html>
<html>
<head>
<title>Harold AI V12</title>
<meta http-equiv="refresh" content="60">
<style>
body { font-family: Arial; background:#0f172a; color:white; padding:30px; }
.card { background:#1e293b; padding:20px; border-radius:12px; margin:10px; display:inline-block; min-width:170px; }
.green { color:#22c55e; }
.red { color:#ef4444; }
table { width:100%; border-collapse:collapse; margin-top:20px; background:#1e293b; }
th,td { padding:10px; border-bottom:1px solid #334155; text-align:left; }
button { padding:10px 18px; margin:6px; border-radius:8px; border:none; cursor:pointer; }
.buy { background:#22c55e; }
.sell { background:#ef4444; color:white; }
.action { background:#38bdf8; }
</style>
</head>
<body>

<h1>🚀 Harold AI V12 Paper Trading Dashboard</h1>

<button class="action" onclick="location.href='/autopilot'">Run AutoPilot</button>
<button class="action" onclick="location.href='/manage'">Manage Positions</button>
<button class="action" onclick="location.href='/scan'">Scan Market</button>
<button class="action" onclick="location.reload()">Refresh</button>

<div id="cards"></div>

<h2>Open Positions</h2>
<table id="positions"></table>

<h2>Recent Trades</h2>
<table id="trades"></table>

<h2>Performance</h2>
<table id="performance"></table>

<h2>Manual Trade</h2>
<form action="/paper/trade-form" method="post">
Symbol <input name="symbol" value="AAPL">
Action <select name="action"><option>BUY</option><option>SELL</option></select>
Price <input name="price" value="225">
Confidence <input name="confidence" value="85">
Reason <input name="reason" value="Dashboard Trade">
<button class="buy" type="submit">Submit Trade</button>
</form>

<script>
async function loadDashboard(){
    const p = await fetch('/paper/portfolio').then(r=>r.json());
    const perf = await fetch('/paper/performance').then(r=>r.json());

    const acct = p.account;

    document.getElementById('cards').innerHTML = `
        <div class="card"><h3>Equity</h3><h2>$${acct.equity}</h2></div>
        <div class="card"><h3>Cash</h3><h2>$${acct.cash}</h2></div>
        <div class="card"><h3>Total P/L</h3><h2 class="${acct.total_pl >= 0 ? 'green':'red'}">$${acct.total_pl}</h2></div>
        <div class="card"><h3>Return</h3><h2>${acct.total_return_pct}%</h2></div>
        <div class="card"><h3>Positions</h3><h2>${acct.open_positions}/${acct.max_open_positions}</h2></div>
        <div class="card"><h3>Win Rate</h3><h2>${perf.win_rate}%</h2></div>
    `;

    let posHtml = `<tr><th>Symbol</th><th>Qty</th><th>Avg</th><th>Last</th><th>Value</th><th>P/L</th><th>%</th></tr>`;
    p.positions.forEach(x=>{
        posHtml += `<tr>
            <td>${x.symbol}</td>
            <td>${x.qty}</td>
            <td>$${x.avg_price}</td>
            <td>$${x.last_price}</td>
            <td>$${x.market_value}</td>
            <td class="${x.unrealized_pl >= 0 ? 'green':'red'}">$${x.unrealized_pl}</td>
            <td>${x.unrealized_pl_pct}%</td>
        </tr>`;
    });
    document.getElementById('positions').innerHTML = posHtml;

    let tradeHtml = `<tr><th>Time</th><th>Symbol</th><th>Action</th><th>Qty</th><th>Price</th><th>P/L</th><th>Reason</th></tr>`;
    p.recent_trades.forEach(t=>{
        tradeHtml += `<tr>
            <td>${t.time}</td>
            <td>${t.symbol}</td>
            <td>${t.action}</td>
            <td>${t.qty}</td>
            <td>$${t.price}</td>
            <td class="${t.realized_pl >= 0 ? 'green':'red'}">$${t.realized_pl}</td>
            <td>${t.reason}</td>
        </tr>`;
    });
    document.getElementById('trades').innerHTML = tradeHtml;

    document.getElementById('performance').innerHTML = `
        <tr><th>Total Trades</th><td>${perf.total_trades}</td></tr>
        <tr><th>Closed Trades</th><td>${perf.closed_trades}</td></tr>
        <tr><th>Winning Trades</th><td>${perf.winning_trades}</td></tr>
        <tr><th>Losing Trades</th><td>${perf.losing_trades}</td></tr>
        <tr><th>Realized P/L</th><td>$${perf.realized_pl}</td></tr>
        <tr><th>Profit Factor</th><td>${perf.profit_factor}</td></tr>
    `;
}
loadDashboard();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
