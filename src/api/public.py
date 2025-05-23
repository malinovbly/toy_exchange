# src/api/public.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from src.models.order import OrderModel, OrderStatus, Direction
from src.models.instrument import InstrumentModel
from src.models.transaction import TransactionModel
from src.schemas.schemas import NewUser, User, Instrument, L2OrderBook, Transaction
from src.utils import (check_username,
                       get_all_instruments,
                       register_new_user,
                       aggregate_orders)
from src.database.database import get_db


summary_tags = {
    "register": "Register",
    "list_instruments": "List Instruments",
    "get_orderbook": "Get Orderbook",
    "get_transaction_history": "Get Transaction History"
}

router = APIRouter()


@router.post("/api/v1/public/register", tags=["public"], response_model=User, summary=summary_tags["register"])
def register(user: NewUser, db: Session = Depends(get_db)):
    if check_username(user.name, db) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    return register_new_user(user, db)


@router.get(path="/api/v1/public/instrument", tags=["public"], response_model=List[Instrument], summary=summary_tags["list_instruments"])
def list_instruments(db: Session = Depends(get_db)):
    return get_all_instruments(db)


@router.get(
    "/api/v1/public/orderbook/{ticker}",
    tags=["public"],
    response_model=L2OrderBook,
    summary="Get Orderbook"
)
def get_orderbook(
    ticker: str,
    limit: int = Query(10, ge=1, le=25),
    db: Session = Depends(get_db)
):
    bids = db.query(OrderModel).filter(
        OrderModel.ticker == ticker,
        OrderModel.direction == Direction.BUY,
        OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
        OrderModel.price != None
    ).order_by(OrderModel.price.desc()).limit(limit).all()

    asks = db.query(OrderModel).filter(
        OrderModel.ticker == ticker,
        OrderModel.direction == Direction.SELL,
        OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
        OrderModel.price != None
    ).order_by(OrderModel.price.asc()).limit(limit).all()

    bid_levels = aggregate_orders(bids)
    ask_levels = aggregate_orders(asks)

    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)


@router.get(
    path="/api/v1/public/transactions/{ticker}", 
    tags=["public"], 
    response_model=List[Transaction],
    summary="Get transaction history"
)
def get_transaction_history(
    ticker: str,
    limit: int = Query(10, ge=1, le=100), 
    db: Session = Depends(get_db)
):
    instrument = db.query(InstrumentModel).filter(
        InstrumentModel.ticker == ticker
    ).first()
    if not instrument:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker} not found"
        )

    transactions = db.query(TransactionModel).filter(
        TransactionModel.ticker == ticker
    ).order_by(TransactionModel.timestamp.desc()).limit(limit).all()

    if not transactions:
        raise HTTPException(
            status_code=404,
            detail=f"No transactions found for ticker {ticker}"
        )

    return [
        Transaction(
            ticker=tx.ticker,
            amount=tx.qty,
            price=tx.price,
            timestamp=tx.timestamp
        )
        for tx in transactions
    ]

