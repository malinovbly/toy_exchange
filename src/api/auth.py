from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import uuid
import hashlib


router = APIRouter()

# Типо "база данных"
fake_users_db = {}

# Схема безопасности — для кнопки "Authorize"
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


class RegisterRequest(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    token: str


# Хэшируем, чтобы не хранить пароль в чистом виде
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# Регистрация: создаём пользователя с user_id и token
@router.post("/api/v1/public/register", tags=["public"], response_model=RegisterResponse)
def register(user: RegisterRequest):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_id = uuid.uuid4()
    token = str(uuid.uuid4())

    fake_users_db[user.username] = {
        "user_id": user_id,
        "password": hash_password(user.password),
        "token": token,
    }

    return {"token": token}


# Проверка токена + возвращаем и user_id, и username
def get_current_user(api_key: str = Security(api_key_header)) -> dict:
    if not api_key or not api_key.startswith("TOKEN "):
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
