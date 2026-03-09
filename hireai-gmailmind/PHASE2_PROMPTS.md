# GmailMind — Phase 2 Claude Code Prompts (11-20)
# Multi-Agent Orchestration System

---

## PROMPT 11 — ORCHESTRATOR AGENT

```
Please read SPEC.md, CONTEXT.md, PHASE2_SPEC.md, and PHASE2_PROMPTS.md first.

Now implement Prompt 11: Orchestrator Agent

Create these new files in the existing hireai-gmailmind project:

1. orchestrator/__init__.py
   Empty file.

2. orchestrator/feature_gates.py
   FeatureGate class:

   TIER_FEATURES = {
     'tier1': {
       'price': 19,
       'max_accounts': 1,
       'max_emails_per_day': 200,
       'features': ['read', 'label', 'archive', 'basic_email_report']
     },
     'tier2': {
       'price': 49,
       'max_accounts': 3,
       'max_emails_per_day': 500,
       'features': [
         'read', 'label', 'archive', 'auto_reply',
         'escalation', 'follow_up', 'whatsapp_report',
         'cv_processing', 'interview_scheduler',
         'candidate_tracker', 'basic_crm', 'basic_email_report'
       ]
     },
     'tier3': {
       'price': 99,
       'max_accounts': 9999,
       'max_emails_per_day': 999999,
       'features': ['all']
     }
   }

   Methods:
   - can_use_feature(user_id, feature_name) -> bool
     Reads user tier from database user_subscriptions table
     tier3 can use all features
     Returns True/False

   - get_user_tier(user_id) -> str
     Read from user_subscriptions table
     Default: 'tier2' if not found (for testing)

   - get_usage_today(user_id) -> int
     Count today's action_logs entries for this user

   - check_daily_limit(user_id) -> bool
     Returns True if under limit, False if exceeded

   - get_upgrade_message(current_tier, blocked_feature) -> str
     Returns friendly upgrade suggestion message

3. orchestrator/agent_registry.py
   AgentRegistry class:
   - __init__: empty dict self.agents = {}
   - register(industry: str, agent_class) -> None
   - get_agent(industry: str) -> agent_class or None
   - list_industries() -> list of registered industry names

4. orchestrator/user_router.py
   UserRouter class:
   - get_user_tier(user_id) -> str
     Read from user_subscriptions table
     Default: 'tier2'
   - get_user_industry(user_id) -> str
     Read from user_configs table (industry column)
     Default: 'general'
   - route_user(user_id) -> dict
     Returns: {industry, tier, features_available}

5. orchestrator/orchestrator.py
   GmailMindOrchestrator class:
   - __init__:
     self.registry = AgentRegistry()
     self.router = UserRouter()
     self.gates = FeatureGate()

   - process_user(user_id) -> dict:
     1. Log "Orchestrator: Processing user={user_id}"
     2. Get tier via self.gates.get_user_tier(user_id)
     3. Check daily limit via self.gates.check_daily_limit(user_id)
        If exceeded: return {'status': 'skipped', 'reason': 'daily_limit'}
     4. Get industry via self.router.get_user_industry(user_id)
     5. Get agent_class via self.registry.get_agent(industry)
        If None: use 'general' as fallback
     6. Log "Orchestrator: Routing user={user_id} to {industry} agent tier={tier}"
     7. Return {'status': 'routed', 'industry': industry, 'tier': tier}
        (actual agent execution will be added in Prompt 19)

   - get_platform_stats() -> dict:
     Returns count of active users, total emails processed today

6. Update scripts/setup_db.py:
   Add these columns if they don't exist:
   - user_subscriptions table: tier VARCHAR(10) DEFAULT 'tier2'
   - user_configs table: industry VARCHAR(20) DEFAULT 'general'

   Use ALTER TABLE ... ADD COLUMN IF NOT EXISTS syntax.

Do NOT modify any existing Phase 1 files.
Use existing database connection patterns from memory/long_term.py.
Add proper logging using Python logging module.

Verify with:
python -c "from orchestrator.orchestrator import GmailMindOrchestrator; o = GmailMindOrchestrator(); print('Prompt 11 Orchestrator: OK')"
```

