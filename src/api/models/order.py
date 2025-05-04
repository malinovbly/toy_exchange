# src/models/order.py
from sqlalchemy import Column, String, Integer, Enum as SqlEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
import uuid
from src.database import Base
from datetime import datetime
from typing import Optional, Union, Literal

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.NEW)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    direction = Column(SqlEnum(Direction), nullable=False)
    ticker = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    
    price = Column(Integer, nullable=True)
    
    filled = Column(Integer, nullable=False, default=0)

    def to_limit_order_dict(self):
        return {
            "id": str(self.id),
            "status": self.status,
            "user_id": str(self.user_id),
            "timestamp": self.timestamp.isoformat(),
            "filled": self.filled,
            "body": {
                "direction": self.direction,
                "ticker": self.ticker,
                "qty": self.qty,
                "price": self.price
            }
        }

    def to_market_order_dict(self):
        return {
            "id": str(self.id),
            "status": self.status,
            "user_id": str(self.user_id),
            "timestamp": self.timestamp.isoformat(),
            "body": {
                "direction": self.direction,
                "ticker": self.ticker,
                "qty": self.qty
            }
        }