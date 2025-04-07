# src/schemas/schemas.py
from pydantic import BaseModel


class NewUser(BaseModel):
    name: str


class User(BaseModel):
    id: str
    name: str
    role: str
    api_key: str
