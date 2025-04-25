# src/api/order.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.database import get_db
from src.exchange import Exchange
from src.api.auth_tests import get_current_user
from src.models.order import OrderModel  # Для SQLAlchemy модели
from src.schemas.schemas import Order, NewOrder  # Для Pydantic модели
from src.models.order import OrderModel, OrderStatus, OrderType, OrderSide
from src.utils import (
    create_order_in_db,
    get_order_by_id, 
    get_orders_by_user, 
    cancel_order, 
    list_all_orders
)
from src.utils import update_balance 

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


@router.post("/api/v1/order", tags=["order"], response_model=NewOrder, summary=summary_tags["create_order"])
async def create_order(order: NewOrder,  
                       current_user: dict = Depends(get_current_user),
                       exchange: Exchange = Depends(get_exchange),
                       db: Session = Depends(get_db)):
    
    if order.order_type == OrderType.MARKET:
        try:
            executed_price = await exchange.get_current_price(order.symbol)
            if executed_price is None:
                raise HTTPException(status_code=500, detail="Could not get market price")
            order.price = executed_price
            order.status = OrderStatus.FILLED

            update_balance(order.user_id, order.symbol,
                           order.quantity if order.side == OrderSide.BUY else -order.quantity, db)
            update_balance(order.user_id, "USD",
                           -order.quantity * executed_price if order.side == OrderSide.BUY else order.quantity * executed_price, db)
        except Exception as e:
            print(f"Market order error: {e}")
            order.status = OrderStatus.REJECTED
    elif order.order_type == OrderType.LIMIT:
        if not order.price: 
            raise HTTPException(status_code=400, detail="Price must be provided for limit orders")
        order.status = OrderStatus.OPEN
    else:
        raise HTTPException(status_code=400, detail="Invalid order type")

    created = create_order_in_db(order, db)
    return NewOrder.model_construct(**created.__dict__)

@router.get("/api/v1/order", tags=["order"], response_model=List[Order], summary=summary_tags["list_orders"])
def list_orders(user_id: Optional[UUID] = Query(None),
                current_user: dict = Depends(get_current_user),
                db: Session = Depends(get_db)):
    
    user_id = current_user['user_id']
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    orders = get_orders_by_user(user_id, db)
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found for this user.")
    
    return [Order.model_construct(**o.__dict__) for o in orders]


@router.get("/api/v1/order/{order_id}", tags=["order"], response_model=Order, summary=summary_tags["get_order"])
def get_order_api(order_id: UUID,
                  current_user: dict = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    order = get_order_by_id(order_id, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(order.user_id) != str(current_user["user_id"]): 
        raise HTTPException(status_code=403, detail="You do not have permission to access this order")
    
    return Order.model_construct(**order.__dict__)


@router.delete("/api/v1/order/{order_id}", tags=["order"], response_model=Order, summary=summary_tags["cancel_order"])
def cancel_order_api(order_id: UUID,
                     current_user: dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    order = cancel_order(order_id, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or cannot cancel filled order")
    return Order.model_construct(**order.__dict__)
