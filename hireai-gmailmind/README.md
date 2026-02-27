# GmailMind - AI-Powered Gmail Assistant

An intelligent Gmail management agent built with OpenAI Agents SDK. GmailMind connects to users' Gmail accounts, reads and understands emails using AI, and can draft replies, categorize messages, extract action items, and manage your inbox autonomously.

## Architecture

```
hireai-gmailmind/
├── agent/          # OpenAI Agents SDK agent definitions and orchestration
├── tools/          # Agent tools (Gmail read, send, search, label, etc.)
├── memory/         # Conversation and email context memory (pgvector)
├── config/         # App configuration and settings
├── api/            # FastAPI REST API
│   └── routes/     # API route handlers
├── scheduler/      # Celery background tasks and email polling
├── models/         # SQLAlchemy database models
├── tests/          # Unit and integration tests
└── scripts/        # Utility and setup scripts
```

## Key Features

- **Gmail Integration**: Full Gmail API access (read, send, search, label, archive)
- **AI Agent**: OpenAI Agents SDK for intelligent email understanding and response
- **Semantic Memory**: pgvector-backed embedding storage for email context recall
- **Background Processing**: Celery + Redis for scheduled email polling and async tasks
- **REST API**: FastAPI endpoints for frontend/client integration
- **Multi-User**: OAuth 2.0 per-user Gmail authentication with encrypted token storage
- **Secure**: Fernet encryption for stored credentials, scoped OAuth permissions

## Tech Stack

| Component       | Technology                    |
|----------------|-------------------------------|
| AI Agent       | OpenAI Agents SDK             |
| API Server     | FastAPI + Uvicorn             |
| Task Queue     | Celery + Redis                |
| Database       | PostgreSQL + pgvector         |
| ORM            | SQLAlchemy + Alembic          |
| Gmail Access   | Google API Python Client      |
| Auth           | Google OAuth 2.0              |
| Encryption     | Fernet (cryptography)         |

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up PostgreSQL with pgvector extension
5. Run database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the server:
   ```bash
   uvicorn api.main:app --reload
   ```
7. Start the Celery worker:
   ```bash
   celery -A scheduler.worker worker --loglevel=info
   ```

## License

MIT
