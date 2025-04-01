from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from .models import InstrumentType, OrderStatus, OrderType  # Import enums

class InstrumentBase(BaseModel):
    ticker: str
    name: str
    instrument_type: Optional[InstrumentType] = InstrumentType.stock  # Default stock

class InstrumentCreate(InstrumentBase):
    pass

class Instrument(InstrumentBase):
    id: int

    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    instrument_id: int
    order_type: OrderType
    price: Optional[float] = None  # Required for limit orders
    quantity: int

    @validator("price")
    def price_must_be_provided_for_limit(cls, v, values):
        if values.get("order_type") == OrderType.limit and v is None:
            raise ValueError("Price is required for limit orders")
        return v

class OrderUpdate(BaseModel):
    status: OrderStatus

class OrderRead(BaseModel):
    id: int
    instrument_id: int
    order_type: OrderType
    price: Optional[float]
    quantity: int
    status: OrderStatus
    created_at: datetime

    class Config:
        orm_mode = True

class BalanceRead(BaseModel):
    instrument_id: int
    ticker: str
    amount: float

    class Config:
        orm_mode = True

class TradeRead(BaseModel):
    price: float
    quantity: int
    timestamp: datetime
    instrument_ticker: str

    class Config:
        orm_mode = True

class CandleData(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True