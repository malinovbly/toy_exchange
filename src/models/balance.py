# src/models/balance.py
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.database import Base


class BalanceModel(Base):
    __tablename__ = "balance"

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), index=True, primary_key=True)
    instrument_ticker = Column(String, ForeignKey("instrument.ticker", ondelete="CASCADE"), index=True, primary_key=True)
    amount = Column(Integer, default=0)
    reserved = Column(Integer, default=0)

    user = relationship("UserModel", backref="balance", passive_deletes=True)
    instrument = relationship("InstrumentModel", backref="balance", passive_deletes=True)
