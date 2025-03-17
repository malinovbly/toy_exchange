# pydantic schemas for entities: users/instruments/...
from pydantic import BaseModel


class User(BaseModel):
    name: str
    ...
