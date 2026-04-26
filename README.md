# Playto Pay — Payout Engine

A merchant payout engine for cross-border payment infrastructure. Merchants accumulate balance from international customer payments (USD → INR), and can request payouts to their Indian bank accounts.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│  React SPA   │────▶│  Django + DRF    │────▶│ PostgreSQL  │
│  (Tailwind)  │     │  REST API        │     │ (BigInt     │
│  Port 5173   │     │  Port 8000       │     │  paise)     │
└──────────────┘     └───────┬──────────┘     └─────────────┘
                             │
                    ┌────────▼────────┐
                    │  Celery Worker  │
                    │  + Beat         │──── Redis (broker)
                    │  (Background    │
                    │   processing)   │
                    └─────────────────┘
```

## Features

- **Merchant Ledger**: Balance derived from immutable ledger entries (credits, debits, holds, releases). All amounts in paise (BigIntegerField).
- **Payout API**: POST `/api/v1/payouts/` with `Idempotency-Key` header. Creates payout in pending state, holds funds.
- **Background Processor**: Celery worker simulates bank settlement (70% success, 20% fail, 10% hang). Retry with exponential backoff (max 3 attempts).
- **Concurrency Control**: `SELECT FOR UPDATE` prevents race conditions on balance checks.
- **State Machine**: `pending → processing → completed/failed`. No backward transitions.
- **JWT Authentication**: Token-based auth via `djangorestframework-simplejwt`.
- **React Dashboard**: Live-updating balance cards, payout form, payout history, ledger table.

## Quick Start

### Prerequisites
- Docker Desktop
- Git

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd playto-pay

# Start all services
docker-compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Django API** on http://localhost:8000
- **Celery Worker** (processes payouts)
- **Celery Beat** (retries stuck payouts every 15s)
- **React Frontend** on http://localhost:5173

The seed script runs automatically on startup, creating 3 test merchants.

### Test Accounts

| Username | Password | Business | Balance |
|----------|----------|----------|---------|
| acme | testpass123 | Acme Design Studio | ₹2,50,000 |
| pixelforge | testpass123 | Pixel Forge Labs | ₹1,00,000 |
| cloudnine | testpass123 | Cloud Nine Agency | ₹50,000 |

### Running Tests

```bash
docker-compose exec backend python manage.py test payouts.tests -v2
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/token/` | No | Get JWT tokens |
| POST | `/api/v1/auth/token/refresh/` | No | Refresh access token |
| POST | `/api/v1/auth/register/` | No | Register merchant |
| GET | `/api/v1/merchants/me/` | Yes | Merchant profile |
| GET | `/api/v1/merchants/me/balance/` | Yes | Balance (DB aggregation) |
| GET | `/api/v1/merchants/me/ledger/` | Yes | Ledger entries (paginated) |
| GET | `/api/v1/merchants/me/payouts/` | Yes | Payout history |
| POST | `/api/v1/payouts/` | Yes | Create payout (+ Idempotency-Key header) |
| GET | `/api/v1/payouts/{id}/` | Yes | Payout detail |

### Example: Create Payout

```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"acme","password":"testpass123"}' | jq -r '.access')

# Create payout
curl -X POST http://localhost:8000/api/v1/payouts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"amount_paise": 100000, "bank_account_id": "<bank-account-uuid>"}'
```

## Tech Stack

- **Backend**: Django 5.x, Django REST Framework, PostgreSQL 16, Celery, Redis
- **Frontend**: React 18, Vite 5, Tailwind CSS 3, Axios, Lucide Icons
- **Auth**: JWT (djangorestframework-simplejwt)
- **Infrastructure**: Docker Compose

## Project Structure

```
.
├── docker-compose.yml
├── .env
├── backend/
│   ├── config/          # Django project settings
│   │   ├── settings.py
│   │   ├── celery.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── payouts/         # Main app
│   │   ├── models.py    # Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
│   │   ├── views.py     # API views with SELECT FOR UPDATE
│   │   ├── tasks.py     # Celery tasks (process_payout, retry_stuck)
│   │   ├── serializers.py
│   │   ├── admin.py
│   │   └── tests/
│   │       ├── test_concurrency.py
│   │       └── test_idempotency.py
│   └── manage.py
└── frontend/
    └── src/
        ├── api/client.js
        ├── pages/
        │   ├── LoginPage.jsx
        │   └── Dashboard.jsx
        └── components/
            ├── BalanceCards.jsx
            ├── PayoutForm.jsx
            ├── PayoutHistory.jsx
            ├── LedgerTable.jsx
            └── StatusBadge.jsx
```
