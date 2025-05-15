# src/models/balance.py
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from src.database.database import Base


class BalanceModel(Base):
    __tablename__ = "balance"

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), index=True, primary_key=True)
    instrument_ticker = Column(String, ForeignKey("instrument.ticker"), index=True, primary_key=True)
    amount = Column(Integer, default=0)
