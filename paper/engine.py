from typing import List, Dict, Optional
from sqlmodel import Session, select
from storage.db import engine as db_engine
from storage.models import (
    PaperOrder, PaperFill, PaperPosition, OrderStatus, 
    Action, OrderType, ExecutionMode, Broker, EventLog
)
from marketdata.quote_store import quote_store
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

class PaperEngine:
    def __init__(self):
        self.pending_orders: List[PaperOrder] = []
        self._lock = asyncio.Lock()

    async def load_pending_orders(self):
        async with self._lock:
            with Session(db_engine) as session:
                self.pending_orders = session.exec(
                    select(PaperOrder).where(PaperOrder.status == OrderStatus.PENDING)
                ).all()
            logger.info(f"Loaded {len(self.pending_orders)} pending orders")

    def _log_event(self, session: Session, user_id: int, event_type: str, description: str, broker: Broker, broker_account_id: str):
        event = EventLog(
            user_id=user_id,
            event_type=event_type,
            description=description,
            broker=broker,
            broker_account_id=broker_account_id
        )
        session.add(event)

    def on_price_update(self, symbol: str, price: float):
        # symbol here is the broker's symbol code (e.g. "2330")
        to_fill = []
        for order in self.pending_orders:
            if order.symbol_code != symbol:
                continue
            
            should_fill = False
            if order.order_type == OrderType.MKT:
                should_fill = True
            elif order.order_type == OrderType.LMT:
                if order.action == Action.BUY and price <= order.price:
                    should_fill = True
                elif order.action == Action.SELL and price >= order.price:
                    should_fill = True
            
            if should_fill:
                to_fill.append((order, price))

        if to_fill:
            for order, fill_price in to_fill:
                self.execute_fill(order, fill_price)

    def execute_fill(self, order: PaperOrder, price: float):
        with Session(db_engine) as session:
            db_order = session.get(PaperOrder, order.id)
            if not db_order or db_order.status != OrderStatus.PENDING:
                return

            fill = PaperFill(
                order_id=db_order.id,
                user_id=db_order.user_id,
                broker=db_order.broker,
                broker_account_id=db_order.broker_account_id,
                normalized_symbol=db_order.normalized_symbol,
                symbol_code=db_order.symbol_code,
                quantity=db_order.quantity,
                price=price,
                commission=0.0
            )
            session.add(fill)

            db_order.status = OrderStatus.FILLED
            session.add(db_order)

            self._log_event(
                session, db_order.user_id, "PAPER_ORDER_FILLED",
                f"Filled {db_order.action} {db_order.quantity} {db_order.normalized_symbol} at {price}",
                db_order.broker, db_order.broker_account_id
            )

            pos = session.exec(
                select(PaperPosition)
                .where(PaperPosition.user_id == db_order.user_id)
                .where(PaperPosition.normalized_symbol == db_order.normalized_symbol)
            ).first()

            if not pos:
                pos = PaperPosition(
                    user_id=db_order.user_id,
                    broker=db_order.broker,
                    broker_account_id=db_order.broker_account_id,
                    normalized_symbol=db_order.normalized_symbol,
                    symbol_code=db_order.symbol_code,
                    quantity=0,
                    average_cost=0.0,
                    realized_pnl=0.0
                )

            old_qty = pos.quantity
            new_qty = old_qty + (db_order.quantity if db_order.action == Action.BUY else -db_order.quantity)
            
            if old_qty == 0:
                pos.average_cost = price
                pos.quantity = new_qty
            elif (old_qty > 0 and db_order.action == Action.BUY) or (old_qty < 0 and db_order.action == Action.SELL):
                pos.average_cost = (pos.average_cost * abs(old_qty) + price * db_order.quantity) / abs(new_qty)
                pos.quantity = new_qty
            else:
                fill_qty = db_order.quantity
                if abs(old_qty) >= fill_qty:
                    pnl = (price - pos.average_cost) * fill_qty if old_qty > 0 else (pos.average_cost - price) * fill_qty
                    pos.realized_pnl += pnl
                    pos.quantity = new_qty
                else:
                    pnl = (price - pos.average_cost) * abs(old_qty) if old_qty > 0 else (pos.average_cost - price) * abs(old_qty)
                    pos.realized_pnl += pnl
                    pos.quantity = new_qty
                    pos.average_cost = price
            
            session.add(pos)
            session.commit()
            
            self.pending_orders = [o for o in self.pending_orders if o.id != order.id]
            logger.info(f"Filled order {order.id} for {order.normalized_symbol} at {price}")

    async def place_order(self, order: PaperOrder):
        with Session(db_engine) as session:
            # Ensure PAPER mode for v1
            order.execution_mode = ExecutionMode.PAPER
            session.add(order)
            session.commit()
            session.refresh(order)
            self.pending_orders.append(order)
            
            self._log_event(
                session, order.user_id, "PAPER_ORDER_CREATED",
                f"Created {order.action} {order.quantity} {order.normalized_symbol} ({order.order_type})",
                order.broker, order.broker_account_id
            )
            session.commit()
            
            quote = quote_store.get_quote(order.symbol_code)
            if order.order_type == OrderType.MKT and quote and quote.last_price > 0:
                self.execute_fill(order, quote.last_price)
            
            return order

    async def cancel_order(self, order_id: int):
        with Session(db_engine) as session:
            db_order = session.get(PaperOrder, order_id)
            if db_order and db_order.status == OrderStatus.PENDING:
                db_order.status = OrderStatus.CANCELLED
                session.add(db_order)
                
                self._log_event(
                    session, db_order.user_id, "PAPER_ORDER_CANCELLED",
                    f"Cancelled {db_order.action} {db_order.quantity} {db_order.normalized_symbol}",
                    db_order.broker, db_order.broker_account_id
                )
                session.commit()
                self.pending_orders = [o for o in self.pending_orders if o.id != order_id]
                return True
        return False

    async def cancel_all_orders(self, user_id: int):
        with Session(db_engine) as session:
            pending = session.exec(
                select(PaperOrder).where(PaperOrder.user_id == user_id).where(PaperOrder.status == OrderStatus.PENDING)
            ).all()
            for order in pending:
                order.status = OrderStatus.CANCELLED
                session.add(order)
                self._log_event(
                    session, order.user_id, "PAPER_ORDER_CANCELALL",
                    f"Cancelled all pending orders for user {user_id}",
                    order.broker, order.broker_account_id
                )
            session.commit()
            self.pending_orders = [o for o in self.pending_orders if o.user_id != user_id]
            return len(pending)

paper_engine = PaperEngine()
