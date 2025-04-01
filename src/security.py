from passlib.context import CryptContext
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db  # Исправленный импорт
from src import models
import jwt
from pydantic import BaseModel
from typing import Optional

# ... (остальной код)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Token Authentication setup
TOKEN_PREFIX = "TOKEN"
bearer_scheme = HTTPBearer(scheme_name="Authorization")

SECRET_KEY = "YOUR_SECRET_KEY"  # Replace with a strong, random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(bearer_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # decode the JWT
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first() # validate the JWT token with user data
    if user is None:
        raise credentials_exception
    return user