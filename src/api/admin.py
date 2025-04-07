# src/api/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.schemas.schemas import User
from src.database import get_db
from src.utils import get_user_by_api_key, delete_user_by_id
from src.security import api_key_header


summary_tags = {
    "delete_user": "Delete User",
    "add_instrument": "Add Instrument",
    "delete_instrument": "Delete Instrument",
    "deposit": "Deposit",
    "withdraw": "Withdraw"
}

router = APIRouter()


@router.delete(path="/api/v1/admin/user/{user_id}", tags=["admin", "user"], response_model=User, summary=summary_tags["delete_user"])
def delete_user(user_id: str, authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_user = get_user_by_api_key(authorization, db)

    if (auth_user.role == "ADMIN") or (auth_user.id == user_id):
        return delete_user_by_id(user_id, db)

    raise HTTPException(status_code=403, detail="Forbidden")


@router.post(path="/api/v1/admin/instrument", tags=["admin"], summary=summary_tags["add_instrument"])
def add_instrument():
    ...


@router.delete(path="/api/v1/admin/instrument/{ticker}", tags=["admin"], summary=summary_tags["delete_instrument"])
def delete_instrument():
    ...


@router.post(path="/api/v1/admin/balance/deposit", tags=["admin"], summary=summary_tags["deposit"])
def deposit():
    ...


@router.post(path="/api/v1/admin/balance/withdraw", tags=["admin"], summary=summary_tags["withdraw"])
def withdraw():
    ...
