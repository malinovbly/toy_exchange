# src/models/user.py
from sqlalchemy import Column, String
import uuid

from src.database import Base


class UserModel(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    role = Column(String)
    api_key = Column(String, nullable=False, index=True)