---

## PROMPT 12 — BASE AGENT + GENERAL AGENT WRAPPER

```
Implement Prompt 12: Base Agent + General Agent Wrapper

Create these files:

1. agents/__init__.py
   Empty file.

2. agents/base_agent.py
   BaseAgent abstract class (use ABC from abc module):

   Class attributes (to be set by subclasses):
   - agent_name: str = "BaseAgent"
   - industry: str = "general"
   - supported_tiers: list = ['tier1', 'tier2', 'tier3']

   Abstract methods (subclasses must implement):
   - get_system_prompt(tier: str) -> str
   - get_available_tools(tier: str) -> list
   - classify_email(email: dict) -> str

   Concrete methods (shared by all agents):
   - validate_tier(tier: str) -> bool
     Check if tier in self.supported_tiers

   - log_action(user_id, action, details, outcome='success'):
     Use existing log_action from memory/long_term.py

   - get_sender_context(sender_email: str) -> dict:
     Use existing get_sender_memory from memory/long_term.py
     Returns sender profile or empty dict

   - format_email_summary(email: dict) -> str:
     Returns: "From: {sender} | Subject: {subject} | Preview: {first 100 chars}"

3. agents/general/__init__.py
   Empty file.

4. agents/general/general_agent.py
   GeneralAgent(BaseAgent) class:

   agent_name = "GmailMind General Agent"
   industry = "general"
   supported_tiers = ['tier1', 'tier2', 'tier3']

   get_system_prompt(tier) -> str:
   - tier1: "You are an email organization assistant. 
             Read emails, apply labels, archive newsletters.
             Do NOT auto-reply. Just organize."
   - tier2: "You are an intelligent email assistant.
             Read emails, organize, auto-reply to inquiries,
             escalate urgent issues, track follow-ups."
   - tier3: "You are an advanced business email manager.
             Full automation, analytics, team coordination,
             CRM sync, comprehensive reporting."

   get_available_tools(tier) -> list:
   - tier1: ['read_emails', 'label_email', 'search_emails']
   - tier2: tier1 tools + ['reply_to_email', 'send_escalation_alert',
             'schedule_followup', 'create_draft']
   - tier3: tier2 tools + ['send_email', 'create_calendar_event',
             'get_crm_contact', 'update_crm']

   classify_email(email) -> str:
   Categories: 'newsletter', 'inquiry', 'urgent', 'spam',
               'notification', 'personal', 'business'
   Use simple keyword matching for now.

5. Register GeneralAgent in orchestrator/agent_registry.py:
   In orchestrator/__init__.py or in orchestrator.py __init__:
   registry.register('general', GeneralAgent)

Verify with:
python -c "
from agents.general.general_agent import GeneralAgent
a = GeneralAgent()
print('Agent:', a.agent_name)
print('Industry:', a.industry)
print('Tier1 tools:', a.get_available_tools('tier1'))
print('Prompt 12 Base Agent: OK')
"
```

---

## PROMPT 13 — HR SPECIALIST AGENT

