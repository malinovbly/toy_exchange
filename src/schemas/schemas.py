# src/schemas/schemas.py
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    name: str


class RegisterResponse(BaseModel):
    token: str
