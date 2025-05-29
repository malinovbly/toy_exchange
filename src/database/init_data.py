from sqlalchemy.orm import Session
from uuid import uuid4

from src.database.database import engine, Base, SessionLocal
from src.models.instrument import InstrumentModel
from src.models.user import UserModel


rub_ticker = {
    "name": "rubles",
    "ticker": "RUB"
}


def create_admin(db: Session):
    if db.query(UserModel).filter_by(name="admin").first() is None:
        admin = UserModel(
            id=uuid4(),
            name="admin",
            role="ADMIN",
            api_key="175b6f1fc25c47e69ff73442f96298ae"
        )
        db.add(admin)
        db.commit()
        print("Admin created")
    else:
        print("Admin already exists")


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db_ticker = db.query(InstrumentModel).filter_by(ticker=rub_ticker["ticker"]).first()
        if db_ticker is None:
            new_ticker = InstrumentModel(name=rub_ticker["name"], ticker=rub_ticker["ticker"])
            db.add(new_ticker)

        create_admin(db)
        db.commit()

    finally:
        db.close()
