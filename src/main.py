# src/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.api import main_router
from src.database.init_data import init_db


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan, openapi_tags=global_tags)
app.include_router(main_router)
