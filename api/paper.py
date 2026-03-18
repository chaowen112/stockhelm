from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import Session, select
from storage.db import get_session
from storage.models import (
    User, PaperOrder, PaperFill, PaperPosition, 
    Action, OrderType, OrderStatus, Broker, ExecutionMode
)
from api.auth import get_current_user
from paper.engine import paper_engine
from broker.shioaji_client import shioaji_broker
from pydantic import BaseModel

router = APIRouter()

class OrderRequest(BaseModel):
    broker: Broker = Broker.SHIOAJI
    symbol_code: str
    action: Action
    quantity: int
    order_type: OrderType
    price: float = 0.0

@router.post("/orders", response_model=PaperOrder)
async def place_order(req: OrderRequest, current_user: User = Depends(get_current_user)):
    # Find normalized symbol and account info
    if req.broker == Broker.SHIOAJI:
        contract = shioaji_broker.get_contract(req.symbol_code)
        if not contract:
            raise HTTPException(status_code=400, detail="Invalid symbol")
        
        normalized = shioaji_broker.normalize_symbol(req.symbol_code, contract.exchange)
        account_id = shioaji_broker.get_account_id()
    else:
        raise HTTPException(status_code=400, detail="Broker not supported")

    order = PaperOrder(
        user_id=current_user.id,
        broker=req.broker,
        broker_account_id=account_id,
        normalized_symbol=normalized,
        symbol_code=req.symbol_code,
        action=req.action,
        quantity=req.quantity,
        order_type=req.order_type,
        price=req.price,
        status=OrderStatus.PENDING,
        execution_mode=ExecutionMode.PAPER
    )
    return await paper_engine.place_order(order)

@router.get("/orders", response_model=List[PaperOrder])
async def get_orders(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(PaperOrder).where(PaperOrder.user_id == current_user.id)).all()

@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, current_user: User = Depends(get_current_user)):
    success = await paper_engine.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or not cancellable")
    return {"status": "cancelled"}

@router.post("/orders/cancel-all")
async def cancel_all_orders(current_user: User = Depends(get_current_user)):
    count = await paper_engine.cancel_all_orders(current_user.id)
    return {"status": "success", "cancelled_count": count}

@router.get("/positions", response_model=List[PaperPosition])
async def get_positions(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(PaperPosition).where(PaperPosition.user_id == current_user.id)).all()

@router.get("/fills", response_model=List[PaperFill])
async def get_fills(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(PaperFill).where(PaperFill.user_id == current_user.id)).all()

@router.get("/pnl")
async def get_pnl(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    positions = session.exec(select(PaperPosition).where(PaperPosition.user_id == current_user.id)).all()
    realized_pnl = sum(p.realized_pnl for p in positions)
    
    unrealized_pnl = 0.0
    from marketdata.quote_store import quote_store
    for p in positions:
        if p.quantity == 0: continue
        quote = quote_store.get_quote(p.symbol_code)
        if quote and quote.last_price > 0:
            upnl = (quote.last_price - p.average_cost) * p.quantity
            unrealized_pnl += upnl
            
    return {
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl
    }
