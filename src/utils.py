# src/utils.py
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, and_, asc, desc
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import Union, List, Optional

from src.models.balance import BalanceModel
from src.models.instrument import InstrumentModel
from src.models.order import OrderModel
from src.models.transaction import TransactionModel
from src.models.user import UserModel
from src.database.database import get_db
from src.security import api_key_header
from src.schemas.schemas import (
    NewUser,
    Level,
    Instrument,
    Body_deposit_api_v1_admin_balance_deposit_post,
    Body_withdraw_api_v1_admin_balance_withdraw_post,
    LimitOrderBody,
    LimitOrder,
    MarketOrderBody,
    MarketOrder,
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
    if (auth_user is None) or (auth_user.role != "ADMIN"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


async def delete_user_by_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_id(user_id, db)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User Not Found")

    await db.delete(db_user)
    await db.commit()

    return db_user


# instruments
async def get_all_instruments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel))
    return list(result.scalars().all())


async def get_instrument_by_ticker(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel).filter_by(ticker=ticker))
    return result.scalar_one_or_none()


async def check_instrument(instrument: Instrument, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InstrumentModel).filter_by(name=instrument.name))
    db_instrument = result.scalar_one_or_none()
    if db_instrument is None:
        result = await db.execute(select(InstrumentModel).filter_by(ticker=instrument.ticker))
        db_instrument = result.scalar_one_or_none()
    return db_instrument


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
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' Not Found")

    await db.execute(delete(BalanceModel).filter_by(instrument_ticker=ticker))

    await db.delete(db_instrument)
    await db.commit()


# balances
async def get_balances_by_user_id(user_id: UUID, db: AsyncSession):
    result = await db.execute(select(BalanceModel).filter_by(user_id=user_id))
    db_balances = list(result.scalars().all())
    balances = {b.instrument_ticker: b.amount for b in db_balances}
    return balances


async def check_balance_record(user_id: UUID, ticker: str, db: AsyncSession):
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


async def user_balance_deposit(request: Body_deposit_api_v1_admin_balance_deposit_post, db: AsyncSession):
    if await get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if await get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{request.ticker}' Not Found")

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


async def user_balance_withdraw(request: Body_withdraw_api_v1_admin_balance_withdraw_post, db: AsyncSession):
    if await get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if await get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{request.ticker}' Not Found")

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
        

async def get_available_balance(user_id: UUID, ticker: str, db: AsyncSession) -> int:
    rec = await check_balance_record(user_id, ticker, db)
    return 0 if rec is None else rec.amount - rec.reserved


async def reserve_balance(user_id: UUID, ticker: str, delta: int, db: AsyncSession):
    rec = await check_balance_record(user_id, ticker, db)
    if rec is None:
        raise HTTPException(status_code=400, detail="No Balance Record")

    if delta > 0 and rec.reserved + delta > rec.amount:
        raise HTTPException(status_code=400, detail="Insufficient free balance")
    if delta < 0 and rec.reserved + delta < 0:
        raise HTTPException(status_code=400, detail="Can't de-reserve more than reserved")

    rec.reserved += delta
    db.add(rec)


# orderbook
async def get_bids(ticker: str, limit: int, db: AsyncSession):
    db_asks = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == Direction.BUY,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price is not None
            )
        )
        .order_by(asc(OrderModel.price))
        .limit(limit)
    )
    return list(db_asks.scalars().all())


async def get_asks(ticker: str, limit: int, db: AsyncSession):
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
        .order_by(asc(OrderModel.price))
        .limit(limit)
    )
    return list(db_asks.scalars().all())


def aggregate_orders(orders: List[OrderModel], is_bid: bool) -> List[Level]:
    levels = dict()
    for order in orders:
        if order.type == "MARKET":
            remaining_qty = order.qty
        else:
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
async def get_transactions_by_ticker(ticker: str, limit: int, db: AsyncSession):
    result = await db.execute(
        select(TransactionModel)
        .filter_by(ticker=ticker)
        .order_by(desc(TransactionModel.timestamp))
        .limit(limit)
    )
    return list(result.scalars().all())


