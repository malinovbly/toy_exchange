from fastapi import Depends, HTTPException, Security, APIRouter
from sqlalchemy.orm import Session
from src.security import api_key_header
from src.database import get_db
from src.models.user import UserModel

router = APIRouter()

def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> dict:
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
    token = api_key[6:]

    user = db.query(UserModel).filter(UserModel.api_key == token).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "username": user.name,
        "user_id": user.id
    }

@router.get("/api/v1/protected", tags=["public"])
def protected_route(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello, {current_user['username']}!",
        "user_id": str(current_user["user_id"])
    }
