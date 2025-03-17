from fastapi import APIRouter


router = APIRouter()


@router.get(path="/api/v1/balance", tags=["balance"])
def get_balances():
    ...


@router.post(path="/api/v1/balance/deposit", tags=["balance"])
def deposit():
    ...


@router.post(path="/api/v1/balance/withdraw", tags=["balance"])
def withdraw():
    ...
