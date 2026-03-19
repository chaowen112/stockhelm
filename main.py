from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from storage.db import init_db
from broker.shioaji_client import shioaji_broker
from paper.engine import paper_engine
from config import settings
import logging
import asyncio

# Configure logging
import os
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "stockhelm.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up StockHelm...")
    init_db()
    shioaji_broker.login()
    await paper_engine.load_pending_orders()
    
    # Start Telegram bot
    from telegram_bot.bot import run_bot
    asyncio.create_task(run_bot())

    
    # Subscribe to existing watchlist symbols
    from sqlmodel import Session, select
    from storage.db import engine as db_engine
    from storage.models import Watchlist
    with Session(db_engine) as session:
        watchlist = session.exec(select(Watchlist)).all()
        for item in watchlist:
            shioaji_broker.subscribe(item.symbol_code)
            logger.info(f"Subscribed to {item.symbol_code}")
    
    yield
    # Shutdown
    logger.info("Shutting down StockHelm...")
    if shioaji_broker.is_logged_in:
        shioaji_broker.logout()

app = FastAPI(title="StockHelm", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers using absolute imports to avoid namespace collision with shioaji.api
from api.auth import router as auth_router
from api.quotes import router as quotes_router
from api.watchlist import router as watchlist_router
from api.paper import router as paper_router

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(quotes_router, prefix="/quotes", tags=["quotes"])
app.include_router(watchlist_router, prefix="/watchlist", tags=["watchlist"])
app.include_router(paper_router, prefix="/paper", tags=["paper"])

# Static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
