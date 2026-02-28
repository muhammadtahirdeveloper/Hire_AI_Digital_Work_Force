# GmailMind - AI-Powered Gmail Assistant

**HireAI Digital Employee #1** — An autonomous Gmail management agent built with OpenAI Agents SDK. GmailMind connects to your Gmail, reads and understands emails using AI, drafts replies, categorizes messages, schedules follow-ups, and manages your inbox — all on autopilot.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/hireai-gmailmind.git
cd hireai-gmailmind

# 2. Copy environment template and fill in your values
cp .env.example .env
# Edit .env with your API keys (see Environment Setup below)

# 3. Start everything with Docker
docker-compose up --build
```

That's it. The API server, Celery worker, scheduler, PostgreSQL, and Redis will all start automatically.

- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## Architecture

```
hireai-gmailmind/
├── agent/              # Core AI agent engine
│   ├── gmailmind.py        # Agent definition (OpenAI Agents SDK)
│   ├── reasoning_loop.py   # Observe > Think > Act > Remember loop
│   ├── safety_guard.py     # 7 hard safety rules enforcer
│   ├── report_generator.py # Daily summary reports
│   └── tool_wrappers.py    # Safety-wrapped tool bindings
├── tools/              # 12 agent tools
│   ├── gmail_tools.py      # read, send, reply, label, search, draft
│   ├── calendar_tools.py   # availability, create event, follow-up
│   ├── crm_tools.py        # get/update contacts (HubSpot + local)
│   └── alert_tools.py      # WhatsApp / Slack escalation
├── memory/             # Memory system
│   ├── long_term.py        # PostgreSQL + pgvector
│   ├── short_term.py       # In-memory session state
│   └── schemas.py          # Memory Pydantic models
├── config/             # Configuration
│   ├── settings.py         # Environment variable loader
│   ├── database.py         # SQLAlchemy engine & sessions
│   ├── credentials.py      # OAuth2 credential management
│   └── business_config.py  # User goals, rules, personality
├── api/                # FastAPI REST API
│   ├── main.py             # App entry point
│   ├── middleware.py       # JWT auth, rate limiting
│   └── routes/
│       ├── agent.py        # /agents/ start, stop, status, logs
│       ├── config.py       # /config/ get, update, credentials
│       └── reports.py      # /reports/ daily, actions
├── scheduler/          # Celery task queue
│   ├── celery_app.py       # Celery + Redis + Beat schedule
│   └── tasks.py            # Agent loop, follow-ups, daily report
├── models/             # Data models
│   └── schemas.py          # SQLAlchemy ORM (4 tables)
├── tests/              # Test suite
├── scripts/            # Setup utilities
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Key Features

- **Gmail Integration**: Full Gmail API access (read, send, search, label, archive, draft)
- **AI Agent**: OpenAI Agents SDK with GPT-4o for intelligent email understanding
- **Semantic Memory**: pgvector-backed embedding storage for context recall
- **Safety Guard**: 7 hard rules that can never be overridden (no delete, no spam reply, no impersonation, etc.)
- **Background Processing**: Celery + Redis for scheduled polling and async tasks
- **REST API**: FastAPI endpoints for platform integration
- **Multi-User**: Per-user OAuth 2.0 with encrypted token storage
- **Daily Reports**: Automated end-of-day summary with action counts and attention items

## Tech Stack

| Component       | Technology                    |
|----------------|-------------------------------|
| AI Agent       | OpenAI Agents SDK + GPT-4o   |
| API Server     | FastAPI + Uvicorn             |
| Task Queue     | Celery + Redis                |
| Database       | PostgreSQL + pgvector         |
| ORM            | SQLAlchemy                    |
| Gmail Access   | Google API Python Client      |
| Auth           | Google OAuth 2.0 + JWT        |
| Encryption     | Fernet (cryptography)         |
| Container      | Docker + Docker Compose       |

## Environment Setup

Copy `.env.example` to `.env` and configure the following:

