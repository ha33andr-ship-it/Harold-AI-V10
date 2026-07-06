from flask import Flask, render_template, request, jsonify
from paper_engine import init_db, portfolio, place_paper_trade

app = Flask(__name__)
init_db()

@app.route("/")
def dashboard():
    return render_template("dashboard.html", portfolio=portfolio())

@app.route("/paper/portfolio")
def paper_portfolio():
    return jsonify(portfolio())

@app.route("/paper/trade", methods=["POST"])
def paper_trade():
    data = request.get_json()
    result = place_paper_trade(
        symbol=data.get("symbol"),
        action=data.get("action"),
        price=float(data.get("price")),
        confidence=float(data.get("confidence")),
        reason=data.get("reason", "Harold AI signal")
    )
    return jsonify(result)

@app.route("/trades")
def trades():
    return render_template("trades.html", portfolio=portfolio())

@app.route("/portfolio")
def portfolio_page():
    return render_template("portfolio.html", portfolio=portfolio())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