async def record_transaction(ticker: str, price: int, qty: int, db: AsyncSession):
    db_transaction = TransactionModel(
        ticker=ticker,
        price=price,
        qty=qty,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(db_transaction)


# orders
async def create_order_in_db(order_data: Union[LimitOrderBody, MarketOrderBody],
                             price: Optional[int], user_id: UUID, db: AsyncSession):
    order_dict = {
        "id": uuid4(),
        "status": OrderStatus.NEW,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc),
        "direction": order_data.direction,
        "ticker": order_data.ticker,
        "qty": order_data.qty,
        "price": price
    }

    if isinstance(order_data, MarketOrderBody):
        order_dict["filled"] = -1
        order_dict["type"] = "MARKET"
    elif isinstance(order_data, LimitOrderBody):
        order_dict["filled"] = 0
        order_dict["type"] = "LIMIT"

    db_order = OrderModel(**order_dict)
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order


def create_order_dict(order: OrderModel):
    order_dict = {
        "id": order.id,
        "status": order.status,
        "user_id": order.user_id,
        "timestamp": order.timestamp
    }

    if order.type == "MARKET":
        order_body = MarketOrderBody(
            direction=order.direction,
            ticker=order.ticker,
            qty=order.qty
        )
        order_dict["body"] = order_body
        return MarketOrder(**order_dict)

    elif order.type == "LIMIT":
        order_body = LimitOrderBody(
            direction=order.direction,
            ticker=order.ticker,
            qty=order.qty,
            price=order.price
        )
        order_dict["body"] = order_body
        order_dict["filled"] = order.filled
        return LimitOrder(**order_dict)


async def get_order_by_id(order_id: UUID, db: AsyncSession):
    result = await db.execute(select(OrderModel).filter_by(id=order_id))
    return result.scalar_one_or_none()


async def get_orders_by_user(user_id: UUID, db: AsyncSession):
    result = await db.execute(select(OrderModel).filter_by(user_id=user_id))
    return list(result.scalars().all())


async def get_orders_by_ticker(ticker: str, db: AsyncSession):
    result = await db.execute(select(OrderModel).filter_by(ticker=ticker))
    return list(result.scalars().all())


async def get_active_orders_by_ticker(ticker: str, db: AsyncSession):
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


async def update_user_balance(
        user_id: UUID,
        ticker: str,
        amount_change: int,
        db: AsyncSession) -> BalanceModel:
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
        raise HTTPException(status_code=400, detail=f"Insufficient balance for {ticker}")

    db_balance.amount = new_amount
    db.add(db_balance)
    return db_balance


async def process_trade(
    is_buy: bool,
    user_id: UUID,
    counterparty_id: UUID,
    ticker: str,
    trade_qty: int,
    trade_price: int,
    db: AsyncSession
):
    trade_amount = trade_qty * trade_price
    ticker_rub = "RUB"

    if is_buy:
        # Снимаем резерв со стороны покупателя (RUB)
        await reserve_balance(user_id, ticker_rub, -trade_amount, db)

        await update_user_balance(user_id, ticker_rub, -trade_amount, db=db)
        await update_user_balance(user_id, ticker, trade_qty, db=db)
        await update_user_balance(counterparty_id, ticker, -trade_qty, db=db)
        await update_user_balance(counterparty_id, ticker_rub, trade_amount, db=db)

    else:
        # Снимаем резерв со стороны продавца (актив)
        await reserve_balance(user_id, ticker, -trade_qty, db)

        await update_user_balance(user_id, ticker, -trade_qty, db=db)
        await update_user_balance(user_id, ticker_rub, trade_amount, db=db)
        await update_user_balance(counterparty_id, ticker_rub, -trade_amount, db=db)
        await update_user_balance(counterparty_id, ticker, trade_qty, db=db)

    await record_transaction(ticker, trade_price, trade_qty, db)


async def update_order_status_and_filled(order: OrderModel, filled_increment: int, db: AsyncSession):
    order.filled += filled_increment
    if order.filled == order.qty:
        order.status = OrderStatus.EXECUTED
    elif order.filled > 0:
        order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        order.status = OrderStatus.NEW
    db.add(order)


async def execute_market_order(market_order: OrderModel, db: AsyncSession):
    remaining_qty = market_order.qty
    ticker = market_order.ticker
    direction = market_order.direction
    user_id = market_order.user_id

    is_buy = direction == Direction.BUY
    opposite_direction = Direction.SELL if is_buy else Direction.BUY
    ticker_rub = "RUB"

    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == opposite_direction,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price.isnot(None)
            )
        )
        .order_by(asc(OrderModel.price) if is_buy else desc(OrderModel.price))
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

        counterparty_ticker_balance = await check_balance_record(seller_id, ticker, db)
        counterparty_rub_balance = await check_balance_record(seller_id, ticker_rub, db)

        if counterparty_ticker_balance is None or (
            (is_buy and counterparty_ticker_balance.amount < trade_qty) or
            (not is_buy and counterparty_rub_balance.amount < trade_qty * trade_price)
        ):
            continue

        await process_trade(is_buy, user_id, seller_id, ticker, trade_qty, trade_price, db)
        await update_order_status_and_filled(limit_order, trade_qty, db)

        remaining_qty -= trade_qty
        total_filled += trade_qty

        if remaining_qty == 0:
            break

    if total_filled < market_order.qty:
        raise HTTPException(status_code=400, detail="Not enough liquidity to fill market order")

    market_order.status = OrderStatus.EXECUTED
    return market_order


async def execute_limit_order(limit_order: OrderModel, db: AsyncSession):
    remaining_qty = limit_order.qty - limit_order.filled
    ticker = limit_order.ticker
    direction = limit_order.direction
    user_id = limit_order.user_id

    is_buy = direction == Direction.BUY
    opposite_direction = Direction.SELL if is_buy else Direction.BUY
    ticker_rub = "RUB"

    price_condition = OrderModel.price <= limit_order.price if is_buy else OrderModel.price >= limit_order.price
    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.ticker == ticker,
                OrderModel.direction == opposite_direction,
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.price.isnot(None),
                price_condition
            )
        )
        .order_by(asc(OrderModel.price) if is_buy else desc(OrderModel.price))
    )
    matching_orders = list(result.scalars().all())

    total_filled = 0
    for match in matching_orders:
        available_qty = match.qty - match.filled
        if available_qty <= 0:
            continue

        counterparty_id = match.user_id 

        trade_qty = min(remaining_qty, available_qty)
        trade_price = match.price

        counterparty_ticker_balance = await check_balance_record(counterparty_id, ticker, db)
        counterparty_rub_balance = await check_balance_record(counterparty_id, ticker_rub, db)

        if counterparty_ticker_balance is None or (
                (is_buy and counterparty_ticker_balance.amount < trade_qty) or
                (not is_buy and counterparty_rub_balance.amount < trade_qty * trade_price)
        ):
            continue

        await process_trade(is_buy, user_id, counterparty_id, ticker, trade_qty, trade_price, db)
        await update_order_status_and_filled(match, trade_qty, db)

        remaining_qty -= trade_qty
        total_filled += trade_qty

        if remaining_qty == 0:
            break

    # Обновление исходной лимитной заявки
    limit_order.filled += total_filled

    if limit_order.filled == 0:
        limit_order.status = OrderStatus.NEW
    elif limit_order.filled < limit_order.qty:
        limit_order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        limit_order.status = OrderStatus.EXECUTED

    db.add(limit_order)
    return limit_order
