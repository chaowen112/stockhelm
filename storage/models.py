from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    LMT = "LMT"
    MKT = "MKT"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class ExecutionMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class Broker(str, Enum):
    SHIOAJI = "SHIOAJI"
    IBKR = "IBKR"

class InstrumentType(str, Enum):
    STOCK = "STOCK"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    telegram_chat_id: Optional[int] = None

class EventLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    event_type: str = Field(index=True)  # e.g., "ORDER_CREATED", "QUOTE_SUBSCRIBED"
    description: str
    broker: Optional[Broker] = None
    broker_account_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Watchlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    broker: Broker
    symbol_code: str  # Original symbol from broker
    normalized_symbol: str = Field(index=True)  # e.g., "SHIOAJI:2330:TSE"
    symbol_name: str
    exchange: str
    instrument_type: InstrumentType
    category: Optional[str] = None

class PaperOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    broker: Broker
    broker_account_id: str
    broker_order_id: Optional[str] = Field(default=None, index=True)
    normalized_symbol: str = Field(index=True)
    symbol_code: str
    action: Action
    quantity: int
    order_type: OrderType
    price: float
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    execution_mode: ExecutionMode = Field(default=ExecutionMode.PAPER)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    fills: List["PaperFill"] = Relationship(back_populates="order")

class PaperFill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="paperorder.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    broker: Broker
    broker_account_id: str
    normalized_symbol: str = Field(index=True)
    symbol_code: str
    quantity: int
    price: float
    commission: float = 0.0
    filled_at: datetime = Field(default_factory=datetime.utcnow)
    
    order: PaperOrder = Relationship(back_populates="fills")

class PaperPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    broker: Broker
    broker_account_id: str
    normalized_symbol: str = Field(index=True)
    symbol_code: str
    quantity: int = 0
    average_cost: float = 0.0
    realized_pnl: float = 0.0
