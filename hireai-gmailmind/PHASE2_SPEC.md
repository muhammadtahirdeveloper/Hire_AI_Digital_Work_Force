# GmailMind — Phase 2 Specification
# Multi-Agent Orchestration System

## Overview

Phase 1 (Prompts 0-10) mein hum ne GmailMind ka base agent banaya jo:
- Gmail se emails padh leta hai
- Auto-label aur archive karta hai
- Sender memory maintain karta hai
- Docker pe deploy ho gaya hai ✅

Phase 2 mein hum same project mein expand karenge:
- Orchestrator Agent (Master Brain)
- HR Specialist Agent
- 3-Tier Subscription System
- Feature Gates per tier
- HR-specific database tables
- WhatsApp reporting

---

## Architecture

```
User signs up → Orchestrator → Routes to Specialist Agent
                             → Applies Tier Features
                             → Executes Agent
```

### New Folder Structure

```
hireai-gmailmind/
├── agent/              ← Existing Phase 1 ✅
├── tools/              ← Existing Phase 1 ✅
├── memory/             ← Existing Phase 1 ✅
├── api/                ← Existing Phase 1 ✅
├── scheduler/          ← Existing Phase 1 ✅
├── models/             ← Existing Phase 1 ✅
├── config/             ← Existing Phase 1 ✅
├── scripts/            ← Existing Phase 1 ✅
│
├── orchestrator/       ← NEW Phase 2
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── agent_registry.py
│   ├── user_router.py
│   ├── feature_gates.py
│   └── health_monitor.py
│
├── agents/             ← NEW Phase 2
│   ├── __init__.py
│   ├── base_agent.py
│   ├── general/
│   │   ├── __init__.py
│   │   └── general_agent.py
│   └── hr/
│       ├── __init__.py
│       ├── hr_agent.py
│       ├── cv_processor.py
│       ├── interview_scheduler.py
│       ├── candidate_tracker.py
│       └── hr_templates.py
│
├── skills/             ← NEW Phase 2
│   ├── __init__.py
│   ├── base_skills.py
│   └── hr_skills.py
│
├── SPEC.md             ← Existing
├── CONTEXT.md          ← Existing
├── PHASE2_SPEC.md      ← This file
└── PHASE2_PROMPTS.md   ← Prompts file
```

---

## 3-Tier System

### Tier 1 — Starter ($19/month)
- 1 Gmail account
- Max 200 emails/day
- Features: read, label, archive, basic_email_report
- NO auto-reply, NO escalation, NO HR features

### Tier 2 — Professional ($49/month)
- 3 Gmail accounts
- Max 500 emails/day
- Features: everything in Tier 1 PLUS:
  - auto_reply
  - escalation alerts (WhatsApp + Email)
  - follow_up tracker
  - whatsapp_report
  - cv_processing (HR)
  - interview_scheduler (HR)
  - candidate_tracker (HR)
  - basic_crm

### Tier 3 — Business ($99/month)
- Unlimited Gmail accounts
- Unlimited emails/day
- ALL features including:
  - advanced_analytics
  - team_management
  - api_access
  - priority_support
  - advanced_crm

---

## Industries Supported

- general → GeneralAgent (Phase 1 agent wrapped)
- hr → HRAgent (Phase 2 new)
- real_estate → RealEstateAgent (Phase 3 future)
- ecommerce → EcommerceAgent (Phase 3 future)

---

## Orchestrator Flow

```
1. User request comes in (scheduler or API)
2. Orchestrator.process_user(user_id)
3. Get user tier from user_subscriptions table
4. Get user industry from user_configs table
5. Check daily usage limit (feature_gates)
6. Get correct agent from agent_registry
7. Get available features for this tier
8. Run agent with feature-limited config
9. Update usage counter
10. Log results to action_logs
```

---

## Database Changes

### New Tables (Phase 2)
- candidates (HR candidate profiles)
- interviews (scheduled interviews)
- job_requirements (open positions)

### Updated Tables (Phase 2)
- user_subscriptions: add tier column (tier1/tier2/tier3)
- user_configs: add industry column (general/hr/real_estate/ecommerce)

---

## Key Principles

1. BACKWARD COMPATIBLE — Phase 1 features still work
2. DEFAULT VALUES — New columns have defaults (tier1, general)
3. GRACEFUL DEGRADATION — If feature not in tier, skip silently
4. SAME DOCKER — No new containers needed
5. SAME .ENV — No new environment variables needed for core features

---

## Testing Strategy

- Each prompt has a quick verify command
- Run pytest after Prompt 20
- Docker test after Prompt 19
- Manual Gmail test after full integration

---

## Important Notes for Claude Code

- Always read SPEC.md + CONTEXT.md + PHASE2_SPEC.md before starting
- Use existing patterns from Phase 1 code
- Follow same logging style (INFO/ERROR with timestamps)
- Follow same database patterns (SQLAlchemy from memory/long_term.py)
- Follow same config patterns (from config/ folder)
- Do NOT modify existing Phase 1 files unless explicitly asked
- Add new files — do not replace existing ones