# GmailMind — Complete Project Structure & Claude Code Prompts
# HireAI Digital Employee #1
# ================================================

## FOLDER STRUCTURE
```
hireai-gmailmind/
│
├── 📄 SPEC.md                          # Aapka already banaya hua SPEC
├── 📄 README.md                        # Project overview
├── 📄 .env.example                     # Environment variables template
├── 📄 docker-compose.yml               # Local dev environment
├── 📄 Dockerfile                       # Agent container
│
├── 📁 agent/                           # Core Agent Engine
│   ├── 📄 __init__.py
│   ├── 📄 gmailmind.py                 # Main agent definition (OpenAI Agents SDK)
│   ├── 📄 reasoning_loop.py            # Observe → Think → Act → Remember loop
│   ├── 📄 safety_guard.py              # Hard rules enforcer
│   └── 📄 report_generator.py         # Daily summary report
│
├── 📁 tools/                           # All 13 Agent Tools
│   ├── 📄 __init__.py
│   ├── 📄 gmail_tools.py               # read, send, reply, label, archive, search
│   ├── 📄 calendar_tools.py            # check availability, create event, schedule
│   ├── 📄 crm_tools.py                 # get contact, update, log activity
│   ├── 📄 memory_tools.py              # read/write sender memory
│   ├── 📄 sheets_tools.py              # log to Google Sheet
│   └── 📄 alert_tools.py              # WhatsApp / Slack escalation
│
├── 📁 memory/                          # Memory System
│   ├── 📄 __init__.py
│   ├── 📄 short_term.py                # Current session context
│   ├── 📄 long_term.py                 # PostgreSQL + pgvector
│   └── 📄 schemas.py                  # Memory data models
│
├── 📁 config/                          # Configuration System
│   ├── 📄 __init__.py
│   ├── 📄 business_config.py           # Load user's business goals & rules
│   ├── 📄 credentials.py               # Encrypted credentials handler
│   └── 📄 settings.py                 # App-wide settings
│
├── 📁 api/                             # FastAPI — HireAI Platform endpoints
│   ├── 📄 __init__.py
│   ├── 📄 main.py                      # FastAPI app entry point
│   ├── 📄 routes/
│   │   ├── 📄 agent.py                 # /agents/start, /stop, /status
│   │   ├── 📄 config.py                # /config/update, /config/get
│   │   └── 📄 reports.py              # /reports/daily, /reports/actions
│   └── 📄 middleware.py               # Auth, rate limiting
│
├── 📁 scheduler/                       # Task Queue
│   ├── 📄 __init__.py
│   ├── 📄 celery_app.py                # Celery + Redis setup
│   └── 📄 tasks.py                    # Scheduled agent tasks
│
├── 📁 models/                          # Data Models
│   ├── 📄 __init__.py
│   ├── 📄 email_model.py               # Email schema
│   ├── 📄 action_log.py                # Action log schema
│   └── 📄 user_config.py              # User config schema
│
├── 📁 tests/                           # Tests
│   ├── 📄 test_tools.py                # Unit tests for all tools
│   ├── 📄 test_agent.py                # Agent reasoning tests
│   ├── 📄 test_workflows.py            # End-to-end workflow tests
│   └── 📄 test_safety.py              # Safety rules tests
│
└── 📁 scripts/                         # Utility Scripts
    ├── 📄 setup_gmail_oauth.py         # One-time Gmail OAuth setup
    ├── 📄 setup_db.py                  # Database initialization
    └── 📄 test_connection.py          # Test all integrations
```

---

## CLAUDE CODE PROMPTS
# ================================================
# Inhe Claude Code mein SEQUENCE mein use karo
# Ek prompt complete hone ke baad agla dena
# ================================================


## ▶ PROMPT 0 — PROJECT INITIALIZATION
```
Read the SPEC.md file in this directory carefully.

Then initialize the GmailMind project with this exact folder structure:

hireai-gmailmind/
├── agent/
├── tools/
├── memory/
├── config/
├── api/
│   └── routes/
├── scheduler/
├── models/
├── tests/
└── scripts/

Create all __init__.py files.
Create a README.md with project overview based on SPEC.md.
Create .env.example with all required environment variables from the SPEC.
Create requirements.txt with these packages:
  openai-agents, fastapi, uvicorn, celery, redis,
  google-api-python-client, google-auth-oauthlib,
  psycopg2-binary, pgvector, sqlalchemy, alembic,
  python-dotenv, cryptography, pydantic, httpx

Do not write any logic yet. Just structure.
```

---

## ▶ PROMPT 1 — GMAIL TOOLS
```
Read SPEC.md section "6. AGENT TOOLS SPECIFICATION".

Create tools/gmail_tools.py with these 6 tools as Python functions
using Google Gmail API (via google-api-python-client):

1. read_emails(max_results, filter, include_thread) -> List[Email]
2. send_email(to, subject, body, reply_to_thread_id) -> dict
3. reply_to_email(thread_id, body) -> dict
4. label_email(email_id, labels, archive) -> bool
5. search_emails(query, max_results) -> List[Email]
6. create_draft(to, subject, body) -> dict

Rules:
- Use OAuth2 credentials from config/credentials.py
- All functions must have proper error handling with try/except
- All functions must log every action taken
- Return typed Pydantic models, not raw dicts
- Add docstrings to every function
- No hardcoded credentials anywhere
```

