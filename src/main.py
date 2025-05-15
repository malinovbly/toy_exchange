# src/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.api import main_router
from src.database import engine, Base, SessionLocal
from src.models.instrument import InstrumentModel


global_tags = [
    {
        "name": "public"
    },
    {
        "name": "balance"
    },
    {
        "name": "order"
    },
    {
        "name": "admin"
    }
]


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db_ticker = db.query(InstrumentModel).filter_by(ticker="RUB").first()
        if db_ticker is None:
            rub_ticker = InstrumentModel(name="rubles", ticker="RUB")
            db.add(rub_ticker)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan, openapi_tags=global_tags)
app.include_router(main_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
