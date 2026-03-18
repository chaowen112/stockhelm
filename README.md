# StockHelm 🛡️⚓

StockHelm is a private trading console and paper trading system for Taiwan financial markets (stocks, futures, options). It provides a web-based dashboard and a Telegram bot for market data monitoring and simulated trading.

## Features

- **Real-time Market Data**: Powered by Shioaji (SinoPac API).
- **Paper Trading Engine**: Simulate buys and sells with persistent state in PostgreSQL.
- **Telegram Integration**: Query quotes and manage watchlists via Telegram commands.
- **Web Dashboard**: Modern, minimal interface to track positions, orders, and PnL.
- **Security Focused**: No live trading capabilities, no broker secrets exposed to the frontend, and strict Telegram allowlisting.
- **Audit-First**: Comprehensive event logging for all trading activities.

## Architecture

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (via SQLModel & Alembic)
- **Market Data**: Shioaji API (Broker-neutral abstraction layer)
- **Telegram**: python-telegram-bot
- **Frontend**: Vanilla JS + Tailwind CSS

## Security Boundaries (v1)

- **NO LIVE TRADING**: The system is designed for paper trading only. No order routes to Shioaji are implemented.
- **Credential Protection**: Shioaji API keys and JWT secrets are stored only on the backend.
- **No CA Certificates**: The system does not require or support CA certificate integration, ensuring real trades cannot be placed even if the app is compromised.
- **Private Deployment**: Intended for single-user use.

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL Database
- Shioaji API Key & Secret (SinoPac account)
- Telegram Bot Token (from @BotFather)

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chaowen.chen/stockhelm.git
   cd stockhelm
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Copy `.env.example` to `.env` and fill in your credentials, including the `DATABASE_URL` for PostgreSQL.
   ```bash
   cp .env.example .env
   ```

4. **Run Migrations**:
   Set up your database schema using Alembic.
   ```bash
   python3 -m alembic upgrade head
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```
   The web dashboard will be available at `http://localhost:8000`.

### Docker Setup

```bash
docker-compose up -d
```

## Telegram Commands

- `/quote <symbol>`: Get a concise quote summary.
- `/watch <symbol>`: Add a symbol to your watchlist.
- `/unwatch <symbol>`: Remove a symbol from your watchlist.
- `/audit <limit>`: View recent activity logs (default: 10).

## Database & Migrations

StockHelm uses Alembic for database migrations to maintain schema integrity across updates.

### Common Migration Tasks

1.  **Generate a new migration**:
    ```bash
    python3 -m alembic revision --autogenerate -m "description of changes"
    ```
2.  **Apply migrations**:
    ```bash
    python3 -m alembic upgrade head
    ```

## Security & Audit

Every significant action (orders, fills, subscriptions, cancellations) is logged in the `eventlog` table for auditing purposes. This "Event-Log First" design ensures that even if the app's state is reset, a full audit trail of user intent and engine actions remains. You can view these logs via the Telegram `/audit` command.

## Intentionally Not Implemented in v1

- Real-time trading (Live Order Routing).
- Multi-user support / SaaS features.
- Advanced charting (TradingView integration).
- Options trading (v1 focus: Stocks & Futures).
- Mobile App (v1 is web-only).

## License

MIT