---

## ▶ PROMPT 2 — MEMORY SYSTEM
```
Read SPEC.md section "4.3 Memory & Context System".

Create the full memory system:

1. models/schemas.py
   - SenderProfile: email, name, company, history, last_interaction, tags
   - ActionLog: timestamp, email_from, action_taken, tool_used, outcome
   - FollowUp: email_id, sender, due_time, note, status

2. memory/long_term.py
   - Use PostgreSQL with SQLAlchemy
   - Functions: get_sender_memory(email), update_sender_memory(email, data)
   - Store full interaction history per sender
   - Use pgvector for semantic search on past emails

3. memory/short_term.py
   - Use Python dict in-memory (resets each run)
   - Track: current_session_emails, actions_taken_today, pending_escalations

4. memory/schemas.py
   - All memory-related Pydantic models

All database connections must use environment variables.
Add proper indexes for email lookup performance.
```

---

## ▶ PROMPT 3 — CALENDAR & CRM TOOLS
```
Read SPEC.md section "6. AGENT TOOLS SPECIFICATION" — tools 7, 8, 9, 10.

Create tools/calendar_tools.py:
1. check_calendar_availability(date_range_start, date_range_end) -> List[FreeSlot]
2. create_calendar_event(title, start_time, end_time, attendees, description) -> str
3. schedule_followup(email_id, follow_up_after_hours, note) -> bool
   (This saves to DB, Celery will pick it up later)

Create tools/crm_tools.py:
1. get_crm_contact(email) -> ContactProfile | None
2. update_crm(email, action, data) -> bool
   (Support HubSpot API + fallback to local PostgreSQL if no CRM configured)

Create tools/alert_tools.py:
1. send_escalation_alert(channel, message, urgency) -> bool
   (Support "whatsapp" via Twilio API and "slack" via webhook)

All tools must:
- Check if integration is configured before calling (graceful skip if not)
- Return clear success/failure with reason
- Log every action
```

---

## ▶ PROMPT 4 — SAFETY GUARD
```
Read SPEC.md section "8. SAFETY & CONTROL RULES".

Create agent/safety_guard.py with a SafetyGuard class:

class SafetyGuard:
    
    HARD_RULES = [
        "never_delete_email_permanently",
        "never_send_mass_email_over_50",
        "never_share_credentials",
        "never_reply_to_spam",
        "never_take_financial_actions",
        "never_impersonate",
        "stop_if_daily_limit_exceeded"
    ]
    
    def check_action(self, action: str, params: dict) -> tuple[bool, str]:
        # Returns (is_safe, reason)
        # Must check ALL hard rules before any action executes
    
    def is_daily_limit_exceeded(self) -> bool:
        # Check actions_taken_today from short_term memory
    
    def contains_escalation_keywords(self, text: str) -> bool:
        # Check for: legal, complaint, urgent, payment dispute, etc.
    
    def is_spam(self, email: dict) -> bool:
        # Detect spam patterns

SafetyGuard must wrap EVERY tool call in the agent.
If any hard rule is violated, raise SafetyViolationError with clear message.
Log all safety checks.
```

---

## ▶ PROMPT 5 — CORE AGENT (Main Brain)
```
Read SPEC.md sections 4, 7 carefully.

Create agent/gmailmind.py using OpenAI Agents SDK:

from agents import Agent, Tool, Runner

1. Define GmailMind as an Agent with:
   - name: "GmailMind"
   - instructions: Full system prompt based on SPEC sections 2, 3, 8
     (Include business goals, personality, safety rules, decision framework)
   - tools: All 13 tools wrapped with SafetyGuard checks
   - model: "gpt-4o"

2. The agent instructions must tell it:
   - How to reason about each email (THINK section from SPEC 7)
   - When to act autonomously vs create draft vs escalate
   - How to use memory before making decisions
   - How to pursue the user's active business goals
   - All safety boundaries

3. Create agent/reasoning_loop.py:
   async def run_agent_loop(user_config: dict):
       # 1. Observe: fetch new emails + pending followups
       # 2. For each email: run GmailMind agent with full context
       # 3. Remember: update memory after each decision
       # 4. Report: append to daily summary
       # 5. Sleep until next interval

The agent must receive memory context with each email:
  - sender_history from long_term memory
  - active_business_goals from user_config
  - today_actions_count from short_term memory

Do not use fake/mock tools. Wire everything to real tool functions.
```

---

## ▶ PROMPT 6 — SCHEDULER & TASK QUEUE
```
Create the Celery-based task scheduler:

1. scheduler/celery_app.py
   - Celery app with Redis broker
   - Beat schedule: run agent loop every CHECK_INTERVAL_MINUTES

2. scheduler/tasks.py
   - @celery.task: run_gmailmind_for_user(user_id)
     Loads user config, runs reasoning_loop, handles errors
   - @celery.task: process_due_followups()
     Check DB for followups due now, trigger agent for each
   - @celery.task: send_daily_report(user_id)
     Generate and email daily summary at EOD

All tasks must:
- Handle exceptions gracefully (never crash the worker)
- Log start, end, duration of every run
- Update agent status in DB (running/idle/error)
```

