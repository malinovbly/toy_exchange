from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.database import get_db
from src.exchange import Exchange
from src.models.order import OrderModel, OrderStatus, Direction
from src.models.balance import BalanceModel
from src.schemas.schemas import (
    LimitOrderBody,
    MarketOrderBody,
    LimitOrder,
    MarketOrder,
    CreateOrderResponse,
    OrderStatus as SchemaOrderStatus
)
from src.utils import (
    create_order_in_db,
    get_order_by_id,
    get_orders_by_user,
    cancel_order,
    update_order_status,
    get_current_user,
    update_user_balance
)

summary_tags = {
    "create_order": "Create Order",
    "list_orders": "List Orders",
    "get_order": "Get Order",
    "cancel_order": "Cancel Order"
}

router = APIRouter()


async def get_exchange():
    exchange = Exchange()
    await exchange.connect()
    return exchange


@router.post(
    "/api/v1/order", tags=["order"], 
    response_model=CreateOrderResponse,
    summary="Create Order"
)
async def create_order(
    order_data: Union[LimitOrderBody, MarketOrderBody],
    current_user: dict = Depends(get_current_user),
    exchange: Exchange = Depends(get_exchange),
    db: Session = Depends(get_db)
):
    try:
        user_id = UUID(current_user["user_id"])
        db_order = create_order_in_db(order_data, user_id, db)
        
        if isinstance(order_data, MarketOrderBody):
            
            executed_price = await exchange.get_current_price(order_data.ticker)
            if executed_price is None:
                raise HTTPException(status_code=500, detail="Could not get market price")
            
           
            base_change = order_data.qty if order_data.direction == Direction.BUY else -order_data.qty
            quote_change = -order_data.qty * executed_price if order_data.direction == Direction.BUY else order_data.qty * executed_price
            
            try:
                update_user_balance(db, user_id, order_data.ticker, base_change)
                update_user_balance(db, user_id, "USD", quote_change)
                
                db_order = update_order_status(
                    db_order.id,
                    SchemaOrderStatus.EXECUTED,
                    order_data.qty,
                    db
                )
            except HTTPException as e:
                db_order = update_order_status(
                    db_order.id,
                    SchemaOrderStatus.REJECTED,
                    0,
                    db
                )
                raise e
        
        return CreateOrderResponse(order_id=db_order.id)
    
    except Exception as e:
        print(f"Order creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/order", tags=["order"], response_model=List[Union[LimitOrder, MarketOrder]], summary="List Orders"
)
def list_orders(
    user_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user['user_id']
    if isinstance(user_id, str):
        user_id = UUID(user_id)
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
    summary="Get Order"
)
def get_order(
    order_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = get_order_by_id(order_id, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != UUID(current_user["user_id"]):
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
    summary="Cancel Order"
)
def cancel_order_api(
    order_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = get_order_by_id(order_id, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != UUID(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    if order.status == OrderStatus.PARTIALLY_EXECUTED and order.price is not None:
        remaining_qty = order.qty - order.filled
        if remaining_qty > 0:
            quote_change = remaining_qty * order.price
            if order.direction == Direction.BUY:
                update_user_balance(db, order.user_id, "USD", quote_change)
            else:
                update_user_balance(db, order.user_id, order.ticker, remaining_qty)
    
    cancelled_order = cancel_order(order_id, db)
    
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