### Required Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (for GPT-4o) |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |
| `ENCRYPTION_KEY` | Fernet key for encrypting stored tokens. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `JWT_SECRET` | Secret key for API JWT tokens |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@postgres:5432/gmailmind` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `HUBSPOT_API_KEY` | HubSpot CRM API key (falls back to local DB) | — |
| `TWILIO_ACCOUNT_SID` | Twilio SID for WhatsApp alerts | — |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | — |
| `SLACK_WEBHOOK_URL` | Slack webhook for escalation alerts | — |
| `DAILY_ACTION_LIMIT` | Max actions per day (safety) | `200` |
| `POLL_INTERVAL_SECONDS` | Email check interval | `300` |

## Configure First User

### Step 1: Set Up Gmail OAuth

```bash
# Run the interactive OAuth wizard
python -m scripts.setup_gmail_oauth
```

This will:
1. Open your browser for Google sign-in
2. Request Gmail API permissions
3. Save your OAuth tokens (encrypted if `ENCRYPTION_KEY` is set)
4. Verify the connection by listing your Gmail labels

### Step 2: Initialize the Database

```bash
# If using Docker (runs inside the container):
docker-compose exec gmailmind-api python -m scripts.setup_db

# If running locally:
python -m scripts.setup_db
```

This creates all tables, indexes, and seeds 8 default business rule templates:
- Lead Response, Client Support, Meeting Request
- Vendor Communication, Newsletter handling, Spam handling
- Urgent Escalation, Follow-Up Reminders

### Step 3: Start the Agent

```bash
# Via API:
curl -X POST http://localhost:8000/agents/default/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Check status:
curl http://localhost:8000/agents/default/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Running Without Docker

If you prefer running services directly:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL and Redis (must be running)

# 3. Set up database
python -m scripts.setup_db

# 4. Set up Gmail OAuth
python -m scripts.setup_gmail_oauth

# 5. Start FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start Celery worker (in another terminal)
celery -A scheduler.celery_app worker --loglevel=info --concurrency=2 \
  -Q default,agent,followups,reports

# 7. Start Celery beat scheduler (in another terminal)
celery -A scheduler.celery_app beat --loglevel=info
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# Run specific test files
pytest tests/test_safety.py -v      # Safety guard tests
pytest tests/test_tools.py -v       # Tool wrapper tests
pytest tests/test_workflows.py -v   # End-to-end workflow tests
```

## API Endpoints

### Agent Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agents/{user_id}/start` | Start the agent for a user |
| `POST` | `/agents/{user_id}/stop` | Stop the agent |
| `GET` | `/agents/{user_id}/status` | Get agent status (running/idle/error) |
| `GET` | `/agents/{user_id}/logs` | Get last 100 action logs |

### Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/config/{user_id}` | Get user's agent config |
| `POST` | `/config/{user_id}` | Save/update config |
| `POST` | `/config/{user_id}/credentials` | Save encrypted credentials |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reports/{user_id}/daily` | Today's summary report |
| `GET` | `/reports/{user_id}/actions` | Paginated action log |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |

## Docker Services

| Service | Container | Description |
|---------|-----------|-------------|
| `gmailmind-api` | FastAPI server | Port 8000, auto-reload in dev |
| `gmailmind-worker` | Celery worker | Processes agent tasks, follow-ups, reports |
| `gmailmind-scheduler` | Celery beat | Triggers periodic tasks |
| `postgres` | PostgreSQL + pgvector | Port 5432, persistent volume |
| `redis` | Redis | Port 6379, persistent volume |

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f gmailmind-api
docker-compose logs -f gmailmind-worker

# Stop all services
docker-compose down

# Stop and remove volumes (full reset)
docker-compose down -v

# Run database setup inside container
docker-compose exec gmailmind-api python -m scripts.setup_db

# Run tests inside container
docker-compose exec gmailmind-api pytest tests/ -v
```

## Safety Rules

GmailMind enforces 7 **hard rules** that can never be overridden:

1. Never delete any email permanently
2. Never send mass emails to more than 50 recipients
3. Never share credentials, passwords, or API keys
4. Never reply to spam
5. Never take financial actions (wire transfers, payments, etc.)
6. Never impersonate anyone
7. Stop all actions if daily limit is exceeded

## License

MIT
