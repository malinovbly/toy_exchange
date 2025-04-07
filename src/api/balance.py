# src/api/balance.py
from fastapi import APIRouter, Depends
from typing import Dict
from uuid import UUID

from src.database import InMemoryDatabase


summary_tags = {
    "get_balances": "Get Balances",
    "deposit": "Deposit",
    "withdraw": "Withdraw"
}


router = APIRouter()


@router.get(path="/api/v1/balance/{user_id}", tags=["balance"], response_model=Dict[str, float], summary=summary_tags["get_balances"])
def get_balances(user_id: UUID, db: InMemoryDatabase = Depends(lambda: InMemoryDatabase())):
    """
    Get the balances for all instruments for a given user.
    """
    balances = db.get_balances(user_id)
    return balances


@router.post(path="/api/v1/balance/deposit", tags=["balance"], summary=summary_tags["deposit"])
def deposit():
    ...


@router.post(path="/api/v1/balance/withdraw", tags=["balance"], summary=summary_tags["withdraw"])
def withdraw():
    ...
