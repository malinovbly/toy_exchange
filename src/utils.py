# src/utils.py
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.schemas.schemas import (Instrument,
                                 Body_deposit_api_v1_admin_balance_deposit_post,
                                 Body_withdraw_api_v1_admin_balance_withdraw_post)
from src.models.user import UserModel
from src.models.instrument import InstrumentModel
from src.models.balance import BalanceModel
from src.database import get_db
from src.security import api_key_header


def generate_uuid():
    return str(uuid4())


# users
def check_user_is_admin(authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    auth_user = get_user_by_api_key(authorization, db)
    if (auth_user is None) or not (auth_user.role == "ADMIN"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


def check_username(username: str, db: Session = Depends(get_db)):
    return db.query(UserModel).filter_by(name=username).first()


def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    return db.query(UserModel).filter_by(id=user_id).first()


def get_user_by_api_key(api_key: str, db: Session = Depends(get_db)):
    return db.query(UserModel).filter_by(api_key=api_key).first()


def delete_user_by_id(user_id: str, db: Session = Depends(get_db)):
    db_user = get_user_by_id(user_id, db)

    if db_user is None:
        raise HTTPException(status_code=404, detail="Not Found")

    db.delete(db_user)
    db.commit()
    return db_user


# instruments
def check_instrument(instrument: Instrument, db: Session = Depends(get_db)):
    db_instrument = db.query(InstrumentModel).filter_by(name=instrument.name).first()
    if db_instrument is None:
        return db.query(InstrumentModel).filter_by(ticker=instrument.ticker).first()
    return db_instrument


def get_instrument_by_ticker(ticker: str, db: Session = Depends(get_db)):
    return db.query(InstrumentModel).filter_by(ticker=ticker).first()


def create_instrument(instrument: Instrument, db: Session = Depends(get_db)):
    if check_instrument(instrument, db) is not None:
        raise HTTPException(status_code=409, detail="Instrument already exists")

    db_instrument = InstrumentModel(
        name=instrument.name,
        ticker=instrument.ticker
    )
    db.add(db_instrument)
    db.commit()


def delete_instrument_by_ticker(ticker: str, db: Session = Depends(get_db)):
    db_instrument = db.query(InstrumentModel).filter_by(ticker=ticker).first()

    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Not Found")

    db.query(BalanceModel).filter_by(instrument_ticker=ticker).delete()
    db.delete(db_instrument)
    db.commit()


# balances
def check_balance_record(user_id: str, ticker: str, db: Session = Depends(get_db)):
    return db.query(BalanceModel).filter_by(user_id=user_id).filter_by(instrument_ticker=ticker).first()


def user_balance_deposit(request: Body_deposit_api_v1_admin_balance_deposit_post, db: Session = Depends(get_db)):
    if get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail="Ticker Not Found")

    record = check_balance_record(user_id=request.user_id, ticker=request.ticker, db=db)

    if record is not None:
        new_amount = record.amount + request.amount
        updated_record = (
            update(BalanceModel)
            .where(BalanceModel.user_id == record.user_id)
            .where(BalanceModel.instrument_ticker == record.instrument_ticker)
            .values(amount=new_amount)
        )
        db.execute(updated_record)
        db.commit()
    else:
        new_record = BalanceModel(
            user_id=request.user_id,
            instrument_ticker=request.ticker,
            amount=request.amount
        )
        db.add(new_record)
        db.commit()


def user_balance_withdraw(request: Body_withdraw_api_v1_admin_balance_withdraw_post, db: Session = Depends(get_db)):
    if get_user_by_id(request.user_id, db) is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    if get_instrument_by_ticker(request.ticker, db) is None:
        raise HTTPException(status_code=404, detail="Ticker Not Found")

    record = check_balance_record(user_id=request.user_id, ticker=request.ticker, db=db)

    if record is None:
        raise HTTPException(status_code=400, detail="Bad Request")
    else:
        new_amount = record.amount - request.amount
        if new_amount >= 0:
            updated_record = (
                update(BalanceModel)
                .where(BalanceModel.user_id == record.user_id)
                .where(BalanceModel.instrument_ticker == record.instrument_ticker)
                .values(amount=new_amount)
            )
            db.execute(updated_record)
            db.commit()
        else:
            raise HTTPException(status_code=403, detail="Insufficient Funds")
