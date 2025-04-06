# src/database.py
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

    def get_order_by_id(self, order_id: UUID) -> Optional[Order]:
        """
        Gets an order by its ID.
        """
        for user_id in self.orders:
            for order in self.orders[user_id]:
                if order.order_id == order_id:
                    return order
        return None

    def get_orders_by_user(self, user_id: UUID) -> List[Order]:
        """
        Gets all orders for a specific user.
        """
        return self.orders.get(user_id, [])  # Return empty list if user has no orders

    def cancel_order(self, order_id: UUID) -> Optional[Order]:
        """
        Cancels an order.
        """
        for user_id in self.orders:
            for i, order in enumerate(self.orders[user_id]):
                if order.order_id == order_id:
                    if order.status == "filled":
                        return None  # Can't cancel a filled order
                    order.status = "cancelled"
                    return order
        return None

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
