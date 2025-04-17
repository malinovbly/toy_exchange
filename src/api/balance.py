# src/api/balance.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict

from src.database import get_db


summary_tags = {
    "get_balances": "Get Balances"
}


router = APIRouter()


@router.get(path="/api/v1/balance/{user_id}", tags=["balance"], response_model=Dict[str, float], summary=summary_tags["get_balances"])
def get_balances(db: Session = Depends(get_db)):
    ...
