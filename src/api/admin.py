# src/api/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database.database import get_db
from src.security import api_key_header
from src.schemas.schemas import (
    User,
    Instrument,
    Ok,
    Body_deposit_api_v1_admin_balance_deposit_post,
    Body_withdraw_api_v1_admin_balance_withdraw_post,
)
from src.utils import (
    check_user_is_admin,
    delete_user_by_id,
    create_instrument,
    delete_instrument_by_ticker,
    user_balance_deposit,
    user_balance_withdraw,
    get_api_key
)

from src.logger import logger


summary_tags = {
    "delete_user": "Delete User",
    "add_instrument": "Add Instrument",
    "delete_instrument": "Delete Instrument",
    "deposit": "Deposit",
    "withdraw": "Withdraw"
}

router = APIRouter()


@router.delete(
    path="/api/v1/admin/user/{user_id}",
    tags=["admin", "user"],
    response_model=User,
    summary=summary_tags["delete_user"]
)
async def delete_user(
        user_id: str,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        if await check_user_is_admin(UUID(api_key), db):
            return await delete_user_by_id(UUID(user_id), db)

    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post(
    path="/api/v1/admin/instrument",
    tags=["admin"],
    response_model=Ok,
    summary=summary_tags["add_instrument"]
)
async def add_instrument(
        instrument: Instrument,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        if await check_user_is_admin(UUID(api_key), db):
            await create_instrument(instrument, db)
        return Ok()

    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.delete(
    path="/api/v1/admin/instrument/{ticker}",
    tags=["admin"],
    response_model=Ok,
    summary=summary_tags["delete_instrument"]
)
async def delete_instrument(
        ticker: str,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        if await check_user_is_admin(UUID(api_key), db):
            await delete_instrument_by_ticker(ticker, db)
            return Ok()

    except Exception:
        logger.exception("DELETE INSTRUMENT ERROR")
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post(
    path="/api/v1/admin/balance/deposit",
    tags=["admin", "balance"],
    response_model=Ok,
    summary=summary_tags["deposit"]
)
async def deposit(
        request: Body_deposit_api_v1_admin_balance_deposit_post,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        if await check_user_is_admin(UUID(api_key), db):
            await user_balance_deposit(request, db)
            return Ok()

    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post(
    path="/api/v1/admin/balance/withdraw",
    tags=["admin", "balance"],
    response_model=Ok,
    summary=summary_tags["withdraw"]
)
async def withdraw(
        request: Body_withdraw_api_v1_admin_balance_withdraw_post,
        authorization: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        api_key = get_api_key(authorization)
        if await check_user_is_admin(UUID(api_key), db):
            await user_balance_withdraw(request, db)
            return Ok()

    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")
