# src/main.py
from fastapi import FastAPI
from src.api import main_router
from src.dependency import get_db
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


app = FastAPI(openapi_tags=global_tags)
app.include_router(main_router)