from fastapi import APIRouter
from src.api.public import router as public_router
from src.api.balance import router as balance_router
from src.api.order import router as order_router
from src.api.admin import router as admin_router
from src.api.auth import router as auth_router


main_router = APIRouter()

main_router.include_router(public_router)
main_router.include_router(balance_router)
main_router.include_router(order_router)
main_router.include_router(admin_router)
main_router.include_router(auth_router)
