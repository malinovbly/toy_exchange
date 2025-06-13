# src/models/transaction.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone

from src.database.database import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("instrument.ticker", ondelete="CASCADE"), nullable=False)
    price = Column(Integer, nullable=False)
    qty = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
