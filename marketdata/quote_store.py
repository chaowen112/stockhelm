from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Quote(BaseModel):
    symbol: str
    last_price: float = 0.0
    volume: int = 0
    total_volume: int = 0
    bid_price: float = 0.0
    bid_size: int = 0
    ask_price: float = 0.0
    ask_size: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteStore:
    def __init__(self):
        self._quotes: Dict[str, Quote] = {}

    def update_tick(self, symbol: str, price: float, volume: int, total_volume: int):
        if symbol not in self._quotes:
            self._quotes[symbol] = Quote(symbol=symbol)
        
        q = self._quotes[symbol]
        q.last_price = price
        q.volume = volume
        q.total_volume = total_volume
        q.updated_at = datetime.utcnow()

    def update_bidask(self, symbol: str, bid_price: float, bid_size: int, ask_price: float, ask_size: int):
        if symbol not in self._quotes:
            self._quotes[symbol] = Quote(symbol=symbol)
        
        q = self._quotes[symbol]
        q.bid_price = bid_price
        q.bid_size = bid_size
        q.ask_price = ask_price
        q.ask_size = ask_size
        q.updated_at = datetime.utcnow()

    def get_quote(self, symbol: str) -> Optional[Quote]:
        return self._quotes.get(symbol)

    def get_all_quotes(self) -> Dict[str, Quote]:
        return self._quotes

quote_store = QuoteStore()
