# src/utils.py
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, asc, desc
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
    Direction,
    UserRole
)


def get_api_key(authorization: str):
    token = authorization.split(' ')
    if len(token) == 1:
        raise HTTPException(status_code=404, detail="Invalid Authorization")
    else:
        return token[1]


# users
async def register_new_user(user: NewUser, db: AsyncSession = Depends(get_db)):
    user_id = uuid4()
    token = uuid4()
    db_user = UserModel(
        id=user_id,
        name=user.name,
        role=UserRole.USER,
        api_key=token
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


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
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if auth_user.role != UserRole.ADMIN:
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
        record.amount += request.amount
    else:
        record = BalanceModel(
            user_id=request.user_id,
            instrument_ticker=request.ticker,
            amount=request.amount
        )
    db.add(record)
    await db.commit()
    await db.refresh(record)


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
            record.amount = new_amount
            db.add(record)
            await db.commit()
            await db.refresh(record)
        else:
            raise HTTPException(status_code=403, detail="Insufficient Funds")
        

async def get_available_balance(user_id: UUID, ticker: str, db: AsyncSession) -> int:
    rec = await check_balance_record(user_id, ticker, db)
    return 0 if rec is None else rec.amount - rec.reserved


async def reserve_balance(user_id: UUID, ticker: str, delta: int, db: AsyncSession):
    stmt = (
        select(BalanceModel)
        .where(
            and_(
                BalanceModel.user_id == user_id,
                BalanceModel.instrument_ticker == ticker
            )
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    rec = result.scalars().first()

    if rec is None:
        raise HTTPException(status_code=400, detail="No Balance Record")

    if delta > 0 and rec.reserved + delta > rec.amount:
        raise HTTPException(status_code=400, detail="Insufficient free balance")
    if delta < 0 and rec.reserved + delta < 0:
        delta = -rec.reserved

    rec.reserved += delta
    db.add(rec)


async def lock_and_update_balance(changes: list[tuple[UUID, str, int]], db: AsyncSession):
    ordered = sorted(changes, key=lambda x: (str(x[0]), x[1]))
    updated = {}
    for user_id, ticker, delta in ordered:
        stmt = (
            select(BalanceModel)
            .where(
                and_(
                    BalanceModel.user_id == user_id,
                    BalanceModel.instrument_ticker == ticker
                )
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        balance = result.scalar_one_or_none()

        if balance is None:
            balance = BalanceModel(user_id=user_id, instrument_ticker=ticker, amount=0)
            db.add(balance)
            await db.flush()

        new_amount = balance.amount + delta
        if new_amount < 0:
            raise HTTPException(status_code=400, detail=f"Insufficient balance for {ticker} of user {user_id}")

        balance.amount = new_amount
        updated[(user_id, ticker)] = balance

    return updated


async def get_max_price_for_market_rub_reserve(ticker: str, db: AsyncSession):
    result = await db.execute(
        select(OrderModel.price)
        .where(
            and_(
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == Direction.SELL,
                OrderModel.ticker == ticker,
                OrderModel.price.isnot(None)
            )
        )
        .order_by(desc(OrderModel.price))
        .limit(1)
    )
    max_price = result.scalar_one_or_none()
    return max_price


# orderbook
async def get_bids(ticker: str, limit: int, db: AsyncSession):
    db_bids = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == Direction.BUY,
                OrderModel.ticker == ticker,
                OrderModel.price.isnot(None)
            )
        )
        .order_by(desc(OrderModel.price))
        .limit(limit)
    )
    return list(db_bids.scalars().all())


async def get_asks(ticker: str, limit: int, db: AsyncSession):
    db_asks = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == Direction.SELL,
                OrderModel.ticker == ticker,
                OrderModel.price.isnot(None)
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
    if ticker is None:
        raise HTTPException(status_code=400, detail="Ticker must be provided")
    db_transaction = TransactionModel(
        ticker=ticker,
        price=price,
        qty=qty,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(db_transaction)


# orders
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
    return db_order


async def get_order_by_id(order_id: UUID, db: AsyncSession):
    result = await db.execute(select(OrderModel).filter_by(id=order_id))
    return result.scalar_one_or_none()


async def get_orders_by_user(user_id: UUID, db: AsyncSession):
    result = await db.execute(select(OrderModel).filter_by(user_id=user_id))
    return list(result.scalars().all())


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
        changes = [
            (user_id, "RUB", -trade_amount),
            (user_id, ticker, trade_qty),
            (counterparty_id, ticker, -trade_qty),
            (counterparty_id, "RUB", trade_amount),
        ]
    else:
        changes = [
            (user_id, ticker, -trade_qty),
            (user_id, "RUB", trade_amount),
            (counterparty_id, "RUB", -trade_amount),
            (counterparty_id, ticker, trade_qty),
        ]
    await lock_and_update_balance(changes, db)

    if is_buy:
        await reserve_balance(user_id, ticker_rub, -trade_amount, db)
    else:
        await reserve_balance(user_id, ticker, -trade_qty, db)

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


# async def execute_market_order(market_order: OrderModel, max_price: int, db: AsyncSession):
#     remaining_qty = market_order.qty
#     ticker = market_order.ticker
#     direction = market_order.direction
#     user_id = market_order.user_id
#
#     is_buy = direction == Direction.BUY
#     opposite_direction = Direction.SELL if is_buy else Direction.BUY
#     ticker_rub = "RUB"
#
#     result = await db.execute(
#         select(OrderModel)
#         .where(
#             and_(
#                 OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
#                 OrderModel.direction == opposite_direction,
#                 OrderModel.ticker == ticker,
#                 OrderModel.price.isnot(None)
#             )
#         )
#         .order_by(asc(OrderModel.price) if is_buy else desc(OrderModel.price))
#     )
#     limit_orders = list(result.scalars().all())
#     if sum([q.qty for q in limit_orders]) < market_order.qty:
#         raise HTTPException(status_code=400, detail="Not enough liquidity to fill market order")
#
#     total_filled = 0
#     for limit_order in limit_orders:
#         available_qty = limit_order.qty - limit_order.filled
#         if available_qty <= 0:
#             continue
#
#         trade_qty = min(remaining_qty, available_qty)
#         trade_price = limit_order.price
#         seller_id = limit_order.user_id
#
#         counterparty_ticker_balance = await check_balance_record(seller_id, ticker, db)
#         counterparty_rub_balance = await check_balance_record(seller_id, ticker_rub, db)
#         if counterparty_ticker_balance is None or (
#             (is_buy and counterparty_ticker_balance.amount < trade_qty) or
#             (not is_buy and counterparty_rub_balance.amount < trade_qty * trade_price)
#         ):
#             continue
#
#         await process_trade(is_buy, user_id, seller_id, ticker, trade_qty, trade_price, db)
#         await update_order_status_and_filled(limit_order, trade_qty, db)
#
#         remaining_qty -= trade_qty
#         total_filled += trade_qty
#
#         if remaining_qty == 0:
#             break
#
#     if total_filled == 0:
#         market_order.status = OrderStatus.CANCELLED
#         if market_order.direction == Direction.SELL:
#             await reserve_balance(market_order.user_id, market_order.ticker, -market_order.qty, db)
#         elif market_order.direction == Direction.BUY:
#             cost = market_order.qty * max_price
#             await reserve_balance(market_order.user_id, "RUB", -cost, db)
#         db.add(market_order)
#         await db.commit()
#         raise HTTPException(status_code=400, detail="No matching orders in the orderbook")
#     market_order.status = OrderStatus.EXECUTED
#     db.add(market_order)
#     return market_order


async def execute_market_sell_order(market_order: OrderModel, db: AsyncSession):
    remaining_qty = market_order.qty
    ticker = market_order.ticker
    user_id = market_order.user_id

    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == Direction.BUY,
                OrderModel.ticker == ticker,
                OrderModel.price.isnot(None)
            )
        )
        .order_by(desc(OrderModel.price))
    )
    limit_orders = list(result.scalars().all())
    if sum([order.qty - order.filled for order in limit_orders]) < remaining_qty:
        raise HTTPException(status_code=400, detail="Not enough liquidity to fill market sell order")

    total_filled = 0
    for limit_order in limit_orders:
        available_qty = limit_order.qty - limit_order.filled
        if available_qty <= 0:
            continue
        trade_qty = min(remaining_qty, available_qty)
        trade_price = limit_order.price
        buyer_id = limit_order.user_id
        seller_balance = await check_balance_record(user_id, ticker, db)
        if seller_balance is None or seller_balance.amount < trade_qty:
            continue
        buyer_rub_balance = await check_balance_record(buyer_id, "RUB", db)
        total_cost = trade_qty * trade_price
        if buyer_rub_balance is None or buyer_rub_balance.amount < total_cost:
            continue

        await process_trade(
            is_buy=False,
            user_id=user_id,
            counterparty_id=buyer_id,
            ticker=ticker,
            trade_qty=trade_qty,
            trade_price=trade_price,
            db=db
        )
        await update_order_status_and_filled(limit_order, trade_qty, db)
        remaining_qty -= trade_qty
        total_filled += trade_qty
        if remaining_qty == 0:
            break

    if total_filled == 0:
        market_order.status = OrderStatus.CANCELLED
        await reserve_balance(user_id, ticker, -market_order.qty, db)
        db.add(market_order)
        await db.commit()
        raise HTTPException(status_code=400, detail="No matching orders in the orderbook to sell")

    market_order.status = OrderStatus.EXECUTED
    db.add(market_order)
    return market_order


