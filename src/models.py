from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base # Исправлено: импортирован declarative_base
from datetime import datetime
from enum import Enum

# Исправлено:  Base = declarative_base()  должно быть здесь, после импортов
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # Use bcrypt or similar in a real app
    token = Column(String, unique=True, index=True)  # For authentication (consider default=uuid.uuid4())
    balances = relationship("Balance", back_populates="user")
    orders = relationship("Order", back_populates="user")

class InstrumentType(str, Enum):
    stock = "акция"
    bond = "облигация"
    memecoin = "мемкоин"

class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    instrument_type = Column(String, default="акция")

class OrderType(str, Enum):
    market = "рыночный"
    limit = "лимитный"

class OrderStatus(str, Enum):
    open = "открыт"
    filled = "исполнен"
    partially_filled = "частично_исполнен"
    cancelled = "отменён"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    order_type = Column(String, nullable=False)
    price = Column(Float)
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="открыт")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    instrument = relationship("Instrument")
    trades = relationship("Trade", back_populates="order")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="trades")

class Balance(Base):
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    instrument_id = Column(Integer, ForeignKey("instruments.id"))
    amount = Column(Float, default=0.0)

    user = relationship("User", back_populates="balances")
    instrument = relationship("Instrument")