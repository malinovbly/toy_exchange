# src/schemas/schemas.py
import pydantic
from pydantic import BaseModel, conint
from typing import Literal
from uuid import UUID
from datetime import datetime
from enum import Enum


class Body_deposit_api_v1_admin_balance_deposit_post(BaseModel):
    user_id: UUID
    ticker: str
    amount: conint(gt=0)


class Body_withdraw_api_v1_admin_balance_withdraw_post(BaseModel):
    user_id: UUID
    ticker: str
    amount: conint(gt=0)


class Instrument(BaseModel):
    name: str
    ticker: pydantic.constr(pattern="^[A-Z]{2,10}$")


class NewUser(BaseModel):
    name: pydantic.constr(min_length=3)


class Ok(BaseModel):
    success: Literal[True] = True


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(BaseModel):
    id: UUID
    name: str
    role: UserRole
    api_key: str


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: conint(ge=1)
    price: conint(gt=0)


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: conint(ge=1)


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0


class MarketOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: datetime
    body: MarketOrderBody


class CreateOrderResponse(BaseModel):
    success: Literal[True] = True 
    order_id: UUID


class Level(BaseModel):
    price: int
    qty: int


class L2OrderBook(BaseModel):
    bid_levels: list[Level]
    ask_levels: list[Level]


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime
