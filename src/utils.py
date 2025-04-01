

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src import models  # Исправленный импорт
import secrets

# ... (остальной код)

def simulate_market_price(instrument_id: int, db: Session):
    """Simulates a simple market price.  Replace with real-world data feed."""
    instrument = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instrument:
        return None
    # Very basic price generation (could use a more sophisticated model)
    trades = db.query(models.Trade).filter(models.Trade.order.has(instrument_id=instrument_id)).all()
    if not trades:
        return 100.0  # Default starting price
    last_trade_price = trades[-1].price
    change = secrets.choice([-1, 0, 1]) * secrets.uniform(0, 1)  # Up, down, or stay
    return round(last_trade_price + change, 2)

def execute_market_order(order: models.Order, db: Session):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == order.instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    user = order.user
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Get current market price
    market_price = simulate_market_price(order.instrument_id, db)
    if market_price is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve market price")

    # Check if user has enough balance
    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user.id, models.Balance.instrument_id == order.instrument_id)
        .first()
    )

    if balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance for instrument")
    required_funds = order.quantity * market_price
    if balance.amount < required_funds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

    # Execute the trade
    trade = models.Trade(order_id=order.id, price=market_price, quantity=order.quantity)
    db.add(trade)

    # Update balances
    balance.amount -= required_funds
    db.add(balance)

    order.status = models.OrderStatus.filled
    db.add(order)
    db.commit()
    db.refresh(order)
    db.refresh(balance)
    return order

def execute_limit_order(order: models.Order, db: Session):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == order.instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    user = order.user
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Get order price
    order_price = order.price
    if order_price is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve limit order price")
    # Check if user has enough balance
    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user.id, models.Balance.instrument_id == order.instrument_id)
        .first()
    )

    if balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance for instrument")
    required_funds = order.quantity * order_price
    if balance.amount < required_funds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

    # Execute the trade if market price meets limit order
    market_price = simulate_market_price(order.instrument_id, db)
    if market_price is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve market price")
    if market_price >= order_price:  # Assuming buy order
        trade = models.Trade(order_id=order.id, price=order_price, quantity=order.quantity)
        db.add(trade)

        # Update balances
        balance.amount -= required_funds
        db.add(balance)

        order.status = models.OrderStatus.filled
        db.add(order)
        db.commit()
        db.refresh(order)
        db.refresh(balance)
        return order
    else:
        order.status = models.OrderStatus.open
        db.add(order)
        db.commit()
        db.refresh(order)
        return order