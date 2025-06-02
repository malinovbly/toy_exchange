# src/utils.py
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, and_
from sqlalchemy.future import select
from datetime import datetime
from typing import Optional, Union, List

from src.models.balance import BalanceModel
from src.models.instrument import InstrumentModel
from src.models.order import OrderModel
from src.models.transaction import TransactionModel
from src.models.user import UserModel
from src.database.database import get_db
from src.security import api_key_header
from src.schemas.schemas import (NewUser,
                                 Level,
                                 Instrument,
                                 Body_deposit_api_v1_admin_balance_deposit_post,
                                 Body_withdraw_api_v1_admin_balance_withdraw_post,
                                 LimitOrderBody,
                                 MarketOrderBody,
                                 OrderStatus,
                                 Direction
                                 )


# users
async def register_new_user(user: NewUser, db: AsyncSession = Depends(get_db)):
    user_id = uuid4()
    token = uuid4()

    db_user = UserModel(
        id=user_id,
        name=user.name,
        role="USER",
        api_key=token
    )
    db.add(db_user)

    await db.commit()
    await db.refresh(db_user)

    return db_user


def get_api_key(authorization: str):
    token = authorization.split(' ')
    if len(token) == 1:
        raise HTTPException(status_code=404, detail="Invalid Authorization")
    else:
        return token[1]


async def check_username(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).filter_by(name=username))
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).filter_by(id=user_id))
    return result.scalar_one_or_none()


async def get_user_by_api_key(api_key: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).filter_by(api_key=api_key))
    return result.scalar_one_or_none()


async def check_user_is_admin(authorization: UUID = Depends(api_key_header), db: AsyncSession = Depends(get_db)):
    auth_user = await get_user_by_api_key(authorization, db)
    if (auth_user is None) or not (auth_user.role == "ADMIN"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


async def delete_user_by_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_id(user_id, db)

    if db_user is None:
        raise HTTPException(status_code=404, detail="Not Found")

    await db.delete(db_user)
    await db.commit()

    return db_user


# instruments
async def check_instrument(instrument: Instrument, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel).filter_by(name=instrument.name))
    db_instrument = result.scalar_one_or_none()
    if db_instrument is None:
        result = await db.execute(select(InstrumentModel).filter_by(ticker=instrument.ticker))
        db_instrument = result.scalar_one_or_none()
    return db_instrument


async def get_all_instruments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel))
    return list(result.scalars().all())


async def get_instrument_by_ticker(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel).filter_by(ticker=ticker))
    return result.scalar_one_or_none()


async def create_instrument(instrument: Instrument, db: AsyncSession = Depends(get_db)):
    existing = await check_instrument(instrument, db)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Instrument already exists")

    db_instrument = InstrumentModel(
        name=instrument.name,
        ticker=instrument.ticker
    )
    db.add(db_instrument)
    await db.commit()
    await db.refresh(db_instrument)


async def delete_instrument_by_ticker(ticker: str, db: AsyncSession = Depends(get_db)):
    if ticker == "RUB":
        raise HTTPException(status_code=403, detail="Forbidden to remove the RUB ticker")

    db_instrument = await get_instrument_by_ticker(ticker, db)
    if db_instrument is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} Not Found")

    await db.execute(delete(BalanceModel).where(BalanceModel.instrument_ticker == ticker))

    await db.delete(db_instrument)
    await db.commit()


# balances
async def get_balances_by_user_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BalanceModel).filter_by(user_id=user_id))
    db_balances = list(result.scalars().all())
    balances = {b.instrument_ticker: b.amount for b in db_balances}
    return balances


async def check_balance_record(user_id: UUID, ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BalanceModel)
        .where(
            and_(
                BalanceModel.user_id == user_id,
                BalanceModel.instrument_ticker == ticker
            )
        )
    )
    return result.scalar_one_or_none()


async def user_balance_deposit(request: Body_deposit_api_v1_admin_balance_deposit_post, db: AsyncSession = Depends(get_db)):
    if await get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if await get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail="Ticker Not Found")

    record = await check_balance_record(user_id=request.user_id, ticker=request.ticker, db=db)
    if record is not None:
        new_amount = record.amount + request.amount
        updated_record = (
            update(BalanceModel)
            .where(
                and_(
                    BalanceModel.user_id == record.user_id,
                    BalanceModel.instrument_ticker == record.instrument_ticker
                )
            )
            .values(amount=new_amount)
        )
        await db.execute(updated_record)
        await db.commit()
        await db.refresh(record)
    else:
        new_record = BalanceModel(
            user_id=request.user_id,
            instrument_ticker=request.ticker,
            amount=request.amount
        )
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)


