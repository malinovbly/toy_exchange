# src/models/user.py
from sqlalchemy import Column, String, Enum as SqlEnum
import uuid

from src.schemas.schemas import UserRole
from src.database import Base


class UserModel(Base):
    __tablename__ = "user"

    id = Column(String, nullable=False, unique=True, index=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    role = Column(SqlEnum(UserRole), default=UserRole.USER)
    api_key = Column(String, nullable=False, unique=True, index=True)
