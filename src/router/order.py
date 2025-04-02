from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src import models, schemas, security  # Исправленный импорт
from src.database import get_db
from src import utils
from typing import List  # Добавляем импорт List

router = APIRouter()

# ... (остальной код)

@router.post("/", response_model=schemas.OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(order_create: schemas.OrderCreate, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    instrument = db.query(models.Instrument).filter(models.Instrument.id == order_create.instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    new_order = models.Order(
        user_id=user.id,
        instrument_id=order_create.instrument_id,
        order_type=order_create.order_type,
        price=order_create.price,
        quantity=order_create.quantity,
    )

    db.add(new_order)
    try:
        db.commit()
        db.refresh(new_order)
    except Exception as e:
        db.rollback()  # Rollback in case of error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create order: {e}")

    if order_create.order_type == models.OrderType.market:
        try:
            executed_order = utils.execute_market_order(new_order, db)
            return schemas.OrderRead.from_orm(executed_order)

        except HTTPException as e:
            db.delete(new_order)
            db.commit()
            raise e  # Re-raise the exception for the client

    elif order_create.order_type == models.OrderType.limit:
        try:
            executed_order = utils.execute_limit_order(new_order, db)
            return schemas.OrderRead.from_orm(executed_order)
        except HTTPException as e:
            db.delete(new_order)
            db.commit()
            raise e  # Re-raise the exception for the client

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order type")

@router.delete("/{order_id}")
async def cancel_order(order_id: int, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == user.id, models.Order.status == models.OrderStatus.open).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or cannot be cancelled")

    order.status = models.OrderStatus.cancelled
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"message": "Order cancelled"}

@router.get("/{order_id}", response_model=schemas.OrderRead)
async def get_order_status(order_id: int, user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return schemas.OrderRead.from_orm(order)

@router.get("/", response_model=List[schemas.OrderRead])
async def get_active_orders(user: models.User = Depends(security.get_current_user), db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(models.Order.user_id == user.id, models.Order.status == models.OrderStatus.open).all()
    return [schemas.OrderRead.from_orm(order) for order in orders]