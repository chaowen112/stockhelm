from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from marketdata.quote_store import quote_store, Quote
from broker.shioaji_client import shioaji_broker
from api.auth import get_current_user
from storage.models import User

router = APIRouter()

@router.get("/{symbol}", response_model=Quote)
async def get_quote(symbol: str, current_user: User = Depends(get_current_user)):
    quote = quote_store.get_quote(symbol)
    if not quote:
        # Try to get a snapshot if not subscribed
        snapshot = shioaji_broker.get_snapshot(symbol)
        if snapshot:
            # Mock a quote from snapshot
            return Quote(
                symbol=symbol,
                last_price=float(snapshot.get("close", 0)),
                volume=int(snapshot.get("volume", 0)),
                total_volume=int(snapshot.get("total_volume", 0)),
                bid_price=float(snapshot.get("bid_price", [0])[0]),
                ask_price=float(snapshot.get("ask_price", [0])[0])
            )
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote

@router.get("/", response_model=Dict[str, Quote])
async def get_all_quotes(current_user: User = Depends(get_current_user)):
    return quote_store.get_all_quotes()
