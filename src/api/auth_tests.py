from fastapi import APIRouter, HTTPException, Security, Depends

from src.security import api_key_header


router = APIRouter()

# Типо "база данных"
fake_users_db = {}


# Проверка токена + возвращаем и user_id, и username
def get_current_user(api_key: str = Security(api_key_header)) -> dict:
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
