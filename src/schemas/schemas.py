# src/schemas/schemas.py
import pydantic
from pydantic import BaseModel, Field, conint
from typing import Optional
from uuid import UUID


class Body_deposit_api_v1_admin_balance_deposit_post(BaseModel):
    user_id: str
    ticker: str
    amount: conint(gt=0)


class Body_withdraw_api_v1_admin_balance_withdraw_post(BaseModel):
    user_id: str
    ticker: str
    amount: conint(gt=0)


class Instrument(BaseModel):
    name: str
    ticker: pydantic.constr(pattern="^[A-Z]{2,10}$")


class NewUser(BaseModel):
    name: pydantic.constr(min_length=3)


class Ok(BaseModel):
    success: bool = True


class User(BaseModel):
    id: str
    name: str
    role: str
    api_key: str

class NewOrder(BaseModel):
    order_id: Optional[str] = None
    user_id: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: float
    status: Optional[str] = "pending"  
    
class Order(BaseModel):
    order_id: UUID
    user_id: UUID
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: float
    status: str  