async def execute_market_buy_order(market_order: OrderModel, db: AsyncSession):
    if (market_order.type != "MARKET") or (market_order.direction != Direction.BUY):
        raise HTTPException(status_code=400, detail="Order Must Be 'BUY' and 'MARKET'")

    remaining_qty = market_order.qty
    ticker = market_order.ticker
    user_id = market_order.user_id
    ticker_rub = "RUB"

    result = await db.execute(
        select(OrderModel)
        .where(
            and_(
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == Direction.SELL,
                OrderModel.ticker == ticker,
                OrderModel.price.isnot(None)
            )
        )
        .order_by(OrderModel.price.asc(), OrderModel.timestamp.asc())
        .with_for_update()
    )
    sell_orders = list(result.scalars().all())
    if not sell_orders:
        raise HTTPException(status_code=400, detail="No sell orders available")

    total_rub_required = 0
    temp_remaining = remaining_qty
    for order in sell_orders:
        available = order.qty - order.filled
        if available <= 0:
            continue
        match_qty = min(available, temp_remaining)
        total_rub_required += match_qty * order.price
        temp_remaining -= match_qty
        if temp_remaining <= 0:
            break

    if temp_remaining > 0:
        raise HTTPException(status_code=400, detail="Not enough liquidity to fill market order")

    rub_balance = await check_balance_record(user_id, ticker_rub, db)
    if not rub_balance or rub_balance.amount < total_rub_required:
        raise HTTPException(status_code=400, detail="Not enough RUB")
    rub_balance.amount -= total_rub_required
    rub_balance.reserved += total_rub_required
    db.add(rub_balance)
    await db.flush()

    total_filled = 0
    rub_spent = 0
    for limit_order in sell_orders:
        available_qty = limit_order.qty - limit_order.filled
        if available_qty <= 0:
            continue

        trade_qty = min(remaining_qty, available_qty)
        trade_price = limit_order.price
        trade_cost = trade_qty * trade_price
        seller_id = limit_order.user_id

        counterparty_balance = await check_balance_record(seller_id, ticker, db)
        if not counterparty_balance or counterparty_balance.amount < trade_qty:
            continue

        await process_trade(
            is_buy=True,
            user_id=user_id,
            counterparty_id=seller_id,
            ticker=ticker,
            trade_qty=trade_qty,
            trade_price=trade_price,
            db=db
        )
        await update_order_status_and_filled(limit_order, trade_qty, db)

        remaining_qty -= trade_qty
        rub_spent += trade_cost
        total_filled += trade_qty

        if remaining_qty == 0:
            break

    if total_filled == 0:
        rub_balance.amount += total_rub_required
        rub_balance.reserved -= total_rub_required
        market_order.status = OrderStatus.CANCELLED
        db.add_all([rub_balance, market_order])
        await db.commit()
        raise HTTPException(status_code=400, detail="No matching orders were executed")

    market_order.status = OrderStatus.EXECUTED
    market_order.filled = total_filled
    db.add(market_order)

    if rub_spent < total_rub_required:
        refund = total_rub_required - rub_spent
        rub_balance.amount += refund
        rub_balance.reserved -= refund
        db.add(rub_balance)

    await db.commit()
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
                OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                OrderModel.direction == opposite_direction,
                OrderModel.ticker == ticker,
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

        trade_qty = min(remaining_qty, available_qty)
        trade_price = match.price
        counterparty_id = match.user_id

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

        if remaining_qty <= 0:
            break

    limit_order.filled += total_filled
    if limit_order.filled == 0:
        limit_order.status = OrderStatus.NEW
    elif limit_order.filled < limit_order.qty:
        limit_order.status = OrderStatus.PARTIALLY_EXECUTED
    else:
        limit_order.status = OrderStatus.EXECUTED

    db.add(limit_order)
    return limit_order
