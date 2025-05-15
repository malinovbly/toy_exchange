# src/models/instrument.py
from sqlalchemy import Column, String

from database.database import Base


class InstrumentModel(Base):
    __tablename__ = "instrument"

    name = Column(String, nullable=False, unique=True, index=True)
    ticker = Column(String, nullable=False, unique=True, index=True, primary_key=True)
