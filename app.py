from flask import Flask, jsonify, request
from paper_engine import portfolio, place_paper_trade

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "Harold AI V10.1 running",
        "mode": "PAPER",
        "portfolio_url": "/paper/portfolio"
    })

@app.route("/paper/portfolio")
def paper_portfolio():
    return jsonify(portfolio())

@app.route("/paper/trade", methods=["POST"])
def paper_trade():
    data = request.get_json()
    return jsonify(place_paper_trade(
        symbol=data.get("symbol"),
        action=data.get("action"),
        price=float(data.get("price")),
        confidence=float(data.get("confidence")),
        reason=data.get("reason", "test")
    ))
