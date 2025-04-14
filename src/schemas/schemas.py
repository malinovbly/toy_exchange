# src/schemas/schemas.py
import pydantic
from pydantic import BaseModel


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
