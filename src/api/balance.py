# src/api/balance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Dict

from src.utils import get_user_by_api_key, get_balances_by_user_id, get_api_key
from src.security import api_key_header
from src.database.database import get_db


summary_tags = {
    "get_balances": "Get Balances"
}

router = APIRouter()


@router.get(
    path="/api/v1/balance",
    tags=["balance"],
    response_model=Dict[str, int],
    summary=summary_tags["get_balances"]
)
async def get_balances(
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        auth_user = await get_user_by_api_key(UUID(api_key), db)
        if auth_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return await get_balances_by_user_id(auth_user.id, db)

    except Exception:
        raise HTTPException(status_code=404, detail="Invalid Authorization")