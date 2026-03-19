from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import settings
from broker.shioaji_client import shioaji_broker
from sqlmodel import Session, select
from storage.db import engine as db_engine
from storage.models import User, Watchlist, Broker, InstrumentType, EventLog
import logging
import asyncio

logger = logging.getLogger(__name__)

async def check_allowlist(update: Update):
    chat_id = update.effective_chat.id
    if chat_id not in settings.telegram_allowlist_ids:
        await update.message.reply_text("Access denied.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_allowlist(update): return
    await update.message.reply_text("Welcome to StockHelm Bot! Use /quote <symbol> to get prices.")

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_allowlist(update): return
    if not context.args:
        await update.message.reply_text("Usage: /quote <symbol>")
        return
    
    symbol = context.args[0]
    snapshot = shioaji_broker.get_snapshot(symbol)
    if not snapshot:
        await update.message.reply_text(f"Symbol {symbol} not found.")
        return
    
    name = snapshot.get("name", symbol)
    last = snapshot.get("close", 0)
    change = snapshot.get("change_price", 0)
    pct = snapshot.get("change_rate", 0)
    vol = snapshot.get("volume", 0)
    bid = snapshot.get("bid_price", [0])[0]
    ask = snapshot.get("ask_price", [0])[0]
    
    msg = (
        f"*{name} ({symbol})*\n"
        f"Price: {last} ({change} / {pct}%)\n"
        f"Vol: {vol}\n"
        f"B/A: {bid} / {ask}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_allowlist(update): return
    if not context.args:
        await update.message.reply_text("Usage: /watch <symbol>")
        return
    
    symbol = context.args[0]
    contract = shioaji_broker.get_contract(symbol)
    if not contract:
        await update.message.reply_text(f"Symbol {symbol} not found.")
        return

    with Session(db_engine) as session:
        admin = session.exec(select(User).where(User.username == settings.ADMIN_USERNAME)).first()
        if not admin:
            await update.message.reply_text("Admin user not found in DB.")
            return
            
        existing = session.exec(
            select(Watchlist)
            .where(Watchlist.user_id == admin.id)
            .where(Watchlist.symbol_code == symbol)
            .where(Watchlist.broker == Broker.SHIOAJI)
        ).first()
        if existing:
            await update.message.reply_text(f"{symbol} is already in watchlist.")
            return
            
        normalized = shioaji_broker.normalize_symbol(symbol, contract.exchange)
        instrument_type = InstrumentType.STOCK if contract.security_type == "STK" else InstrumentType.FUTURES
        
        new_item = Watchlist(
            user_id=admin.id,
            broker=Broker.SHIOAJI,
            symbol_code=symbol,
            normalized_symbol=normalized,
            symbol_name=contract.name,
            exchange=contract.exchange,
            instrument_type=instrument_type,
            category=contract.category
        )
        session.add(new_item)
        
        event = EventLog(
            user_id=admin.id,
            event_type="QUOTE_SUBSCRIBED",
            description=f"Telegram added {normalized}",
            broker=Broker.SHIOAJI
        )
        session.add(event)
        session.commit()
        shioaji_broker.subscribe(symbol)
        
    await update.message.reply_text(f"Added {contract.name} ({symbol}) to watchlist.")

async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_allowlist(update): return
    limit = 10
    if context.args:
        try: limit = int(context.args[0])
        except: pass

    with Session(db_engine) as session:
        logs = session.exec(
            select(EventLog).order_by(EventLog.created_at.desc()).limit(limit)
        ).all()
        if not logs:
            await update.message.reply_text("No logs found.")
            return
            
        msg = "*Recent Activity:*\n"
        for log in logs:
            msg += f"• `{log.created_at.strftime('%H:%M:%S')}` {log.event_type}: {log.description}\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")

async def run_bot():
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("audit", audit))
    
    logger.info("Telegram bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)