---

## ▶ PROMPT 7 — FASTAPI ENDPOINTS
```
Read SPEC.md section "10. TECHNICAL ARCHITECTURE".

Create the FastAPI backend in api/:

api/main.py — FastAPI app with CORS, auth middleware

api/routes/agent.py:
- POST /agents/{user_id}/start    → Start agent for user
- POST /agents/{user_id}/stop     → Stop agent
- GET  /agents/{user_id}/status   → Running/idle/error + last_run
- GET  /agents/{user_id}/logs     → Last 100 actions

api/routes/config.py:
- GET  /config/{user_id}          → Get user's agent config
- POST /config/{user_id}          → Save/update config
- POST /config/{user_id}/credentials → Save encrypted credentials

api/routes/reports.py:
- GET  /reports/{user_id}/daily   → Today's summary
- GET  /reports/{user_id}/actions → Paginated action log

All endpoints must:
- Verify JWT token (from HireAI platform auth)
- Validate subscription is active before starting agent
- Return consistent JSON response format:
  { success: bool, data: any, error: str | null }
```

---

## ▶ PROMPT 8 — REPORT GENERATOR
```
Create agent/report_generator.py:

class ReportGenerator:
    
    def generate_daily_summary(self, user_id: str, date: str) -> dict:
        # Pull all actions from DB for this user+date
        # Calculate: emails_processed, auto_replied, escalated,
        #            followups_set, leads_created, avg_response_time
        # Find items needing human attention
        # Return structured report dict
    
    def format_email_report(self, report: dict) -> str:
        # Convert to nice HTML email
        # Include emoji, tables, action list
        # Ready to send via Gmail
    
    def get_attention_items(self, user_id: str) -> List[dict]:
        # Return emails/actions that need human review
        # Escalations, drafts awaiting approval, errors

Report must match exactly the format defined in SPEC.md section 9.1.
```

---

## ▶ PROMPT 9 — TESTS
```
Create comprehensive tests in tests/:

tests/test_tools.py:
- Test each Gmail tool with mocked Gmail API responses
- Test calendar tools with mocked Google Calendar
- Test memory read/write operations
- Test CRM tools with mocked HubSpot responses

tests/test_safety.py:
- Test every HARD RULE is enforced
- Test SafetyViolationError is raised correctly
- Test daily limit enforcement
- Test spam detection
- Test escalation keyword detection

tests/test_workflows.py:
- Test full "New Lead Email" workflow end-to-end
- Test full "Complaint Email" workflow end-to-end
- Test follow-up scheduling workflow
- Mock all external APIs

Use pytest + pytest-asyncio.
Aim for 80%+ coverage.
All tests must pass before moving to deployment.
```

---

## ▶ PROMPT 10 — DOCKER & DEPLOYMENT
```
Create deployment configuration:

1. Dockerfile:
   - Base: python:3.11-slim
   - Install requirements
   - Copy source code
   - Entry: uvicorn api.main:app

2. docker-compose.yml (for local dev):
   services:
     - gmailmind-api (FastAPI)
     - gmailmind-worker (Celery worker)
     - gmailmind-scheduler (Celery beat)
     - postgres (PostgreSQL + pgvector)
     - redis (for Celery broker)

3. scripts/setup_db.py:
   - Create all tables
   - Create indexes
   - Insert default business rule templates

4. scripts/setup_gmail_oauth.py:
   - Guide user through Gmail OAuth2 flow
   - Save credentials.json securely

5. Update README.md with:
   - Quick start: git clone → docker-compose up
   - Environment setup guide
   - How to configure first user
   - How to run tests

Final check: docker-compose up should start everything with zero errors.
```

---

## HOW TO USE THESE PROMPTS
# ================================================

### Step 1 — Claude Code Install
```bash
npm install -g @anthropic-ai/claude-code
cd hireai-gmailmind
claude
```

### Step 2 — SPEC rakho project root mein
```bash
# SPEC.md aapke folder mein honi chahiye
ls
# SPEC.md  (✅ must be here)
```

### Step 3 — Prompts dene ka tarika
```
- Claude Code open karo
- Prompt 0 paste karo → Enter
- Wait karo jab tak complete ho
- Phir Prompt 1 paste karo
- Is tarah sequence follow karo
- Har prompt ke baad test karo
```

### Step 4 — Review karo
```
Har prompt ke baad:
✅ Code parho — samajh aaya?
✅ Tests chalao — pass ho rahe hain?
✅ Koi improvement chahiye? Claude ko batao
✅ Phir agla prompt do
```

### GOLDEN RULE
```
❌ Kabhi multiple prompts ek saath mat do
❌ Kabhi bina review kiye aage mat bado
✅ Ek prompt → Review → Test → Agla prompt
✅ Ye hai real Spec-Driven Development
```
