# src/api/balance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from src.utils import get_user_by_api_key, get_balances_by_user_id
from src.security import api_key_header
from src.database import get_db


summary_tags = {
    "get_balances": "Get Balances"
}

router = APIRouter()


@router.get(path="/api/v1/balance", tags=["balance"], response_model=Dict[str, int], summary=summary_tags["get_balances"])
def get_balances(authorization: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_user = get_user_by_api_key(authorization, db)
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return get_balances_by_user_id(auth_user.id, db)
