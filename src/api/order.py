from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict
from uuid import UUID
from src.exchange import Exchange
from src.database import get_db
from src.models.order import Order, OrderStatus, OrderType, OrderSide
from src.database import InMemoryDatabase
from src.api.auth_tests import get_current_user  # Импортируем функцию для проверки токена


router = APIRouter()


async def get_exchange():
    exchange = Exchange()
    await exchange.connect()
    return exchange


# Создание нового ордера (с проверкой токена)
@router.post(path="/api/v1/order", tags=["order"], response_model=Order, summary="Create a new order")
async def create_order(order: Order, 
                       current_user: dict = Depends(get_current_user),  
                       exchange: Exchange = Depends(get_exchange),
                       db: InMemoryDatabase = Depends(get_db)):
    """
    Create a new order.
    """
    if order.order_type == OrderType.MARKET:
        try:
            executed_price = await exchange.get_current_price(order.symbol)
            if executed_price is None:
                raise HTTPException(status_code=500, detail="Could not get market price")
            print(f"Executing Market Order: {order} at price: {executed_price}")
            order.price = executed_price
            order.status = OrderStatus.FILLED
            db.update_balance(order.user_id, order.symbol,
                              order.quantity if order.side == OrderSide.BUY else -order.quantity)  # For simplicity, assume we have tokens
            db.update_balance(order.user_id, "USD",
                              -order.quantity * executed_price if order.side == OrderSide.BUY else order.quantity * executed_price)  # Buy uses USD
        except Exception as e:
            print(f"Error executing market order: {e}")
            order.status = OrderStatus.REJECTED
    elif order.order_type == OrderType.LIMIT:
        order.status = OrderStatus.OPEN
    else:
        raise HTTPException(status_code=400, detail="Invalid order type")

    created_order = db.create_order(order)
    return created_order


# Получение всех ордеров (с проверкой токена)
@router.get(path="/api/v1/order", tags=["order"], response_model=List[Order],
            summary="List all orders (or filter by user)")
def list_orders(user_id: Optional[UUID] = Query(None, description="Filter orders by user ID"),
                current_user: dict = Depends(get_current_user), 
                db: InMemoryDatabase = Depends(get_db)):
    """
    List all orders.  Optionally filter by user ID.
    """
    if user_id:
        return db.get_orders_by_user(user_id)
    all_orders = []
    for user_id in db.orders:
        all_orders.extend(db.orders[user_id])
    return all_orders


# Получение ордера по ID (с проверкой токена)
@router.get(path="/api/v1/order/{order_id}", tags=["order"], response_model=Order, summary="Get an order by ID")
def get_order(order_id: UUID, current_user: dict = Depends(get_current_user), 
              db: InMemoryDatabase = Depends(get_db)):
    """
    Get an order by its ID.
    """
    order = db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# Отмена ордера (с проверкой токена)
@router.delete(path="/api/v1/order/{order_id}", tags=["order"], response_model=Order, summary="Cancel an order")
def cancel_order(order_id: UUID, current_user: dict = Depends(get_current_user),  
                 db: InMemoryDatabase = Depends(get_db)):
    """
    Cancel an order.  This will change the order's status to CANCELLED.
    """
    cancelled_order = db.cancel_order(order_id)
    if not cancelled_order:
        raise HTTPException(status_code=404, detail="Order not found or cannot cancel filled order")
    return cancelled_order


# Получение статуса ордера (с проверкой токена)
@router.get(path="/api/v1/order/{order_id}/status", tags=["order"], response_model=OrderStatus,
            summary="Get order status")
def get_order_status(order_id: UUID, current_user: dict = Depends(get_current_user),  
                     db: InMemoryDatabase = Depends(get_db)):
    """
    Get the status of a specific order.
    """
    order = db.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.status


# Получение активных ордеров пользователя (с проверкой токена)
@router.get(path="/api/v1/order/active/{user_id}", tags=["order"], response_model=List[Order],
            summary="Get active orders for a user")
def get_active_orders(user_id: UUID, current_user: dict = Depends(get_current_user),  
                      db: InMemoryDatabase = Depends(get_db)):
    """
    Get a list of active orders (OPEN or PENDING) for a given user.
    """
    orders = db.get_orders_by_user(user_id)
    active_orders = [order for order in orders if order.status in (OrderStatus.OPEN, OrderStatus.PENDING)]
    return active_orders


# Получение ордербука для символа (с проверкой токена)
@router.get(path="/api/v1/orderbook/{symbol}", tags=["order"], response_model=Dict,
            summary="Get order book for a symbol")
async def get_orderbook(symbol: str, current_user: dict = Depends(get_current_user), 
                        exchange: Exchange = Depends(get_exchange)):  # Make async
    """
    Get the order book (bids and asks) for a specific trading symbol.
    """
    orderbook = await exchange.get_order_book(symbol)  # Await get orderbook
    if orderbook is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve order book")
    return orderbook
