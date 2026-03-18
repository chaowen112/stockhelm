from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from storage.models import Broker, InstrumentType

class AbstractBroker(ABC):
    @property
    @abstractmethod
    def broker_name(self) -> Broker:
        pass

    @abstractmethod
    def login(self) -> bool:
        pass

    @abstractmethod
    def logout(self) -> bool:
        pass

    @abstractmethod
    def get_contract(self, symbol: str) -> Any:
        pass

    @abstractmethod
    def get_snapshot(self, symbol: str) -> Any:
        pass

    @abstractmethod
    def subscribe(self, symbol: str) -> bool:
        pass

    @abstractmethod
    def unsubscribe(self, symbol: str) -> bool:
        pass

    @abstractmethod
    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Returns normalized symbol: BROKER:SYMBOL:EXCHANGE"""
        return f"{self.broker_name}:{symbol}:{exchange}"

    @abstractmethod
    def get_account_id(self) -> str:
        pass
