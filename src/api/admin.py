from fastapi import APIRouter


summary_tags = {
    "delete_user": "Delete User",
    "add_instrument": "Add Instrument",
    "delete_instrument": "Delete Instrument",
    "deposit": "Deposit",
    "withdraw": "Withdraw"
}

router = APIRouter()


@router.delete(path="/api/v1/admin/user/{user_id}", tags=["admin", "user"], summary=summary_tags["delete_user"])
def delete_user():
    ...


@router.post(path="/api/v1/admin/instrument", tags=["admin"], summary=summary_tags["add_instrument"])
def add_instrument():
    ...


@router.delete(path="/api/v1/admin/instrument/{ticker}", tags=["admin"], summary=summary_tags["delete_instrument"])
def delete_instrument():
    ...


@router.post(path="/api/v1/admin/balance/deposit", tags=["admin"], summary=summary_tags["deposit"])
def deposit():
    ...


@router.post(path="/api/v1/admin/balance/withdraw", tags=["admin"], summary=summary_tags["withdraw"])
def withdraw():
    ...
