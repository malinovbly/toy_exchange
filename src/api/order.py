# src/api/order.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_db
from src.models.order import OrderStatus
from src.security import api_key_header
from src.schemas.schemas import (
    LimitOrderBody,
    MarketOrderBody,
    LimitOrder,
    MarketOrder,
    CreateOrderResponse,
    Direction,
    Ok
)
from src.utils import (
    create_order_in_db,
    get_order_by_id,
    get_user_by_api_key,
    get_orders_by_user,
    get_instrument_by_ticker,
    execute_market_order,
    execute_limit_order,
    get_api_key,
    create_order_dict,
    get_available_balance,
    reserve_balance
)

summary_tags = {
    "create_order": "Create Order",
    "list_orders": "List Orders",
    "get_order": "Get Order",
    "cancel_order": "Cancel Order"
}

router = APIRouter()


@router.post(
    path="/api/v1/order",
    tags=["order"],
    response_model=CreateOrderResponse,
    summary=summary_tags["create_order"]
)
async def create_order(
        order_data: Union[LimitOrderBody, MarketOrderBody],
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        auth_user = await get_user_by_api_key(UUID(api_key), db)
        if auth_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user_id = auth_user.id

        # Проверка существования тикера в базе
        instrument = await get_instrument_by_ticker(order_data.ticker, db)
        if instrument is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{order_data.ticker}' Not Found")

        # Проверка кол-ва тикера (если продаем)
        if order_data.direction == Direction.SELL:
            avail = await get_available_balance(user_id, order_data.ticker, db)
            if avail < order_data.qty:
                raise HTTPException(status_code=400, detail=f"Insufficient '{order_data.ticker}' balance for order")
            # Резервируем
            await reserve_balance(user_id, order_data.ticker, +order_data.qty, db)

        elif order_data.direction == Direction.BUY:
            cost = order_data.qty * order_data.price
            avail_rub = await get_available_balance(user_id, "RUB", db)
            if avail_rub < cost:
                raise HTTPException(status_code=400, detail="Insufficient 'RUB' balance for order")
            await reserve_balance(user_id, "RUB", +cost, db)

        # Рыночная заявка
        if isinstance(order_data, MarketOrderBody):
            db_order = await create_order_in_db(order_data=order_data, price=None, user_id=user_id, db=db)
            executed_order = await execute_market_order(db_order, db=db)

        # Лимитная заявка
        else:
            db_order = await create_order_in_db(order_data=order_data, price=order_data.price, user_id=user_id, db=db)
            executed_order = await execute_limit_order(db_order, db=db)

        await db.commit()
        await db.refresh(executed_order)
        return CreateOrderResponse(order_id=executed_order.id)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    path="/api/v1/order",
    tags=["order"],
    response_model=List[Union[LimitOrder, MarketOrder]],
    summary=summary_tags["list_orders"]
)
async def list_orders(
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        auth_user = await get_user_by_api_key(UUID(api_key), db)
        if auth_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user_id = auth_user.id
        orders = await get_orders_by_user(user_id, db)

        if not orders:
            return []

        result = []
        for order in orders:
            order_dict = create_order_dict(order)
            result.append(order_dict)

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    path="/api/v1/order/{order_id}",
    tags=["order"],
    response_model=Union[LimitOrder, MarketOrder],
    summary=summary_tags["get_order"]
)
async def get_order(
        order_id: str,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        auth_user = await get_user_by_api_key(UUID(api_key), db)
        if auth_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        order = await get_order_by_id(UUID(order_id), db)

        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.user_id != auth_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this order")

        return create_order_dict(order)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    path="/api/v1/order/{order_id}",
    tags=["order"],
    response_model=Ok,
    summary=summary_tags["cancel_order"]
)
async def cancel_order(
        order_id: str,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = UUID(get_api_key(authorization))
        auth_user = await get_user_by_api_key(api_key, db)
        if auth_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Получаем ордер
        order_id = UUID(order_id)
        db_order = await get_order_by_id(order_id, db)
        if db_order is None:
            raise HTTPException(status_code=404, detail="Order Not Found")

        if db_order.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail=f"Order Already {db_order.status}")

        # Разморозка оставшегося объема
        unfilled_qty = db_order.qty - db_order.filled
        if unfilled_qty > 0:
            ticker = db_order.ticker
            direction = db_order.direction
            user_id = db_order.user_id

            if direction == Direction.BUY:
                # Возвращаем RUB
                refund = unfilled_qty * (db_order.price or 1)
                await reserve_balance(user_id, "RUB", -refund, db)
            else:
                # Возвращаем тикер
                await reserve_balance(user_id, ticker, -unfilled_qty, db)

        # Отменяем ордер
        db_order.status = OrderStatus.CANCELLED
        await db.commit()
        return Ok()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
