from fastapi import FastAPI
from src.router import router

global_tags = [
    {"name": "public"},
    {"name": "balance"},
    {"name": "order"},
    {"name": "admin"}
]

app = FastAPI(openapi_tags=global_tags)
app.include_router(router)


