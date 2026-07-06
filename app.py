from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Harold AI V10 Online!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Received Alert:")
    print(data)

    return jsonify({
        "status": "success",
        "message": "TradingView alert received",
        "data": data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