async def user_balance_withdraw(request: Body_withdraw_api_v1_admin_balance_withdraw_post, db: AsyncSession = Depends(get_db)):
    if await get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if await get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail="Ticker Not Found")

    record = await check_balance_record(user_id=request.user_id, ticker=request.ticker, db=db)
    if record is None:
        raise HTTPException(status_code=400, detail="Bad Request")
    else:
        new_amount = record.amount - request.amount
        if new_amount >= 0:
            updated_record = (
                update(BalanceModel)
                .where(
                    and_(
                        BalanceModel.user_id == record.user_id,
                        BalanceModel.instrument_ticker == record.instrument_ticker
                    )
                )
                .values(amount=new_amount)
            )
            await db.execute(updated_record)
            await db.commit()
        else:
            raise HTTPException(status_code=403, detail="Insufficient Funds")


# orderbook
async def get_bids(ticker: str, limit: int, db: AsyncSession = Depends(get_db)):
    db_asks = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == Direction.SELL,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price is not None
            )
        )
        .order_by(OrderModel.price.asc())
        .limit(limit)
    )
    return list(db_asks.scalars().all())


async def get_asks(ticker: str, limit: int, db: AsyncSession = Depends(get_db)):
    db_asks = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == Direction.SELL,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price is not None
            )
        )
        .order_by(OrderModel.price.asc())
        .limit(limit)
    )
    return list(db_asks.scalars().all())


def aggregate_orders(orders: List[OrderModel], is_bid: bool) -> List[Level]:
    levels = {}
    for order in orders:
        remaining_qty = order.qty - order.filled
        if remaining_qty <= 0:
            continue
        levels[order.price] = levels.get(order.price, 0) + remaining_qty

    return sorted(
        [Level(price=price, qty=qty) for price, qty in levels.items()],
        key=lambda lvl: lvl.price,
        reverse=is_bid
    )


# transactions
async def get_transactions_by_ticker(ticker: str, limit: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TransactionModel)
        .where(TransactionModel.ticker == ticker)
        .order_by(TransactionModel.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def record_transaction(ticker: str, price: int, qty: int, db: AsyncSession = Depends(get_db)):
    transaction = TransactionModel(
        ticker=ticker,
        price=price,
        qty=qty,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)
    await db.commit()


# orders
async def create_order_in_db(order_data: Union[LimitOrderBody, MarketOrderBody], price: int, user_id: UUID,
                             db: AsyncSession = Depends(get_db)):
    db_order = OrderModel(
        id=uuid4(),
        user_id=user_id,
        timestamp=datetime.utcnow(),
        direction=order_data.direction,
        ticker=order_data.ticker,
        qty=order_data.qty,
        status=OrderStatus.NEW,
        price=price,
        filled=0
    )

    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order


async def get_order_by_id(order_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderModel).filter_by(id=order_id))
    return result.scalar_one_or_none()


async def delete_order_by_id(order_id: UUID, db: AsyncSession = Depends(get_db)):
    db_order = await get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    await db.delete(db_order)
    await db.commit()
    return db_order


async def get_orders_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderModel).filter_by(user_id=user_id))
    return list(result.scalars().all())


async def list_all_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderModel))
    return list(result.scalars().all())


async def update_order_status(
        order_id: UUID,
        new_status: OrderStatus,
        filled_qty: Optional[int] = None,
        db: AsyncSession = Depends(get_db)
):
    db_order = await get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")

    db_order.status = new_status
    if filled_qty is not None:
        db_order.filled = filled_qty

    await db.commit()
    await db.refresh(db_order)
    return db_order


async def get_orders_by_ticker(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderModel).filter_by(ticker=ticker))
    return list(result.scalars().all())


async def get_active_orders_by_ticker(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
            )
        )
    )
    return list(result.scalars().all())


async def cancel_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    db_order = await get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")

    if db_order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
        raise HTTPException(
            status_code=400,
            detail="Only NEW or PARTIALLY_EXECUTED orders can be cancelled"
        )

    db_order.status = OrderStatus.CANCELLED

    await db.commit()
    await db.refresh(db_order)
    return db_order


async def update_user_balance(
        user_id: UUID,
        ticker: str,
        amount_change: int,
        direction: Direction = None,
        db: AsyncSession = Depends(get_db)
) -> BalanceModel:
    db_balance = await check_balance_record(user_id, ticker, db)
    if db_balance is None:
        db_balance = BalanceModel(
            user_id=user_id,
            instrument_ticker=ticker,
            amount=0
        )
        db.add(db_balance)

    new_amount = db_balance.amount + amount_change

    # Выдается и при слуаче нехватки баланса юзера, и при случае нехватки баланса другого трейдера
    if new_amount < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance for {ticker}"
        )

    db_balance.amount = new_amount

    await db.commit()
    await db.refresh(db_balance)
    return db_balance


