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
        "mode": "PAPER",
        "market_open": market_is_open(),
        "autopilot": "/autopilot",
        "autopilot_force": "/autopilot-force"
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
h1 { margin-bottom: 6px; }
.sub { color:#94a3b8; margin-top:0; }
.card { background:#1e293b; padding:20px; border-radius:12px; margin:10px; display:inline-block; min-width:170px; vertical-align:top; }
.green { color:#22c55e; }
.red { color:#ef4444; }
.yellow { color:#facc15; }
table { width:100%; border-collapse:collapse; margin-top:20px; background:#1e293b; border-radius: 12px; overflow:hidden; }
th,td { padding:10px; border-bottom:1px solid #334155; text-align:left; }
th { background:#111827; color:#cbd5e1; }
button { padding:10px 18px; margin:6px; border-radius:8px; border:none; cursor:pointer; font-weight:bold; }
input, select { padding:8px; margin:4px; border-radius:6px; border:1px solid #334155; }
.buy { background:#22c55e; }
.sell { background:#ef4444; color:white; }
.action { background:#38bdf8; }
.warning { background:#f59e0b; }
.panel { background:#1e293b; padding:20px; border-radius:12px; margin-top:20px; }
a { color:#38bdf8; }
</style>
</head>
<body>

<h1>🚀 Harold AI V12 Paper Trading Dashboard</h1>
<p class="sub">Paper Mode | Auto-refreshes every 60 seconds</p>

<button class="action" onclick="location.href='/autopilot'">Run AutoPilot</button>
<button class="warning" onclick="location.href='/autopilot-force'">Force AutoPilot Test</button>
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

<div class="panel">
<h2>Manual Trade</h2>
<form action="/paper/trade-form" method="post">
Symbol <input name="symbol" value="AAPL">
Action <select name="action"><option>BUY</option><option>SELL</option></select>
Price <input name="price" value="225">
Confidence <input name="confidence" value="85">
Reason <input name="reason" value="Dashboard Trade">
<button class="buy" type="submit">Submit Trade</button>
</form>
</div>

<div class="panel">
<h2>Reset Paper Account</h2>
<form action="/paper/reset" method="post">
<button class="sell" type="submit">Reset Account</button>
</form>
</div>

<script>
function money(x){ return Number(x || 0).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); }

async function loadDashboard(){
    const p = await fetch('/paper/portfolio').then(r=>r.json());
    const perf = await fetch('/paper/performance').then(r=>r.json());

    const acct = p.account;
    const plClass = acct.total_pl >= 0 ? 'green':'red';

    document.getElementById('cards').innerHTML = `
        <div class="card"><h3>Equity</h3><h2>$${money(acct.equity)}</h2></div>
        <div class="card"><h3>Cash</h3><h2>$${money(acct.cash)}</h2></div>
        <div class="card"><h3>Total P/L</h3><h2 class="${plClass}">$${money(acct.total_pl)}</h2></div>
        <div class="card"><h3>Return</h3><h2>${acct.total_return_pct}%</h2></div>
        <div class="card"><h3>Positions</h3><h2>${acct.open_positions}/${acct.max_open_positions}</h2></div>
        <div class="card"><h3>Trades Today</h3><h2>${acct.trades_today}/${acct.max_trades_per_day}</h2></div>
        <div class="card"><h3>Win Rate</h3><h2>${perf.win_rate}%</h2></div>
        <div class="card"><h3>Profit Factor</h3><h2>${perf.profit_factor ?? 'N/A'}</h2></div>
    `;

    let posHtml = `<tr><th>Symbol</th><th>Qty</th><th>Avg</th><th>Last</th><th>Value</th><th>P/L</th><th>%</th></tr>`;
    if (!p.positions.length) {
        posHtml += `<tr><td colspan="7">No open positions.</td></tr>`;
    }
    p.positions.forEach(x=>{
        posHtml += `<tr>
            <td><b>${x.symbol}</b></td>
            <td>${x.qty}</td>
            <td>$${money(x.avg_price)}</td>
            <td>$${money(x.last_price)}</td>
            <td>$${money(x.market_value)}</td>
            <td class="${x.unrealized_pl >= 0 ? 'green':'red'}">$${money(x.unrealized_pl)}</td>
            <td class="${x.unrealized_pl_pct >= 0 ? 'green':'red'}">${x.unrealized_pl_pct}%</td>
        </tr>`;
    });
    document.getElementById('positions').innerHTML = posHtml;

    let tradeHtml = `<tr><th>Time</th><th>Symbol</th><th>Action</th><th>Qty</th><th>Price</th><th>P/L</th><th>Reason</th></tr>`;
    if (!p.recent_trades.length) {
        tradeHtml += `<tr><td colspan="7">No trades yet.</td></tr>`;
    }
    p.recent_trades.forEach(t=>{
        tradeHtml += `<tr>
            <td>${t.time}</td>
            <td><b>${t.symbol}</b></td>
            <td class="${t.action === 'BUY' ? 'green':'red'}">${t.action}</td>
            <td>${t.qty}</td>
            <td>$${money(t.price)}</td>
            <td class="${t.realized_pl >= 0 ? 'green':'red'}">$${money(t.realized_pl)}</td>
            <td>${t.reason}</td>
        </tr>`;
    });
    document.getElementById('trades').innerHTML = tradeHtml;

    document.getElementById('performance').innerHTML = `
        <tr><th>Total Trades</th><td>${perf.total_trades}</td></tr>
        <tr><th>Closed Trades</th><td>${perf.closed_trades}</td></tr>
        <tr><th>Winning Trades</th><td>${perf.winning_trades}</td></tr>
        <tr><th>Losing Trades</th><td>${perf.losing_trades}</td></tr>
        <tr><th>Realized P/L</th><td class="${perf.realized_pl >= 0 ? 'green':'red'}">$${money(perf.realized_pl)}</td></tr>
        <tr><th>Average Win</th><td>$${money(perf.avg_win)}</td></tr>
        <tr><th>Average Loss</th><td>$${money(perf.avg_loss)}</td></tr>
        <tr><th>Profit Factor</th><td>${perf.profit_factor ?? 'N/A'}</td></tr>
        <tr><th>Take Profit %</th><td>${perf.take_profit_pct ?? 'N/A'}</td></tr>
        <tr><th>Stop Loss %</th><td>${perf.stop_loss_pct ?? 'N/A'}</td></tr>
    `;
}
loadDashboard();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

