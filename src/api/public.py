# src/api/public.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.schemas.schemas import NewUser, User, Instrument, L2OrderBook, Transaction
from src.utils import (
    check_username,
    get_all_instruments,
    get_instrument_by_ticker,
    register_new_user,
    aggregate_orders,
    get_bids,
    get_asks,
    get_transactions_by_ticker,
    check_instrument
)
from src.database.database import get_db


summary_tags = {
    "register": "Register",
    "list_instruments": "List Instruments",
    "get_orderbook": "Get Orderbook",
    "get_transaction_history": "Get Transaction History"
}

router = APIRouter()


@router.post(
    path="/api/v1/public/register",
    tags=["public"],
    response_model=User,
    summary=summary_tags["register"]
)
async def register(
        user: NewUser,
        db: AsyncSession = Depends(get_db)
):
    if await check_username(user.name, db) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    return await register_new_user(user, db)


@router.get(
    path="/api/v1/public/instrument",
    tags=["public"],
    response_model=List[Instrument],
    summary=summary_tags["list_instruments"]
)
async def list_instruments(db: AsyncSession = Depends(get_db)):
    return await get_all_instruments(db)


@router.get(
    path="/api/v1/public/orderbook/{ticker}",
    tags=["public"],
    response_model=L2OrderBook,
    summary=summary_tags["get_orderbook"]
)
async def get_orderbook(
        ticker: str,
        limit: int = Query(10, ge=1, le=25),
        db: AsyncSession = Depends(get_db)
):
    instrument = await get_instrument_by_ticker(ticker, db)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' Not Found")

    bids = await get_bids(ticker, limit, db)
    asks = await get_asks(ticker, limit, db)

    bid_levels = aggregate_orders(bids, is_bid=True)
    ask_levels = aggregate_orders(asks, is_bid=False)

    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)


@router.get(
    path="/api/v1/public/transactions/{ticker}",
    tags=["public"],
    response_model=List[Transaction],
    summary=summary_tags["get_transaction_history"]
)
async def get_transaction_history(
    ticker: str,
    limit: int = Query(10, ge=1, le=100), 
    db: AsyncSession = Depends(get_db)
):
    instrument = await get_instrument_by_ticker(ticker, db)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    transactions = await get_transactions_by_ticker(ticker, limit, db)
    if (transactions is None) or (len(transactions) == 0):
        raise HTTPException(status_code=404, detail=f"No transactions found for ticker {ticker}")

    return [
        Transaction(
            ticker=tx.ticker,
            amount=tx.qty,
            price=tx.price,
            timestamp=tx.timestamp
        )
        for tx in transactions
    ]
