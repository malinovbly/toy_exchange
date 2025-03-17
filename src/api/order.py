from fastapi import APIRouter


router = APIRouter()


@router.post(path="/api/v1/order", tags=["order"])
def create_order():
    ...


@router.get(path="/api/v1/order", tags=["order"])
def list_orders():
    ...


@router.get(path="/api/v1/order/{order_id}", tags=["order"])
def get_order():
    ...


@router.delete(path="/api/v1/order/{order_id}", tags=["order"])
def cancel_order():
    ...
