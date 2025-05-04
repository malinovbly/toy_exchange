# src/utils.py
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.schemas.schemas import (NewUser,
                                 Instrument,
                                 Body_deposit_api_v1_admin_balance_deposit_post,
                                 Body_withdraw_api_v1_admin_balance_withdraw_post,
                                 )
from src.schemas.schemas import LimitOrderBody, MarketOrderBody, OrderStatus as SchemaOrderStatus
from src.models.user import UserModel
from src.models.instrument import InstrumentModel
from src.models.balance import BalanceModel
from src.models.order import OrderModel, OrderStatus, Direction
from src.database import get_db
from src.security import api_key_header
from src.models.order import OrderStatus


from src.models.user import UserModel
from sqlalchemy.orm import Session
from src.database import get_db
from fastapi import Depends, HTTPException, Security, APIRouter

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

# тот самый старый get_current_user
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
# прочесать позже и объединить с импортами в начале
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends
from src.models.order import OrderModel, OrderStatus, Direction
from src.schemas.schemas import LimitOrderBody, MarketOrderBody, OrderStatus as SchemaOrderStatus
from src.database import get_db
from typing import Optional, Union

def create_order_in_db(order_data: Union[LimitOrderBody, MarketOrderBody], user_id: UUID, db: Session = Depends(get_db)):
    db_order = OrderModel(
        id=uuid4(),
        user_id=user_id,
        timestamp=datetime.utcnow(),
        direction=order_data.direction,
        ticker=order_data.ticker,
        qty=order_data.qty,
        status=OrderStatus.NEW,
        filled=0
    )
    
    if isinstance(order_data, LimitOrderBody):
        db_order.price = order_data.price
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order_by_id(order_id: UUID, db: Session = Depends(get_db)):
    return db.query(OrderModel).filter(OrderModel.id == order_id).first()


def delete_order_by_id(order_id: UUID, db: Session = Depends(get_db)):
    db_order = get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    db.delete(db_order)
    db.commit()
    return db_order


def get_orders_by_user(user_id: UUID, db: Session = Depends(get_db)):
    return db.query(OrderModel).filter(OrderModel.user_id == user_id).all()


def cancel_order(order_id: UUID, db: Session = Depends(get_db)):
    db_order = get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    
    if db_order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
        raise HTTPException(
            status_code=400,
            detail="Only NEW or PARTIALLY_EXECUTED orders can be cancelled"
        )
    
    db_order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(db_order)
    return db_order


def list_all_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

def update_order_status(
    order_id: UUID, 
    new_status: SchemaOrderStatus,
    filled_qty: Optional[int] = None,
    db: Session = Depends(get_db)
):
    db_order = get_order_by_id(order_id, db)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order Not Found")
    
    db_order.status = new_status
    if filled_qty is not None:
        db_order.filled = filled_qty
    
    db.commit()
    db.refresh(db_order)
    return db_order


def get_orders_by_ticker(ticker: str, db: Session = Depends(get_db)):
    return db.query(OrderModel).filter(OrderModel.ticker == ticker).all()


def get_active_orders_by_ticker(ticker: str, db: Session = Depends(get_db)):
    return db.query(OrderModel).filter(
        OrderModel.ticker == ticker,
        OrderModel.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
    ).all()

# тут была попытка обновлять баланс по заказам, не совсем доделано
def update_user_balance(
    db: Session,
    user_id: UUID,
    ticker: str,
    amount_change: int
) -> BalanceModel:
    balance = db.query(BalanceModel).filter(
        BalanceModel.user_id == str(user_id),
        BalanceModel.instrument_ticker == ticker
    ).first()

    if not balance:
        balance = BalanceModel(
            user_id=str(user_id),
            instrument_ticker=ticker,
            amount=0
        )
        db.add(balance)

    new_amount = balance.amount + amount_change
    if new_amount < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance for {ticker}"
        )
    balance.amount = new_amount
    db.commit()
    db.refresh(balance)
    return balance

