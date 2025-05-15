from database.database import engine, Base, SessionLocal
from src.models.instrument import InstrumentModel


rub_ticker = {
    "name": "rubles",
    "ticker": "RUB"
}


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db_ticker = db.query(InstrumentModel).filter_by(ticker=rub_ticker["ticker"]).first()
        if db_ticker is None:
            new_ticker = InstrumentModel(name=rub_ticker["name"], ticker=rub_ticker["ticker"])
            db.add(new_ticker)
            db.commit()
    finally:
        db.close()
