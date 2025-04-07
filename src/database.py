# src/database.py
from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = sqlalchemy.orm.declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from typing import List, Optional, Dict
from uuid import UUID
from src.models.order import Order
from collections import defaultdict


class InMemoryDatabase:
    def __init__(self):
        self.orders = defaultdict(list)  # {user_id: [Order, Order, ...]}
        self.balances: Dict[UUID, Dict[str, float]] = defaultdict(
            lambda: {"USD": 1000.0})  # {user_id: {symbol: balance}}

    def create_order(self, order: Order) -> Order:
        """
        Creates a new order.
        """
        self.orders[order.user_id].append(order)  # Store by user_id
        return order

    def get_balances(self, user_id: UUID) -> Dict[str, float]:
        """
        Gets all balances for a user.
        """
        return self.balances.get(user_id, {})

    def update_balance(self, user_id: UUID, symbol: str, amount: float):
        """
        Updates the balance for a given user and symbol.  Creates balance if it doesn't exist.
        """
        if user_id not in self.balances:
            self.balances[user_id] = {}
        if symbol not in self.balances[user_id]:
            self.balances[user_id][symbol] = 0.0
        self.balances[user_id][symbol] += amount
        return self.balances[user_id][symbol]

