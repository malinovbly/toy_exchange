from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src import models, schemas, security  # Исправленный импорт
from src.database import get_db
from typing import List  # Добавляем импорт List
router = APIRouter()

# ... (остальной код)

@router.get("/", response_model=List[schemas.BalanceRead])
async def get_balances(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    balances = db.query(models.Balance).filter(models.Balance.user_id == user.id).all()
    return [
        schemas.BalanceRead(instrument_id=balance.instrument_id, ticker=balance.instrument.ticker, amount=balance.amount)
        for balance in balances
    ]