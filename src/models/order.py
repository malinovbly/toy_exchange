# src/models/order.py
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SqlEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from enum import Enum

from src.schemas.schemas import OrderStatus, Direction
from src.database.database import Base


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.NEW)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    direction = Column(SqlEnum(Direction), nullable=False)
    ticker = Column(String, ForeignKey("instrument.ticker", ondelete="CASCADE"), nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Integer, nullable=True)
    filled = Column(Integer, nullable=False, default=0)

    type = Column(SqlEnum(OrderType), nullable=False)
