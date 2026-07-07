from flask import Flask, jsonify, request
from paper_engine import portfolio, place_paper_trade, performance, reset_paper_account

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "status": "Harold AI V10.3 running",
        "mode": "PAPER",
        "dashboard": "/dashboard",
        "portfolio_url": "/paper/portfolio",
        "performance_url": "/paper/performance"
    })


@app.route("/paper/portfolio")
def paper_portfolio():
    return jsonify(portfolio())


@app.route("/paper/performance")
def paper_performance():
    return jsonify(performance())


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
        <title>Harold AI V10.3</title>
    </head>

    <body style="font-family:Arial;padding:40px;">

        <h1>🚀 Harold AI V10.3</h1>
        <h2>Paper Trading Dashboard</h2>

        <p><a href="/paper/portfolio">View Portfolio JSON</a></p>
        <p><a href="/paper/performance">View Performance JSON</a></p>

        <hr>

        <h2>Execute Paper Trade</h2>

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

        <h2>Reset Paper Account</h2>
        <form action="/paper/reset" method="post">
            <button type="submit">Reset Account</button>
        </form>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
