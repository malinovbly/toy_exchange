# src/models/order.py

from pydantic import BaseModel
from uuid import UUID, uuid4
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Order(BaseModel):
    order_id: UUID = uuid4()
    user_id: UUID
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING

    def __repr__(self):
        return (
            f"Order(order_id={self.order_id}, user_id={self.user_id}, symbol={self.symbol}, type={self.order_type}, side={self.side},"
            f" quantity={self.quantity}, price={self.price}, status={self.status})")
