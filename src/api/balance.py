# src/api/balance.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from uuid import UUID
from pydantic import BaseModel
from src.database import InMemoryDatabase
from decimal import Decimal


router = APIRouter()


@router.get(path="/api/v1/balance/{user_id}", tags=["balance"], response_model=Dict[str, float],
            summary="Get user balances")
def get_balances(user_id: UUID, db: InMemoryDatabase = Depends(lambda: InMemoryDatabase())):
    """
    Get the balances for all instruments for a given user.
    """
    balances = db.get_balances(user_id)
    return balances


@router.post(path="/api/v1/balance/deposit", tags=["balance"])
def deposit():
    ...


@router.post(path="/api/v1/balance/withdraw", tags=["balance"])
def withdraw():
    ...
