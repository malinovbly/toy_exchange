from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
import uuid
from sqlalchemy.orm import Session

from src.schemas.schemas import RegisterRequest, RegisterResponse
from src.database import get_db
from src.models.user import UserModel


router = APIRouter()

# Типо "база данных"
fake_users_db = {}

# Схема безопасности — для кнопки "Authorize"
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


# Регистрация: создаём пользователя с user_id и token
@router.post("/api/v1/public/register", tags=["public"], response_model=RegisterResponse)
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    if not db.query(UserModel).filter(UserModel.name == user.name).first() is None:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_id = str(uuid.uuid4())
    token = str(uuid.uuid4())

    db_user = UserModel(
        id=user_id,
        name=user.name,
        role="USER",
        api_key=token
    )
    db.add(db_user)
    db.commit()

    return {"token": token}


# Проверка токена + возвращаем и user_id, и username
def get_current_user(api_key: str = Security(api_key_header), db: Session = Depends(get_db)) -> dict:
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
    token = api_key[6:]

    for username, user in fake_users_db.items():
        if user["token"] == token:
            return {
                "username": username,
                "user_id": user["user_id"]
            }

    raise HTTPException(status_code=401, detail="Invalid token")


# Пример защищённого маршрута
@router.get("/api/v1/protected", tags=["public"])
def protected_route(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello, {current_user['username']}!",
        "user_id": str(current_user["user_id"])
    }
