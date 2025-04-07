from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.schemas.schemas import User
from src.models.user import UserModel
from src.database import get_db


summary_tags = {
    "delete_user": "Delete User",
    "add_instrument": "Add Instrument",
    "delete_instrument": "Delete Instrument",
    "deposit": "Deposit",
    "withdraw": "Withdraw"
}

router = APIRouter()


@router.delete(path="/api/v1/admin/user/{user_id}", tags=["admin", "user"], response_model=User, summary=summary_tags["delete_user"])
def delete_user(user_id: str, authorization: str = None, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter_by(id=user_id).first()

    if db_user:
        db.delete(db_user)
        db.commit()
        return db_user

    raise HTTPException(status_code=422, detail="Validation Error")


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
