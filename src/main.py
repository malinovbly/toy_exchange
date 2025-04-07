# src/main.py
from fastapi import FastAPI
from src.api import main_router

from src.database import engine, Base


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

Base.metadata.create_all(bind=engine)

app = FastAPI(openapi_tags=global_tags)
app.include_router(main_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
