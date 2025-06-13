# src/models/user.py
from sqlalchemy import Column, String, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.schemas.schemas import UserRole
from src.database.database import Base


class UserModel(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    role = Column(SqlEnum(UserRole), default=UserRole.USER)
    api_key = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    orders = relationship("OrderModel", backref="user", passive_deletes=True)
    balance = relationship("BalanceModel", backref="user", passive_deletes=True)
