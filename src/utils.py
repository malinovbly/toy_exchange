# src/utils.py
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.schemas.schemas import (NewUser,
                                 Instrument,
                                 Body_deposit_api_v1_admin_balance_deposit_post,
                                 Body_withdraw_api_v1_admin_balance_withdraw_post,
                                 Order)
from src.models.user import UserModel
from src.models.instrument import InstrumentModel
from src.models.balance import BalanceModel
from src.models.order import OrderModel
from src.database import get_db
from src.security import api_key_header
from src.models.order import OrderStatus


def generate_uuid():
    return str(uuid4())


# users
def register_new_user(user: NewUser, db: Session = Depends(get_db)):
    user_id = generate_uuid()
    token = generate_uuid()

    db_user = UserModel(
        id=user_id,
        name=user.name,
        role="USER",
        api_key=token
    )
    db.add(db_user)
    db.commit()

    return db_user


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


def get_all_instruments(db: Session = Depends(get_db)):
    return db.query(InstrumentModel).all()


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
def get_balances_by_user_id(user_id: str, db: Session = Depends(get_db)):
    db_balances = db.query(BalanceModel).filter_by(user_id=user_id).all()
    balances = {b.instrument_ticker: b.amount for b in db_balances}
    return balances


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


# orders
def create_order_in_db(order: Order, db: Session = Depends(get_db)):
    db_order = OrderModel(
        order_id=uuid4(),  # сразу UUID, без str()
        user_id=UUID(order.user_id),  # преобразуем строку в UUID
        symbol=order.symbol,
        order_type=order.order_type,
        side=order.side,
        quantity=order.quantity,
        price=order.price,
        status=OrderStatus.PENDING
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_order_by_id(order_id: str, db: Session = Depends(get_db)):
    return db.query(OrderModel).filter_by(order_id=order_id).first()


def delete_order_by_id(order_id: str, db: Session = Depends(get_db)):
    db_order = get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    db.delete(db_order)
    db.commit()
    return db_order

def get_orders_by_user(cur_user_id: UUID, db: Session):
    return db.query(OrderModel).filter_by(user_id=cur_user_id).all()

def cancel_order(order_id: str, db: Session = Depends(get_db)):
    db_order = db.query(OrderModel).filter_by(order_id=order_id).first()
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    db_order.status = OrderStatus.CANCELLED
    db.commit()
    return db_order

def list_all_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

def update_balance(user_id: str, ticker: str, new_amount: float, db: Session = Depends(get_db)):
    record = check_balance_record(user_id=user_id, ticker=ticker, db=db)
    
    if record:
        record.amount = new_amount
        db.commit()
        return record
    else:
        raise HTTPException(status_code=404, detail="Balance record not found")