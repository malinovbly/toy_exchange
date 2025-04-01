from fastapi import APIRouter
from .public import router as public_router
from .balance import router as balance_router
from .order import router as order_router
from .admin import router as admin_router

router = APIRouter()

router.include_router(public_router)
router.include_router(balance_router, prefix="/balances", tags=["Balances"])
router.include_router(order_router, prefix="/orders", tags=["Orders"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
