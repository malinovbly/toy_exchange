# src/database/init_data.py
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database.database import async_engine, Base, AsyncSessionLocal
from src.models.instrument import InstrumentModel
from src.models.user import UserModel


rub_ticker = {
    "name": "rubles",
    "ticker": "RUB"
}


async def create_admin(db: AsyncSession):
    result = await db.execute(select(UserModel).filter_by(name="admin"))
    admin = result.scalar_one_or_none()
    if admin is None:
        new_admin = UserModel(
            id=uuid4(),
            name="admin",
            role="ADMIN",
            api_key="175b6f1fc25c47e69ff73442f96298ae"
        )
        db.add(new_admin)
        print("Admin created")
    else:
        print("Admin already exists")


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(InstrumentModel).filter_by(ticker=rub_ticker["ticker"]))
        ticker = result.scalar_one_or_none()
        if ticker is None:
            new_ticker = InstrumentModel(
                name=rub_ticker["name"],
                ticker=rub_ticker["ticker"]
            )
            db.add(new_ticker)

        await create_admin(db)
        await db.commit()
