from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlmodel import Session, select
from storage.db import get_session
from storage.models import User, Watchlist, Broker, InstrumentType, EventLog
from api.auth import get_current_user
from broker.shioaji_client import shioaji_broker

router = APIRouter()

@router.get("/", response_model=List[Watchlist])
async def get_watchlist(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Watchlist).where(Watchlist.user_id == current_user.id)).all()

@router.post("/", response_model=Watchlist)
async def add_to_watchlist(symbol_code: str, broker: Broker = Broker.SHIOAJI, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # Check if already in watchlist
    existing = session.exec(
        select(Watchlist)
        .where(Watchlist.user_id == current_user.id)
        .where(Watchlist.symbol_code == symbol_code)
        .where(Watchlist.broker == broker)
    ).first()
    if existing:
        return existing
    
    # Use Shioaji broker for now
    if broker == Broker.SHIOAJI:
        contract = shioaji_broker.get_contract(symbol_code)
        if not contract:
            raise HTTPException(status_code=400, detail="Invalid symbol")
        
        normalized = shioaji_broker.normalize_symbol(symbol_code, contract.exchange)
        instrument_type = InstrumentType.STOCK if contract.security_type == "STK" else InstrumentType.FUTURES
        
        new_item = Watchlist(
            user_id=current_user.id,
            broker=broker,
            symbol_code=symbol_code,
            normalized_symbol=normalized,
            symbol_name=contract.name,
            exchange=contract.exchange,
            instrument_type=instrument_type,
            category=contract.category
        )
        session.add(new_item)
        
        # Log event
        event = EventLog(
            user_id=current_user.id,
            event_type="QUOTE_SUBSCRIBED",
            description=f"Subscribed to {normalized}",
            broker=broker
        )
        session.add(event)
        session.commit()
        session.refresh(new_item)
        
        # Subscribe to real-time data
        shioaji_broker.subscribe(symbol_code)
        return new_item
    else:
        raise HTTPException(status_code=400, detail="Broker not supported yet")

@router.delete("/{normalized_symbol}")
async def remove_from_watchlist(normalized_symbol: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    item = session.exec(
        select(Watchlist).where(Watchlist.user_id == current_user.id).where(Watchlist.normalized_symbol == normalized_symbol)
    ).first()
    if item:
        symbol_code = item.symbol_code
        broker = item.broker
        
        session.delete(item)
        
        event = EventLog(
            user_id=current_user.id,
            event_type="QUOTE_UNSUBSCRIBED",
            description=f"Unsubscribed from {normalized_symbol}",
            broker=broker
        )
        session.add(event)
        session.commit()
        
        # Check if anyone else is watching this symbol
        others = session.exec(select(Watchlist).where(Watchlist.normalized_symbol == normalized_symbol)).first()
        if not others:
            if broker == Broker.SHIOAJI:
                shioaji_broker.unsubscribe(symbol_code)
            
    return {"status": "success"}
