# src/utils.py
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from src.schemas.schemas import Instrument
from src.models.user import UserModel
from src.models.instrument import InstrumentModel
from src.database import get_db


def generate_uuid():
    return str(uuid4())


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


def check_instrument(instrument: Instrument, db: Session = Depends(get_db)):
    db_instrument = db.query(InstrumentModel).filter_by(name=instrument.name).first()
    if db_instrument is None:
        return db.query(InstrumentModel).filter_by(ticker=instrument.ticker).first()
    return db_instrument


def delete_instrument_by_ticker(ticker: str, db: Session = Depends(get_db)):
    db_instrument = db.query(InstrumentModel).filter_by(ticker=ticker).first()

    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Not Found")

    db.delete(db_instrument)
    db.commit()
