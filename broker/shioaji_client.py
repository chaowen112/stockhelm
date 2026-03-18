import shioaji as sj
from typing import Optional, List, Dict, Any, Union
from config import settings
from marketdata.quote_store import quote_store
from broker.base import AbstractBroker
from storage.models import Broker
import logging

logger = logging.getLogger(__name__)

class ShioajiBroker(AbstractBroker):
    def __init__(self):
        self.api = sj.Shioaji()
        self.is_logged_in = False

    @property
    def broker_name(self) -> Broker:
        return Broker.SHIOAJI

    def login(self):
        try:
            self.api.login(
                api_key=settings.SHIOAJI_API_KEY,
                secret_key=settings.SHIOAJI_SECRET_KEY,
                subscribe_trade=False
            )
            self.is_logged_in = True
            self._setup_callbacks()
            logger.info("Shioaji login successful")
            return True
        except Exception as e:
            logger.error(f"Shioaji login failed: {e}")
            return False

    def logout(self):
        if self.is_logged_in:
            self.api.logout()
            self.is_logged_in = False
            return True
        return False

    def _setup_callbacks(self):
        @self.api.on_quote
        def quote_callback(topic, quote):
            try:
                symbol = topic.split("/")[-1]
                if "Tick" in topic:
                    price = float(getattr(quote, 'close', 0))
                    volume = int(getattr(quote, 'volume', 0))
                    total_volume = int(getattr(quote, 'total_volume', 0))
                    quote_store.update_tick(symbol, price, volume, total_volume)
                    
                    from paper.engine import paper_engine
                    paper_engine.on_price_update(symbol, price)
                    
                elif "BidAsk" in topic:
                    bid_prices = getattr(quote, 'bid_price', [0])
                    bid_volumes = getattr(quote, 'bid_volume', [0])
                    ask_prices = getattr(quote, 'ask_price', [0])
                    ask_volumes = getattr(quote, 'ask_volume', [0])
                    
                    quote_store.update_bidask(
                        symbol=symbol,
                        bid_price=float(bid_prices[0]) if bid_prices else 0,
                        bid_size=int(bid_volumes[0]) if bid_volumes else 0,
                        ask_price=float(ask_prices[0]) if ask_prices else 0,
                        ask_size=int(ask_volumes[0]) if ask_volumes else 0
                    )
            except Exception as e:
                logger.error(f"Error in Shioaji quote callback: {e}")

    def get_contract(self, symbol: str):
        try:
            contract = self.api.Contracts.Stocks[symbol]
            if contract: return contract
        except:
            pass
        try:
            contract = self.api.Contracts.Futures[symbol]
            if contract: return contract
        except:
            pass
        return None

    def get_snapshot(self, symbol: str):
        contract = self.get_contract(symbol)
        if contract:
            return self.api.snapshots([contract])[0]
        return None

    def subscribe(self, symbol: str):
        contract = self.get_contract(symbol)
        if contract:
            self.api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick)
            self.api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk)
            return True
        return False

    def unsubscribe(self, symbol: str):
        contract = self.get_contract(symbol)
        if contract:
            self.api.quote.unsubscribe(contract, quote_type=sj.constant.QuoteType.Tick)
            self.api.quote.unsubscribe(contract, quote_type=sj.constant.QuoteType.BidAsk)
            return True
        return False

    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        return f"{self.broker_name}:{symbol}:{exchange}"

    def get_account_id(self) -> str:
        # For Shioaji, use the primary stock account for now
        if self.api.stock_account:
            return self.api.stock_account.account_id
        return "PAPER_ACCT"

shioaji_broker = ShioajiBroker()
