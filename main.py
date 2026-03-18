from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from storage.db import init_db
from broker.shioaji_client import shioaji_client
from paper.engine import paper_engine
from config import settings
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up StockHelm...")
    init_db()
    shioaji_client.login()
    await paper_engine.load_pending_orders()
    
    # Start Telegram bot
    from telegram.bot import run_bot
    asyncio.create_task(run_bot())
    
    # Subscribe to existing watchlist symbols
    from sqlmodel import Session, select
    from storage.db import engine as db_engine
    from storage.models import Watchlist
    with Session(db_engine) as session:
        watchlist = session.exec(select(Watchlist)).all()
        for item in watchlist:
            shioaji_client.subscribe(item.symbol_code)
            logger.info(f"Subscribed to {item.symbol_code}")
    
    yield
    # Shutdown
    logger.info("Shutting down StockHelm...")
    if shioaji_client.is_logged_in:
        shioaji_client.api.logout()

app = FastAPI(title="StockHelm", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from api import auth, quotes, watchlist, paper
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(paper.router, prefix="/paper", tags=["paper"])

# Static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