```
Implement Prompt 13: HR Specialist Agent

Create these files in agents/hr/:

1. agents/hr/__init__.py
   Empty file.

2. agents/hr/hr_templates.py
   HR_TEMPLATES dictionary with these templates:

   'cv_received': """
   Dear {candidate_name},

   Thank you for applying for the {job_title} position.
   We have received your application and will review it shortly.
   We will be in touch within 3-5 business days.

   Best regards,
   {company_name} HR Team
   """

   'interview_invite': """
   Dear {candidate_name},

   We are pleased to invite you for an interview for the {job_title} position.
   Please let us know your availability for the following slots:
   {available_slots}

   Interview Duration: {duration} minutes
   Format: {interview_type}

   Best regards,
   {company_name} HR Team
   """

   'interview_confirmation': """
   Dear {candidate_name},

   Your interview has been confirmed:
   Date: {interview_date}
   Time: {interview_time}
   Format: {interview_type}
   {location_or_link}

   Please let us know if you need to reschedule.

   Best regards,
   {company_name} HR Team
   """

   'rejection_polite': """
   Dear {candidate_name},

   Thank you for your interest in the {job_title} position
   and for taking the time to apply.

   After careful consideration, we have decided to move forward
   with other candidates whose experience more closely matches
   our current needs.

   We will keep your profile on file for future opportunities.

   Best regards,
   {company_name} HR Team
   """

   'follow_up_candidate': """
   Dear {candidate_name},

   I wanted to follow up regarding your application for {job_title}.
   We are still reviewing candidates and will update you soon.

   Best regards,
   {company_name} HR Team
   """

   'client_position_update': """
   Dear {client_name},

   Update on your {job_title} requirement:
   - CVs received: {cv_count}
   - Shortlisted: {shortlisted_count}
   - Interviews scheduled: {interview_count}

   We will share candidate profiles by {expected_date}.

   Best regards,
   {recruiter_name}
   """

3. agents/hr/cv_processor.py
   CVProcessor class:

   extract_cv_info(email_body: str, subject: str) -> dict:
   Use GPT-4o to extract from email body:
   Returns: {
     name: str or None,
     email: str or None,
     phone: str or None,
     experience_years: int or 0,
     skills: list of str,
     current_role: str or None,
     location: str or None,
     education: str or None,
     has_cv_attachment: bool
   }
   Use simple prompt: "Extract candidate info from this email. Return JSON only."

   score_candidate(cv_info: dict, job_requirements: dict) -> int:
   Score 0-100 based on:
   - Skills match: up to 50 points
   - Experience match: up to 30 points
   - Location match: up to 20 points
   Return integer score.

   is_cv_email(email: dict) -> bool:
   Check if email contains CV/resume keywords:
   ['cv', 'resume', 'application', 'applying', 'candidate', 'portfolio']
   in subject or body (case insensitive)

4. agents/hr/candidate_tracker.py
   CandidateTracker class:

   STAGES = ['applied', 'screened', 'interview', 'offer', 'hired', 'rejected']

   get_candidate(user_id: str, email: str) -> dict or None:
   Read from candidates table.

   create_candidate(user_id: str, cv_info: dict, job_title: str) -> int:
   Insert into candidates table.
   Return candidate id.

   update_stage(user_id: str, email: str, stage: str, notes: str = '') -> bool:
   Update candidates table.
   Also schedule follow_up if stage == 'interview'.

   get_pipeline_summary(user_id: str) -> dict:
   Returns count per stage:
   {'applied': 5, 'screened': 3, 'interview': 2, 'offer': 1, 'hired': 0, 'rejected': 2}

   get_candidates_by_stage(user_id: str, stage: str) -> list:
   Returns list of candidates in given stage.

5. agents/hr/interview_scheduler.py
   InterviewScheduler class:

   find_available_slots(user_id: str, duration_minutes: int = 60, days_ahead: int = 7) -> list:
   Use existing check_calendar_availability from tools/calendar_tools.py
   Return list of available datetime slots.

   schedule_interview(user_id: str, candidate_email: str,
                      slot: str, job_title: str,
                      interview_type: str = 'video') -> dict:
   1. Create calendar event using create_calendar_event from tools/calendar_tools.py
   2. Insert record in interviews table
   3. Return {'calendar_event_id': ..., 'interview_id': ...}

   get_upcoming_interviews(user_id: str, days: int = 7) -> list:
   Query interviews table for upcoming scheduled interviews.

6. agents/hr/hr_agent.py
   HRAgent(BaseAgent) class:

   agent_name = "GmailMind HR Agent"
   industry = "hr"
   supported_tiers = ['tier2', 'tier3']

   __init__:
   self.cv_processor = CVProcessor()
   self.candidate_tracker = CandidateTracker()
   self.interview_scheduler = InterviewScheduler()

   get_system_prompt(tier) -> str:
   "You are an expert HR recruitment email assistant.
    You help recruiters manage candidate applications, 
    schedule interviews, and communicate professionally.
    Always be warm, professional, and encouraging to candidates.
    For internal client emails, be concise and data-driven."

   classify_email(email) -> str:
   Categories specific to HR:
   - 'cv_application': email has CV/resume/application keywords
   - 'interview_request': has interview/meeting/schedule keywords
   - 'candidate_followup': has follow up/status/update keywords from candidates
   - 'client_update': from known client domains/emails
   - 'job_inquiry': asking about open positions
   - 'offer_acceptance': candidate accepting offer
   - 'offer_rejection': candidate rejecting offer
   - 'other': anything else

   process_email(email: dict, user_config: dict, tier: str, user_id: str) -> dict:
   
   category = self.classify_email(email)
   
   If category == 'cv_application':
     1. Extract CV info using cv_processor
     2. Create/update candidate in tracker
     3. Score candidate
     4. If score >= 70: draft interview invite
     5. If score < 40: draft polite rejection
     6. If 40-69: mark as 'screened', send acknowledgment
     7. Return action taken

   If category == 'interview_request':
     1. Find available slots
     2. Reply with available times
     3. Return action taken

   If category == 'candidate_followup':
     1. Get candidate current stage
     2. Send appropriate update using template
     3. Return action taken

   If category == 'other':
     1. Label and archive appropriately
     2. Return action taken

7. Register HRAgent in orchestrator/agent_registry.py

Verify with:
python -c "
from agents.hr.hr_agent import HRAgent
a = HRAgent()
print('HR Agent:', a.agent_name)
print('Industry:', a.industry)
print('Supported Tiers:', a.supported_tiers)
print('Prompt 13 HR Agent: OK')
"
```

