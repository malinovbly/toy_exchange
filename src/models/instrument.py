# src/models/instrument.py
from sqlalchemy import Column, String

from src.database import Base


class InstrumentModel(Base):
    __tablename__ = "instrument"

    name = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True, primary_key=True)
