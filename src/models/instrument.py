# src/models/instrument.py
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from src.database.database import Base


class InstrumentModel(Base):
    __tablename__ = "instrument"

    name = Column(String, nullable=False, unique=True, index=True)
    ticker = Column(String, nullable=False, unique=True, index=True, primary_key=True)

    orders = relationship("OrderModel", backref="instrument", passive_deletes=True)
    balance = relationship("BalanceModel", backref="instrument", passive_deletes=True)
    transactions = relationship("TransactionModel", backref="instrument", passive_deletes=True)