---

## PROMPT 14 — HR SKILLS & TOOLS

```
Implement Prompt 14: HR Skills & Tools

Create these files:

1. skills/__init__.py
   Empty file.

2. skills/base_skills.py
   BaseSkills class with utility methods:

   smart_reply(email: dict, tone: str, template: str) -> str:
   tone options: 'professional', 'warm', 'urgent', 'formal'
   Use GPT-4o to generate appropriate reply.
   Keep replies concise (max 150 words).

   detect_urgency(email: dict) -> str:
   Returns: 'low', 'medium', 'high', 'critical'
   Critical keywords: ['urgent', 'asap', 'immediately', 'legal', 'lawsuit', 'complaint']
   High keywords: ['important', 'deadline', 'today', 'tomorrow']
   Medium keywords: ['soon', 'this week', 'follow up']

   extract_contact_info(text: str) -> dict:
   Extract: {email, phone, name, company}
   Use simple regex patterns.

   suggest_follow_up_date(context: str) -> str:
   Returns date string like "2026-03-05"
   Default: 3 business days from today.

3. skills/hr_skills.py
   HRSkills(BaseSkills) class:

   log_candidate_to_sheets(cv_info: dict, job_title: str, user_id: str) -> bool:
   If GOOGLE_SHEETS_ID in env: log to Google Sheets
   Otherwise: just log to Python logger
   Return True always (graceful fallback).

   search_candidate_database(user_id: str, query: str) -> list:
   Search candidates table by:
   - name ILIKE %query%
   - email ILIKE %query%
   - skills JSON contains query
   - current_role ILIKE %query%
   Return list of matching candidates.

   get_job_requirements(user_id: str, job_title: str) -> dict:
   Read from job_requirements table.
   If not found: return default empty requirements dict.

   generate_weekly_recruitment_report(user_id: str) -> dict:
   Query last 7 days from:
   - candidates table (new this week, per stage)
   - interviews table (scheduled, completed)
   - action_logs table (emails processed)
   Return comprehensive report dict.

   format_report_for_whatsapp(report: dict) -> str:
   Format report as WhatsApp-friendly message with emojis:
   "📊 Weekly HR Report
    ==================
    📧 Emails processed: {count}
    👤 New CVs: {count}
    ⭐ Shortlisted: {count}
    📅 Interviews scheduled: {count}
    ✅ Hires: {count}
    ❌ Rejections: {count}"

Verify with:
python -c "
from skills.hr_skills import HRSkills
s = HRSkills()
print('HR Skills ready')
from skills.base_skills import BaseSkills
b = BaseSkills()
print('Base Skills ready')
print('Prompt 14 HR Skills: OK')
"
```

