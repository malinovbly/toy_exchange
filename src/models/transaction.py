# src/models/transaction.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from src.database.database import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    # По идее, пока что id нигде не используется
    # Добавила, просто чтобы консоль не ругалась
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    qty = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
