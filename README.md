# Payout Engine

A Django-based payout engine for Indian merchants who receive USD payments from international customers. Built following Stripe/Razorpay patterns with proper concurrency handling, idempotency, and ledger integrity.

## Features

- **Merchant Ledger** - Balance calculated from credits/debits via DB aggregation (not stored)
- **Payout Request API** - POST `/api/v1/payouts/` with idempotency keys
- **Background Processor** - Celery workers with 70/20/10 success/fail/hang simulation
- **React Dashboard** - Balance card, payout form, transaction/payout history tables
- **State Machine** - Enforced transitions: pending → processing → completed/failed

## Tech Stack

| Layer | Choice |
|-------|-------|
| Backend | Django 4.2+, DRF |
| Database | PostgreSQL |
| Background Jobs | Celery + Redis |
| Frontend | React 18 + Tailwind |
| Container | Docker Compose |

## Quick Start (Docker)

```bash
# Clone and start all services
docker-compose up -d

# Seed test data
docker-compose exec backend python manage.py seed
```

Access:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Admin: http://localhost:8000/admin/

## Local Development

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py runserver 8000
```

### Celery Workers

```bash
# Terminal 2 - Worker
celery -A config worker -l info

# Terminal 3 - Beat (scheduler)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/balance/` | GET | Get merchant balance |
| `/api/v1/ledger/` | GET | Transaction history |
| `/api/v1/payouts/` | GET | Payout history |
| `/api/v1/payouts/` | POST | Create payout |
| `/api/v1/bank-accounts/` | GET | List bank accounts |

## Seeded Merchants

| Name | Email | Initial Balance |
|------|-------|-----------------|
| Acme Agency | acme@example.com | ₹50,000 |
| BuildFast Studio | buildfast@example.com | ₹25,000 |
| PixelPerfect Labs | pixelperfect@example.com | ₹80,000 |

## Testing

```bash
# Run tests
python manage.py test payouts.tests

# Idempotency tests (SQLite works)
python manage.py test payouts.tests.test_idempotency

# Concurrency tests (requires PostgreSQL)
python manage.py test payouts.tests.test_concurrency
```

## Environment Variables

```env
# Backend .env
SECRET_KEY=your-secret-key
DEBUG=True
DB_ENGINE=postgresql
DATABASE_URL=postgres://user:pass@host:5432/dbname?sslmode=require
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Frontend .env
VITE_API_URL=http://localhost:8000
```

## Core Design Decisions

1. **Balance via DB aggregation** - Never stored as column. Always calculated with `Coalesce(Sum(...), Value(0))`

2. **select_for_update()** - Inside `transaction.atomic()` to prevent race conditions

3. **Idempotency** - IdempotencyRecord with unique constraint per merchant, 24h expiry

4. **State machine** - LEGAL_TRANSITIONS dict blocking illegal transitions

5. **BigIntegerField** - Money stored as paise (integers), never floats

## License

MIT