---

## PROMPT 15 — HR DATABASE SCHEMA

```
Implement Prompt 15: HR Database Schema

Update scripts/setup_db.py to add HR tables.

Add this function create_hr_tables(engine) and call it from main():

1. candidates table:
CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    current_role VARCHAR(255),
    experience_years INTEGER DEFAULT 0,
    skills JSONB DEFAULT '[]',
    education TEXT,
    location VARCHAR(255),
    cv_score INTEGER DEFAULT 0,
    stage VARCHAR(50) DEFAULT 'applied',
    job_title_applied VARCHAR(255),
    notes TEXT,
    source_email_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, email)
);

2. interviews table:
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    candidate_email VARCHAR(255) NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    interview_type VARCHAR(50) DEFAULT 'video',
    calendar_event_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

3. job_requirements table:
CREATE TABLE IF NOT EXISTS job_requirements (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    required_skills JSONB DEFAULT '[]',
    min_experience_years INTEGER DEFAULT 0,
    location VARCHAR(255),
    salary_range VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

4. Add columns to existing tables using ALTER TABLE:
ALTER TABLE user_subscriptions
ADD COLUMN IF NOT EXISTS tier VARCHAR(10) DEFAULT 'tier2';

ALTER TABLE user_configs
ADD COLUMN IF NOT EXISTS industry VARCHAR(20) DEFAULT 'general';

Also add indexes:
CREATE INDEX IF NOT EXISTS idx_candidates_user_id ON candidates(user_id);
CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(stage);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(user_id, email);
CREATE INDEX IF NOT EXISTS idx_interviews_user_id ON interviews(user_id);
CREATE INDEX IF NOT EXISTS idx_interviews_scheduled ON interviews(scheduled_at);

Run and verify:
python scripts/setup_db.py

Expected output should include:
- candidates table created
- interviews table created  
- job_requirements table created
- tier column added to user_subscriptions
- industry column added to user_configs
```

---

## PROMPT 16 — ORCHESTRATOR API ROUTES

```
Implement Prompt 16: Orchestrator & HR API Routes

1. Create api/routes/orchestrator_routes.py
   Router prefix: /platform

   GET /platform/stats
   Response: {
     active_users: int,
     emails_processed_today: int,
     agents_running: {general: int, hr: int},
     timestamp: str
   }
   Read from action_logs table (today's entries count).

   POST /platform/users/{user_id}/setup
   Body: {industry: str, tier: str}
   - Update user_configs.industry for this user_id
   - Update user_subscriptions.tier for this user_id
   - If records don't exist, create them
   Response: {success: true, user_id, industry, tier}

   GET /platform/users/{user_id}/agent-info
   Response: {
     user_id: str,
     industry: str,
     tier: str,
     agent_name: str,
     features_available: list,
     emails_processed_today: int,
     daily_limit: int
   }

2. Create api/routes/hr_routes.py
   Router prefix: /hr

   GET /hr/{user_id}/candidates
   Query params: stage (optional), page=1, page_size=20
   Response: paginated list of candidates

   GET /hr/{user_id}/candidates/{candidate_email}
   Response: full candidate profile

   PUT /hr/{user_id}/candidates/{candidate_email}/stage
   Body: {stage: str, notes: str}
   Response: {success: true, candidate_email, new_stage}

   GET /hr/{user_id}/pipeline
   Response: {applied: 5, screened: 3, interview: 2, offer: 1, hired: 0, rejected: 2}

   GET /hr/{user_id}/interviews
   Query params: days_ahead=7
   Response: list of upcoming interviews

   GET /hr/{user_id}/report/weekly
   Response: weekly recruitment report dict

   POST /hr/{user_id}/jobs
   Body: {job_title, required_skills, min_experience_years, location}
   Response: {success: true, job_id: int}

   GET /hr/{user_id}/jobs
   Response: list of active job requirements

3. Register both routers in api/main.py:
   from api.routes.orchestrator_routes import router as orchestrator_router
   from api.routes.hr_routes import router as hr_router
   app.include_router(orchestrator_router)
   app.include_router(hr_router)

Do NOT add authentication to these routes yet (keep same as existing routes).

Verify:
docker-compose up --build
Open http://localhost:8000/docs
New sections should appear: Platform, Hr
```