async def process_trade(
    is_buy: bool,
    user_id: UUID,
    counterparty_id: UUID,
    ticker: str,
    trade_qty: int,
    trade_price: int,
    db: AsyncSession = Depends(get_db)
):
    trade_amount = trade_qty * trade_price
    ticker_rub = "RUB"

    if is_buy:
        await update_user_balance(user_id, ticker_rub, -trade_amount, db=db)
        await update_user_balance(user_id, ticker, trade_qty, db=db)
        await update_user_balance(counterparty_id, ticker, -trade_qty, db=db)
        await update_user_balance(counterparty_id, ticker_rub, trade_amount, db=db)
    else:
        await update_user_balance(user_id, ticker, -trade_qty, db=db)
        await update_user_balance(user_id, ticker_rub, trade_amount, db=db)
        await update_user_balance(counterparty_id, ticker_rub, -trade_amount, db=db)
        await update_user_balance(counterparty_id, ticker, trade_qty, db=db)

    await record_transaction(ticker, trade_price, trade_qty, db)


async def update_order_status_and_filled(order: OrderModel, filled_increment: int, db: AsyncSession = Depends(get_db)):
    order.filled += filled_increment
    if order.filled == order.qty:
        order.status = OrderStatus.EXECUTED
    elif order.filled > 0:
        order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        order.status = OrderStatus.NEW

    db.add(order)
    await db.commit()


async def execute_market_order(market_order: OrderModel, db: AsyncSession = Depends(get_db)):
    remaining_qty = market_order.qty
    ticker = market_order.ticker
    direction = market_order.direction
    user_id = market_order.user_id

    is_buy = direction == Direction.BUY
    opposite_direction = Direction.SELL if is_buy else Direction.BUY

    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == opposite_direction,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price is not None
            )
        )
        .order_by(OrderModel.price.asc() if is_buy else OrderModel.price.desc())
    )
    limit_orders = list(result.scalars().all())

    total_filled = 0

    for limit_order in limit_orders:
        available_qty = limit_order.qty - limit_order.filled
        if available_qty <= 0:
            continue

        trade_qty = min(remaining_qty, available_qty)
        trade_price = limit_order.price
        seller_id = limit_order.user_id

        await process_trade(is_buy, user_id, seller_id, ticker, trade_qty, trade_price, db)
        await update_order_status_and_filled(limit_order, trade_qty, db)

        remaining_qty -= trade_qty
        total_filled += trade_qty

        if remaining_qty == 0:
            break

    if total_filled == 0:
        raise HTTPException(status_code=400, detail="No matching orders in the orderbook")

    # обновляем сам рыночный ордер
    market_order.filled = total_filled
    market_order.status = (
        OrderStatus.EXECUTED
        if total_filled == market_order.qty
        else OrderStatus.PARTIALLY_EXECUTED
    )

    db.add(market_order)
    await db.commit()
    await db.refresh(market_order)
    return market_order


async def execute_limit_order(limit_order: OrderModel, db: AsyncSession = Depends(get_db)):
    remaining_qty = limit_order.qty
    ticker = limit_order.ticker
    direction = limit_order.direction
    user_id = limit_order.user_id

    is_buy = direction == Direction.BUY
    opposite_direction = Direction.SELL if is_buy else Direction.BUY

    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == opposite_direction,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price is not None,
                OrderModel.price <= limit_order.price if is_buy else OrderModel.price >= limit_order.price
            )
        )
        .order_by(OrderModel.price.asc() if is_buy else OrderModel.price.desc())
    )
    matching_orders = list(result.scalars().all())

    total_filled = 0

    for match in matching_orders:
        available_qty = match.qty - match.filled
        if available_qty <= 0:
            continue

        trade_qty = min(remaining_qty, available_qty)
        trade_price = match.price
        counterparty_id = match.user_id

        await process_trade(is_buy, user_id, counterparty_id, ticker, trade_qty, trade_price, db)
        await update_order_status_and_filled(match, trade_qty, db)

        remaining_qty -= trade_qty
        total_filled += trade_qty

        if remaining_qty == 0:
            break

    # Обновление исходной лимитной заявки
    limit_order.filled = total_filled
    if total_filled == 0:
        limit_order.status = OrderStatus.NEW  
    elif total_filled < limit_order.qty:
        limit_order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        limit_order.status = OrderStatus.EXECUTED

    db.add(limit_order)
    await db.commit()
    await db.refresh(limit_order)

    return limit_order
