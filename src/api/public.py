# src/api/public.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.schemas.schemas import NewUser, User
from src.models.user import UserModel
from src.utils import generate_uuid, check_username
from src.database import get_db


summary_tags = {
    "register": "Register",
    "list_instruments": "List Instruments",
    "get_orderbook": "Get Orderbook",
    "get_transaction_history": "Get Transaction History"
}


router = APIRouter()


# Регистрация: создаём пользователя с user_id и token
@router.post("/api/v1/public/register", tags=["public"], response_model=User, summary=summary_tags["register"])
def register(user: NewUser, db: Session = Depends(get_db)):
    if not check_username(user.name, db) is None:
        raise HTTPException(status_code=409, detail="Username already exists")

    token = generate_uuid()

    db_user = UserModel(
        id=generate_uuid(),
        name=user.name,
        role="USER",
        api_key=token
    )
    db.add(db_user)
    db.commit()

    return db_user


@router.get(path="/api/v1/public/instrument", tags=["public"], summary=summary_tags["list_instruments"])
def list_instruments():
    ...


@router.get(path="/api/v1/public/orderbook/{ticker}", tags=["public"], summary=summary_tags["get_orderbook"])
def get_orderbook():
    ...


@router.get(path="/api/v1/public/transactions/{ticker}", tags=["public"], summary=summary_tags["get_transaction_history"])
def get_transaction_history():
    ...
