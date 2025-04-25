# src/models/order.py
from sqlalchemy import Column, String, Float, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
import uuid
from src.database import Base


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderModel(Base):
    __tablename__ = "orders"

    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(SqlEnum(OrderType), nullable=False)
    side = Column(SqlEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
