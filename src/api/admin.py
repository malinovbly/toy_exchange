from fastapi import APIRouter


router = APIRouter()


@router.post(path="/api/v1/admin/instrument", tags=["admin"])
def add_instrument():
    ...


@router.delete(path="/api/v1/admin/instrument/{ticker}", tags=["admin"])
def delete_instrument():
    ...
