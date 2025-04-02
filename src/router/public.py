from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src import models, schemas, security  # Исправленный импорт
from src.database import get_db
from src import utils
from typing import List, Dict  # Импортируем Dict
router = APIRouter()


@router.get("/marketdata/{instrument_id}/book", response_model=Dict[str, List[Dict[str, float]]]) # Simplified: Bids/Asks
async def get_order_book(instrument_id: int, db: Session = Depends(get_db)):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    # Simulate order book data (replace with real order book logic)
    bids = []
    asks = []

    for order in db.query(models.Order).filter(
            models.Order.instrument_id == instrument_id,
            models.Order.status == models.OrderStatus.open,
            models.Order.order_type == models.OrderType.limit
    ).all():
        if order.price is not None:
            if order.quantity > 0:  # Assuming bids
                bids.append({"price": order.price, "quantity": order.quantity})
            elif order.quantity < 0:  # Assuming asks
                asks.append({"price": order.price, "quantity": abs(order.quantity)})

    # Sort bids and asks (highest bid, lowest ask)
    bids.sort(key=lambda x: x["price"], reverse=True)
    asks.sort(key=lambda x: x["price"])

    return {"bids": bids, "asks": asks}

@router.get("/trades", response_model=List[schemas.TradeRead])
async def get_trade_history(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    trades = db.query(models.Trade).join(models.Order).filter(models.Order.user_id == user.id).all()
    return [schemas.TradeRead(price=trade.price, quantity=trade.quantity, timestamp=trade.timestamp, instrument_ticker=trade.order.instrument.ticker) for trade in trades]

@router.get("/candles/{instrument_id}", response_model=List[schemas.CandleData])
async def get_candles(instrument_id: int,  user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instrument:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    trades = db.query(models.Trade).join(models.Order).filter(models.Order.instrument_id == instrument_id).order_by(models.Trade.timestamp).all()

    candles: List[schemas.CandleData] = []
    if not trades:
        return []

    # Group trades by 1-minute intervals (example; adjust for desired interval)
    time_interval = 60  # seconds (1 minute)
    first_trade_time = trades[0].timestamp
    current_candle_start = first_trade_time.replace(microsecond=0, second=0)
    open_price = trades[0].price
    high_price = trades[0].price
    low_price = trades[0].price
    volume = 0
    current_trades = []

    for trade in trades:
        if (trade.timestamp - current_candle_start).total_seconds() < time_interval:
            # Add trade to current candle
            high_price = max(high_price, trade.price)
            low_price = min(low_price, trade.price)
            volume += trade.quantity
            current_trades.append(trade)
        else:
            # Close current candle and create new one
            if current_trades:
                candles.append(
                    schemas.CandleData(
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=current_trades[-1].price,  # Last trade's price
                        volume=volume,
                        timestamp=current_candle_start,
                    )
                )

            # Start new candle
            current_candle_start = trade.timestamp.replace(microsecond=0, second=0)
            open_price = trade.price
            high_price = trade.price
            low_price = trade.price
            volume = trade.quantity
            current_trades = [trade]

    # Handle the last candle
    if current_trades:
        candles.append(
            schemas.CandleData(
                open=open_price,
                high=high_price,
                low=low_price,
                close=current_trades[-1].price,  # Last trade's price
                volume=volume,
                timestamp=current_candle_start,
            )
        )

    return candles