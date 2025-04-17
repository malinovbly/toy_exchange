# src/api/public.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from src.schemas.schemas import NewUser, User, Instrument
from src.models.user import UserModel
from src.utils import (generate_uuid,
                       check_username,
                       get_all_instruments,
                       register_new_user)
from src.database import get_db


summary_tags = {
    "register": "Register",
    "list_instruments": "List Instruments",
    "get_orderbook": "Get Orderbook",
    "get_transaction_history": "Get Transaction History"
}


router = APIRouter()


@router.post("/api/v1/public/register", tags=["public"], response_model=User, summary=summary_tags["register"])
def register(user: NewUser, db: Session = Depends(get_db)):
    if check_username(user.name, db) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    return register_new_user(user, db)


@router.get(path="/api/v1/public/instrument", tags=["public"], response_model=List[Instrument], summary=summary_tags["list_instruments"])
def list_instruments(db: Session = Depends(get_db)):
    return get_all_instruments(db)


@router.get(path="/api/v1/public/orderbook/{ticker}", tags=["public"], summary=summary_tags["get_orderbook"])
def get_orderbook():
    ...


@router.get(path="/api/v1/public/transactions/{ticker}", tags=["public"], summary=summary_tags["get_transaction_history"])
def get_transaction_history():
    ...
