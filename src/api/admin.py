# src/api/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from src.schemas.schemas import (User,
                                 Instrument,
                                 Ok,
                                 Body_deposit_api_v1_admin_balance_deposit_post,
                                 Body_withdraw_api_v1_admin_balance_withdraw_post)
from src.utils import (get_user_by_api_key,
                       check_user_is_admin,
                       delete_user_by_id,
                       create_instrument,
                       delete_instrument_by_ticker,
                       user_balance_deposit,
                       user_balance_withdraw)
from src.database import get_db
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

    auth_user = get_user_by_api_key(UUID(authorization), db)

    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if (auth_user.role == "ADMIN") or (auth_user.id == UUID(user_id)):
        return delete_user_by_id(UUID(user_id), db)

    raise HTTPException(status_code=403, detail="Forbidden")


@router.post(path="/api/v1/admin/instrument", tags=["admin"], response_model=Ok, summary=summary_tags["add_instrument"])
def add_instrument(instrument: Instrument, authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if check_user_is_admin(UUID(authorization), db):
        create_instrument(instrument, db)

    return Ok


@router.delete(path="/api/v1/admin/instrument/{ticker}", tags=["admin"], response_model=Ok, summary=summary_tags["delete_instrument"])
def delete_instrument(ticker: str, authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if check_user_is_admin(UUID(authorization), db):
        delete_instrument_by_ticker(ticker, db)

    return Ok


@router.post(path="/api/v1/admin/balance/deposit", tags=["admin", "balance"], response_model=Ok, summary=summary_tags["deposit"])
def deposit(request: Body_deposit_api_v1_admin_balance_deposit_post, authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if check_user_is_admin(UUID(authorization), db):
        user_balance_deposit(request, db)

    return Ok


@router.post(path="/api/v1/admin/balance/withdraw", tags=["admin", "balance"], response_model=Ok, summary=summary_tags["withdraw"])
def withdraw(request: Body_withdraw_api_v1_admin_balance_withdraw_post, authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if check_user_is_admin(UUID(authorization), db):
        user_balance_withdraw(request, db)

    return Ok
