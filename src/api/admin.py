from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src import models, schemas, security  # Исправленный импорт
from src.database import get_db

router = APIRouter()


router = APIRouter()

async def get_admin_user(db: Session = Depends(get_db), token: str = Depends(security.bearer_scheme)):
    # Implement your admin token validation logic here
    # This is a VERY simplified example
    token_str = token.credentials.split(" ")[-1]
    if token_str != "YOUR_ADMIN_TOKEN":  # Replace with a real admin token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token"
        )
    return True

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), is_admin: bool = Depends(get_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

@router.put("/balances/{user_id}/{instrument_id}")
async def update_balance(
    user_id: int,
    instrument_id: int,
    amount: float,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user),
):
    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id, models.Balance.instrument_id == instrument_id)
        .first()
    )
    if not balance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Balance not found")
    balance.amount = amount
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return {"message": "Balance updated"}

@router.post("/instruments", response_model=schemas.Instrument)
async def create_instrument(
    instrument: schemas.InstrumentCreate,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user),
):
    db_instrument = models.Instrument(**instrument.dict())
    db.add(db_instrument)
    db.commit()
    db.refresh(db_instrument)
    return db_instrument

@router.delete("/instruments/{instrument_id}")
async def delete_instrument(
    instrument_id: int,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(get_admin_user),
):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    db.delete(instrument)
    db.commit()
    return {"message": "Instrument deleted"}