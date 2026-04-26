# Playto Payout Engine

A payout engine for cross-border payments. Merchants accumulate balance from customer payments (credits) and withdraw to their Indian bank accounts (payouts). The system handles concurrency, idempotency, and data integrity at the database level.

## Stack

- **Backend:** Django + Django REST Framework
- **Frontend:** React + Tailwind CSS
- **Database:** PostgreSQL
- **Background Jobs:** Celery + Redis
- **Task Scheduler:** Celery Beat

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for PostgreSQL and Redis)

### 1. Clone and install

```bash
git clone https://github.com/empuraan01/playto-payout.git
cd playto-payout

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Start PostgreSQL and Redis

```bash
docker-compose up -d
```

This starts PostgreSQL on port 5432 and Redis on port 6379.

### 3. Run migrations and seed data

```bash
python manage.py migrate
python manage.py seed
```

The seed script creates 3 merchants with bank accounts and credit history:
- Acme Agency — ₹1,50,000
- Priya Sharma — ₹80,000
- Nova Digital — ₹2,00,000

### 4. Start the backend

You need three terminals:

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A config worker --loglevel=info

# Terminal 3: Celery beat (retry scheduler)
celery -A config beat --loglevel=info
```

### 5. Start the frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:5173 to access the dashboard.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/merchants/` | List all merchants with bank accounts |
| GET | `/api/v1/merchants/<id>/balance/` | Available and held balance |
| GET | `/api/v1/merchants/<id>/ledger/` | Ledger entries (newest first) |
| GET | `/api/v1/payouts/<merchant_id>/` | Payout history |
| POST | `/api/v1/payouts/` | Create a payout request |

### Create Payout

```bash
curl -X POST http://localhost:8000/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: <uuid>" \
  -d '{
    "merchant_id": "<merchant-uuid>",
    "amount_paise": 1000000,
    "bank_account_id": "<bank-account-uuid>"
  }'
```

## Architecture

### Ledger

Every money movement is an append-only ledger entry. Balance is never stored — it's always derived from the ledger via database-level aggregation. Four entry types: `credit`, `debit_hold`, `debit_confirm`, `debit_release`.

### Concurrency

`SELECT FOR UPDATE` on the merchant row inside a transaction. Two simultaneous payouts exceeding the balance — exactly one succeeds, the other is rejected.

### Idempotency

`Idempotency-Key` header (merchant-supplied UUID) scoped per merchant with 24-hour expiry. Duplicate requests return the cached response. Simultaneous in-flight duplicates are handled by a `UniqueConstraint` on `(key, merchant)`.

### State Machine

Payouts follow: `pending → processing → completed` or `pending → processing → failed`. Illegal transitions (backwards, skipping states) raise a `ValueError`. Enforced in the `transition_to` method on the Payout model.

### Payout Processor

Celery worker picks up pending payouts. Simulated bank settlement: 70% success, 20% failure, 10% hang. On failure, funds are returned atomically with the state transition. Payouts stuck in processing for 30+ seconds are retried with exponential backoff (30s, 60s, 120s), max 3 attempts.

## Tests

```bash
python manage.py test
```

35+ tests covering:
- Ledger balance calculations and API endpoints
- Payout creation, validation, and error handling
- Idempotency (cached responses, merchant scoping)
- Concurrency (threaded simultaneous payouts)
- State machine (valid and illegal transitions)
- Audit log creation

## Project Structure

```
playto-payout/
├── config/             # Django project config, Celery setup
├── merchants/          # Merchant and BankAccount models, views, seed script
├── ledger/             # LedgerEntry model, balance calculation
├── payouts/            # Payout model, state machine, API, Celery tasks
├── frontend/           # React dashboard
├── docker-compose.yml  # PostgreSQL + Redis
├── EXPLAINER.md        # Architecture decisions and AI audit
└── README.md
```