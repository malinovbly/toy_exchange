from fastapi import APIRouter


router = APIRouter()


@router.get(path="/api/v1/public/instrument", tags=["public"])
def list_instruments():
    ...


@router.get(path="/api/v1/public/orderbook/{ticker}", tags=["public"])
def get_orderbook():
    ...


@router.get(path="/api/v1/public/transactions/{ticker}", tags=["public"])
def get_transaction_history():
    ...
