# src/api/order.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_db
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
    cancel_order,
    get_instrument_by_ticker,
    execute_market_order,
    execute_limit_order,
    get_api_key,
    check_balance_record,
    create_order_dict
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
            raise HTTPException(
                status_code=404,
                detail=f"Ticker '{order_data.ticker}' not found in instruments"
            )

        # Проверка кол-ва тикера (если продаем)
        balance = await check_balance_record(user_id, order_data.ticker, db)
        if (balance is None or balance.amount < order_data.qty) and order_data.direction == Direction.SELL:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {order_data.ticker} balance for order"
            )
        
        # Проверка кол-ва рублей (если покупаем)
        elif order_data.direction == Direction.BUY:
            rub_balance = await check_balance_record(user_id, "RUB", db)
            total_cost = order_data.qty * getattr(order_data, "price", 1) 

            if rub_balance is None or rub_balance.amount < total_cost:
                raise HTTPException(status_code=400, detail=f"Insufficient RUB balance for order")

        # Рыночная заявка
        if isinstance(order_data, MarketOrderBody):
            db_order = await create_order_in_db(order_data, price=None, user_id=user_id, db=db)
            executed_order = await execute_market_order(db_order, db=db)

        # Лимитная заявка
        else:
            db_order = await create_order_in_db(order_data, price=order_data.price, user_id=user_id, db=db)
            executed_order = await execute_limit_order(db_order, db=db)

        return CreateOrderResponse(order_id=executed_order.id)

    except HTTPException as he:
        raise he
    except Exception as e:
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

        user_id = auth_user.id
        order = await get_order_by_id(UUID(order_id), db)

        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this order")

        order_dict = create_order_dict(order)
        return order_dict

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    path="/api/v1/order/{order_id}",
    tags=["order"],
    response_model=Union[LimitOrder, MarketOrder],
    summary=summary_tags["cancel_order"]
)
async def delete_order_api(
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

        await cancel_order(UUID(order_id), db)
        return Ok

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))