# src/dependencies.py
from src.database import InMemoryDatabase

# Создать ОДИН экземпляр базы данных
db = InMemoryDatabase()


# Определить функцию-зависимость, которая возвращает этот ЖЕ экземпляр
def get_db():
    return db