---

## PROMPT 17 — WHATSAPP REPORTS & DAILY SUMMARY

```
Implement Prompt 17: WhatsApp Reports & Daily Summary

1. Create tools/whatsapp_tools.py:

   send_whatsapp_message(to_phone: str, message: str) -> bool:
   - Uses Twilio WhatsApp API
   - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN from .env
   - TWILIO_WHATSAPP_FROM from .env (format: whatsapp:+14155238886)
   - to_phone should be formatted as whatsapp:+{number}
   - If Twilio not configured: log warning and return False
   - Return True on success, False on failure

   send_whatsapp_alert(to_phone: str, message: str, urgency: str = 'medium') -> bool:
   urgency icons: critical=🚨, high=⚠️, medium=ℹ️, low=💬
   Format: "{icon} GmailMind Alert\n{message}"
   Call send_whatsapp_message internally.

   send_whatsapp_report(to_phone: str, report: dict, report_type: str = 'daily') -> bool:
   Format report as readable WhatsApp message.
   Daily format:
   "📊 GmailMind Daily Report
    Date: {date}
    ─────────────────
    📧 Emails processed: {count}
    🏷️  Labels applied: {count}
    📁 Archived: {count}
    🚨 Escalations: {count}
    ──────────────────
    ✅ Agent running smoothly"

   HR Weekly format (if report has hr_data):
   "📊 HR Weekly Report
    Week: {week}
    ─────────────────
    👤 New CVs: {count}
    ⭐ Shortlisted: {count}
    📅 Interviews: {count}
    ✅ Hired: {count}
    ❌ Rejected: {count}
    ─────────────────
    📈 Pipeline: Applied({n}) → Screened({n}) → Interview({n})"

2. Update agent/report_generator.py:
   Add generate_hr_daily_summary(user_id: str, date: str) -> dict:
   - Query candidates created today
   - Query interviews scheduled today
   - Query action_logs for HR actions today
   - Return comprehensive dict

3. Update scheduler/tasks.py:
   Update send_daily_report task:
   - Get user tier
   - Generate report using report_generator
   - If tier == 'tier1': send email only (existing behavior)
   - If tier in ['tier2', 'tier3']: 
     * Send email report
     * Send WhatsApp report if ESCALATION_WHATSAPP_TO is set
   - If user industry == 'hr': include HR metrics

   Add new task send_hr_weekly_report:
   @app.task(name='scheduler.tasks.send_hr_weekly_report')
   def send_hr_weekly_report(user_id='default'):
     - Generate weekly HR report
     - Send via WhatsApp if configured
     - Send via email

4. Update scheduler/celery_app.py:
   Add to beat_schedule:
   'send-hr-weekly-report': {
     'task': 'scheduler.tasks.send_hr_weekly_report',
     'schedule': crontab(hour=9, minute=0, day_of_week=1),
     'args': ('default',)
   }

Verify:
python -c "from tools.whatsapp_tools import send_whatsapp_alert; print('Prompt 17 WhatsApp Tools: OK')"
```

---

## PROMPT 18 — FULL ORCHESTRATOR INTEGRATION

