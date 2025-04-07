# src/utils.py
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from src.models.user import UserModel
from src.database import get_db


def generate_uuid():
    return str(uuid4())


def check_username(username: str, db: Session = Depends(get_db)):
    return db.query(UserModel).filter_by(name=username).first()


def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter_by(id=user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Not Found")

    return db_user


def get_user_by_api_key(api_key: str, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter_by(api_key=api_key).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="Not Found")

    return db_user


def delete_user_by_id(user_id: str, db: Session = Depends(get_db)):
    db_user = get_user_by_id(user_id, db)

    if not db_user:
        raise HTTPException(status_code=404, detail="Not Found")

    db.delete(db_user)
    db.commit()
    return db_user
