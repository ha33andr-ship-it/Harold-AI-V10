from fastapi import FastAPI
from pydantic import BaseModel
from paper_engine import place_paper_trade, portfolio, init_db

app = FastAPI(title="Harold AI V10.1 Paper Trading")

init_db()


class PaperTradeRequest(BaseModel):
    symbol: str
    action: str
    price: float
    confidence: float
    reason: str = "Harold AI signal"


@app.get("/")
def home():
    return {
        "status": "Harold AI V10.1 running",
        "mode": "PAPER"
    }


@app.post("/paper/trade")
def paper_trade(req: PaperTradeRequest):
    return place_paper_trade(
        symbol=req.symbol,
        action=req.action,
        price=req.price,
        confidence=req.confidence,
        reason=req.reason
    )


@app.get("/paper/portfolio")
def paper_portfolio():
    return portfolio()