```
Implement Prompt 18: Full Orchestrator Integration

Connect everything together. Update scheduler to use Orchestrator.

1. Update orchestrator/orchestrator.py process_user() method:

   Full implementation:
   async def process_user(user_id: str, gmail_service=None, calendar_service=None) -> dict:
   
   Step 1: Get tier and check limits
   tier = self.gates.get_user_tier(user_id)
   if not self.gates.check_daily_limit(user_id):
     log warning "Daily limit exceeded for user={user_id} tier={tier}"
     return {'status': 'skipped', 'reason': 'daily_limit_exceeded'}

   Step 2: Get industry and route
   industry = self.router.get_user_industry(user_id)
   agent_class = self.registry.get_agent(industry)
   if agent_class is None:
     industry = 'general'
     agent_class = self.registry.get_agent('general')

   Step 3: Log routing
   log info "Orchestrator: Routing user={user_id} to {industry} agent tier={tier}"

   Step 4: Get available features
   features = self.gates.TIER_FEATURES.get(tier, {}).get('features', [])

   Step 5: For now return routing info
   (actual agent execution uses existing reasoning_loop for general,
    HR agent process_email for hr industry)
   
   return {
     'status': 'routed',
     'user_id': user_id,
     'industry': industry,
     'tier': tier,
     'features': features
   }

2. Update scheduler/tasks.py run_gmailmind_for_user:
   
   At the START of the task, before calling reasoning_loop:
   - Create orchestrator instance
   - Call orchestrator.process_user(user_id) to get routing info
   - Log the routing result
   - Then continue with existing reasoning_loop code
   
   This way existing code still works, but orchestrator is now active.
   
   Add this at beginning of the async run function:
   from orchestrator.orchestrator import GmailMindOrchestrator
   orchestrator = GmailMindOrchestrator()
   routing = await orchestrator.process_user(user_id)
   logger.info(f"[orchestrator] Routing: {routing}")
   
   if routing.get('status') == 'skipped':
     return {'status': 'skipped', 'reason': routing.get('reason')}

3. Create orchestrator/health_monitor.py:
   HealthMonitor class:
   
   check_all_users() -> dict:
   Query user_subscriptions for active users.
   For each user check last action_log entry.
   Return {user_id: last_active_timestamp}
   
   get_inactive_users(hours: int = 2) -> list:
   Return users with no activity in last N hours.

4. Update api/routes/orchestrator_routes.py:
   Add GET /platform/health endpoint:
   Response: {
     status: 'healthy',
     active_users: int,
     inactive_users: list,
     timestamp: str
   }

Verify with docker-compose up --build:
Check logs for:
"Orchestrator: Routing user=default to general agent tier=tier2"
This confirms orchestrator is active.
```

---

## PROMPT 19 — TESTS & FINAL VERIFICATION

