from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.schemas.schemas import RegisterRequest, RegisterResponse
from src.models.user import UserModel
from src.utils import generate_uuid
from src.database import get_db


router = APIRouter()


# Регистрация: создаём пользователя с user_id и token
@router.post("/api/v1/public/register", tags=["public"], response_model=RegisterResponse)
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    if not db.query(UserModel).filter(UserModel.name == user.name).first() is None:
        raise HTTPException(status_code=400, detail="Username already exists")

    token = generate_uuid()

    db_user = UserModel(
        id=generate_uuid(),
        name=user.name,
        role="USER",
        api_key=token
    )
    db.add(db_user)
    db.commit()

    return {"token": token}


@router.get(path="/api/v1/public/instrument", tags=["public"])
def list_instruments():
    ...


@router.get(path="/api/v1/public/orderbook/{ticker}", tags=["public"])
def get_orderbook():
    ...


@router.get(path="/api/v1/public/transactions/{ticker}", tags=["public"])
def get_transaction_history():
    ...
