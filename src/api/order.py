from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union
from uuid import UUID
from sqlalchemy.orm import Session

from src.api.public import get_orderbook
from src.database import get_db
from src.security import api_key_header
from src.schemas.schemas import (
    LimitOrderBody,
    MarketOrderBody,
    LimitOrder,
    MarketOrder,
    CreateOrderResponse,
    OrderStatus,
    Direction
)
from src.utils import (
    create_order_in_db,
    get_order_by_id,
    get_user_by_api_key,
    get_orders_by_user,
    cancel_order,
    update_order_status,
    update_user_balance,
    get_instrument_by_ticker
)

summary_tags = {
    "create_order": "Create Order",
    "list_orders": "List Orders",
    "get_order": "Get Order",
    "cancel_order": "Cancel Order"
}

router = APIRouter()


@router.post(
    "/api/v1/order", tags=["order"],
    response_model=CreateOrderResponse,
    summary=summary_tags["create_order"]
)
async def create_order(
        order_data: Union[LimitOrderBody, MarketOrderBody],
        authorization: str = Depends(api_key_header),
        db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    auth_user = get_user_by_api_key(UUID(authorization), db)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = auth_user.id

        # Проверка существования тикера в базе
        instrument = get_instrument_by_ticker(order_data.ticker, db)
        if instrument is None:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker '{order_data.ticker}' not found in instruments"
            )

        # Рыночная заявка
        if isinstance(order_data, MarketOrderBody):
            orderbook = get_orderbook(order_data.ticker, limit=10, db=db)
            if order_data.direction == Direction.BUY:
                if not orderbook.ask_levels:
                    raise HTTPException(status_code=400, detail="No available asks in orderbook")
                market_price = str(orderbook.ask_levels[0].price)
            else:
                if not orderbook.bid_levels:
                    raise HTTPException(status_code=400, detail="No available bids in orderbook")
                market_price = str(orderbook.bid_levels[0].price)

            db_order = create_order_in_db(order_data, market_price, user_id, db)
            db_order = update_order_status(
                db_order.id,
                OrderStatus.NEW,
                order_data.qty,
                db
            )
        # Лимитная заявка
        else:
            db_order = create_order_in_db(order_data, order_data.price, user_id, db)

        return CreateOrderResponse(order_id=db_order.id)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Order creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/order", tags=["order"], response_model=List[Union[LimitOrder, MarketOrder]], summary=summary_tags["list_orders"])
def list_orders(
        authorization: str = Depends(api_key_header),
        db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    auth_user = get_user_by_api_key(UUID(authorization), db)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = auth_user.id
    orders = get_orders_by_user(user_id, db)

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found for this user")

    result = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "status": order.status,
            "user_id": order.user_id,
            "timestamp": order.timestamp,
            "filled": order.filled,
            "body": {
                "direction": order.direction,
                "ticker": order.ticker,
                "qty": order.qty
            }
        }

        if order.price is not None:
            order_dict["body"]["price"] = order.price
            result.append(LimitOrder(**order_dict))
        else:
            result.append(MarketOrder(**order_dict))

    return result


@router.get(
    "/api/v1/order/{order_id}", tags=["order"],
    response_model=Union[LimitOrder, MarketOrder],
    summary=summary_tags["get_order"]
)
def get_order(
        order_id: str,
        authorization: str = Depends(api_key_header),
        db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    auth_user = get_user_by_api_key(UUID(authorization), db)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = auth_user.id
    order = get_order_by_id(UUID(order_id), db)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this order")

    order_dict = {
        "id": order.id,
        "status": order.status,
        "user_id": order.user_id,
        "timestamp": order.timestamp,
        "filled": order.filled,
        "body": {
            "direction": order.direction,
            "ticker": order.ticker,
            "qty": order.qty
        }
    }

    if order.price is not None:
        order_dict["body"]["price"] = order.price
        return LimitOrder(**order_dict)
    return MarketOrder(**order_dict)


@router.delete(
    "/api/v1/order/{order_id}", tags=["order"],
    response_model=Union[LimitOrder, MarketOrder],
    summary=summary_tags["cancel_order"]
)
def cancel_order_api(
        order_id: str,
        authorization: str = Depends(api_key_header),
        db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    auth_user = get_user_by_api_key(UUID(authorization), db)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized 2")

    order = get_order_by_id(UUID(order_id), db)

    if order.status == OrderStatus.PARTIALLY_EXECUTED or order.status == OrderStatus.NEW:
        quote_change = order.qty * order.price
        if order.direction == Direction.BUY:
            update_user_balance(order.user_id, order.ticker, -quote_change, order.direction, db)
        else:
            update_user_balance(order.user_id, order.ticker, quote_change, order.direction, db)

    cancelled_order = cancel_order(UUID(order_id), db)

    order_dict = {
        "id": cancelled_order.id,
        "status": cancelled_order.status,
        "user_id": cancelled_order.user_id,
        "timestamp": cancelled_order.timestamp,
        "filled": cancelled_order.filled,
        "body": {
            "direction": cancelled_order.direction,
            "ticker": cancelled_order.ticker,
            "qty": cancelled_order.qty
        }
    }

    if cancelled_order.price is not None:
        order_dict["body"]["price"] = cancelled_order.price
        return LimitOrder(**order_dict)
    return MarketOrder(**order_dict)
