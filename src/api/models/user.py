# src/models/user.py
from sqlalchemy import Column, String
import uuid

from src.database import Base


class UserModel(Base):
    __tablename__ = "user"

    id = Column(String, nullable=False, unique=True, index=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    role = Column(String)
    api_key = Column(String, nullable=False, unique=True, index=True)