```
Implement Prompt 19: Tests & Final Verification

1. Create tests/test_orchestrator.py:

import pytest
from orchestrator.orchestrator import GmailMindOrchestrator
from orchestrator.feature_gates import FeatureGate
from orchestrator.agent_registry import AgentRegistry
from agents.general.general_agent import GeneralAgent
from agents.hr.hr_agent import HRAgent

def test_agent_registry():
    registry = AgentRegistry()
    registry.register('general', GeneralAgent)
    registry.register('hr', HRAgent)
    assert registry.get_agent('general') == GeneralAgent
    assert registry.get_agent('hr') == HRAgent
    assert registry.get_agent('unknown') is None

def test_feature_gates_tier1():
    fg = FeatureGate()
    features = fg.TIER_FEATURES['tier1']['features']
    assert 'read' in features
    assert 'auto_reply' not in features
    assert 'cv_processing' not in features

def test_feature_gates_tier2():
    fg = FeatureGate()
    features = fg.TIER_FEATURES['tier2']['features']
    assert 'auto_reply' in features
    assert 'cv_processing' in features
    assert 'interview_scheduler' in features

def test_feature_gates_tier3():
    fg = FeatureGate()
    features = fg.TIER_FEATURES['tier3']['features']
    assert 'all' in features

def test_upgrade_message():
    fg = FeatureGate()
    msg = fg.get_upgrade_message('tier1', 'auto_reply')
    assert 'tier2' in msg.lower() or 'upgrade' in msg.lower()

def test_general_agent_tools():
    agent = GeneralAgent()
    tier1_tools = agent.get_available_tools('tier1')
    tier2_tools = agent.get_available_tools('tier2')
    assert 'read_emails' in tier1_tools
    assert 'auto_reply' not in tier1_tools
    assert len(tier2_tools) > len(tier1_tools)

def test_hr_agent_industry():
    agent = HRAgent()
    assert agent.industry == 'hr'
    assert 'tier1' not in agent.supported_tiers
    assert 'tier2' in agent.supported_tiers

def test_orchestrator_init():
    o = GmailMindOrchestrator()
    assert o.registry is not None
    assert o.router is not None
    assert o.gates is not None

2. Create tests/test_hr_agent.py:

import pytest
from agents.hr.cv_processor import CVProcessor
from agents.hr.candidate_tracker import CandidateTracker
from agents.hr.hr_agent import HRAgent

def test_cv_email_detection():
    processor = CVProcessor()
    cv_email = {
        'subject': 'Job Application - Software Engineer',
        'body': 'Please find attached my resume for the position.'
    }
    assert processor.is_cv_email(cv_email) == True

def test_non_cv_email_detection():
    processor = CVProcessor()
    regular_email = {
        'subject': 'Meeting Tomorrow',
        'body': 'Can we meet tomorrow at 3pm?'
    }
    assert processor.is_cv_email(regular_email) == False

def test_candidate_scoring_high():
    processor = CVProcessor()
    cv_info = {
        'skills': ['Python', 'Django', 'PostgreSQL'],
        'experience_years': 5,
        'location': 'Remote'
    }
    job_req = {
        'required_skills': ['Python', 'Django'],
        'min_experience_years': 3,
        'location': 'Remote'
    }
    score = processor.score_candidate(cv_info, job_req)
    assert score >= 70

def test_hr_email_classification():
    agent = HRAgent()
    cv_email = {'subject': 'Application for Developer Role', 'body': 'Please find my CV attached'}
    assert agent.classify_email(cv_email) == 'cv_application'
    
    interview_email = {'subject': 'Re: Interview Schedule', 'body': 'I am available for interview'}
    assert agent.classify_email(interview_email) == 'interview_request'

def test_pipeline_stages():
    tracker = CandidateTracker()
    valid_stages = tracker.STAGES
    assert 'applied' in valid_stages
    assert 'screened' in valid_stages
    assert 'interview' in valid_stages
    assert 'hired' in valid_stages
    assert 'rejected' in valid_stages

3. Update CONTEXT.md to mark Phase 2 complete:

Add this section:
## Phase 2 Status
- Prompt 11: Orchestrator Agent ✅
- Prompt 12: Base Agent + General Wrapper ✅
- Prompt 13: HR Specialist Agent ✅
- Prompt 14: HR Skills & Tools ✅
- Prompt 15: HR Database Schema ✅
- Prompt 16: Orchestrator API Routes ✅
- Prompt 17: WhatsApp Reports ✅
- Prompt 18: Full Integration ✅
- Prompt 19: Tests & Verification ✅

4. Run all verifications:
python -m pytest tests/ -v --tb=short
docker-compose up --build

5. Git commit:
git add .
git commit -m "Phase 2 Complete - Orchestrator + HR Agent with 3-Tier System"
git push

Expected in docker logs:
"Orchestrator: Routing user=default to general agent tier=tier2"
"HR Agent ready" (when HR user processes)

PHASE 2 COMPLETE! 🎉
```

---

## QUICK REFERENCE

### Verify All Prompts
```bash
# After each prompt run its verify command
# After Prompt 15 run:
python scripts/setup_db.py

# After Prompt 18 run:
docker-compose up --build

# After Prompt 19 run:
python -m pytest tests/ -v
```

### Git Commit After Each Prompt
```bash
git add .
git commit -m "Prompt XX complete: [description]"
```

### How to Start
Tell Claude Code exactly this:
```
Please read these 4 files completely:
1. SPEC.md
2. CONTEXT.md
3. PHASE2_SPEC.md
4. PHASE2_PROMPTS.md

After reading, confirm you understand the project.
Then wait for me to say which prompt to implement.
```

Then say: "Now implement Prompt 11"