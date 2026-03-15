# PHASE 5 PROMPTS — HireAI Platform
## AI Router + Multi-Provider Integration + Real Email Pipeline
### Complete Implementation Guide for Claude Code

---

## CONTEXT (Read Before Starting)

**Project:** HireAI — Intelligent Email Agents Platform
**Backend:** FastAPI at `/mnt/e/Digital_AI_WorkForce/hireai-gmailmind/`
**Frontend:** Next.js 14 at `/mnt/e/Digital_AI_WorkForce/hireai-frontend/`
**Database:** Neon PostgreSQL (cloud)
**Deployed Frontend:** https://hireai-frontend.vercel.app
**Backend Host:** Railway
**Contact:** hireaidigitalemployee@gmail.com

**AI Providers (Phase 5):**
- Gemini (google-generativeai) → Free tier, HireAI managed key
- Groq (groq) → Free tier, HireAI managed key
- OpenAI (openai) → Paid tier, BYOK only
- Claude/Anthropic (anthropic) → Paid tier, BYOK only

**Tier → Provider Rules:**
- Free Trial → Gemini or Groq only (HireAI managed keys)
- Tier 1 Starter ($19) → Gemini or Groq only (HireAI managed keys)
- Tier 2 Professional ($49) → Any provider (managed or BYOK)
- Tier 3 Enterprise ($99) → Any provider (managed or BYOK)

**Keys Already Available:**
- GEMINI_API_KEY → In Railway env vars
- GROQ_API_KEY → Add to Railway env vars
- OPENAI_API_KEY → BYOK only (user provides)
- ANTHROPIC_API_KEY → BYOK only (user provides)

**Phases Already Complete:**
- Phase 1: Core agent + Gmail integration + memory system
- Phase 2: Multi-agent orchestrator + HR agent + feature gates
- Phase 2.5: Security (API keys, encryption, rate limiting, headers)
- Phase 3: Real Estate agent + E-commerce agent
- Phase 4: Next.js frontend + dashboard + auth + all pages
- Phase 4.5: Setup wizard AI model selection, agent health, usage meter, billing

---

## HOW TO USE THESE PROMPTS
1. Open hireai-gmailmind/ project in Claude Code
2. First say:
   "Please read PHASE5_PROMPTS.md"
3. Then say: "Now implement Prompt 71"
4. Verify → git commit → then say "Now implement Prompt 72"
5. Continue until Prompt 85

## IMPORTANT RULES FOR CLAUDE CODE
- Do NOT break any existing features from Phases 1–4.5
- Do NOT remove any existing endpoints or tables
- All 4 agents (General, HR, Real Estate, E-commerce) must work with all providers
- Free users MUST only use Gemini or Groq — never bill them
- BYOK keys stored encrypted in database (use existing EncryptionManager)
- Test after every prompt before moving to next
- The AI Router is the SINGLE entry point for all LLM calls

---

## PROMPT 71 — AI ROUTER CORE

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 71: AI Router Core

Create the central AI router that all agents will use instead of calling
OpenAI/Anthropic directly. This is the most important file in Phase 5.

1. Create config/ai_router.py:

   class AIRouter:
       """Central router for all AI/LLM calls.

       Reads user's ai_provider from user_agents table,
       routes to correct provider, returns unified response.
       """

       PROVIDER_MAP = {
           "gemini": "_call_gemini",
           "groq": "_call_groq",
           "openai": "_call_openai",
           "claude": "_call_claude",
       }

       # Free-tier providers (no BYOK needed)
       FREE_PROVIDERS = {"gemini", "groq"}

       # Paid-tier providers (BYOK or managed)
       PAID_PROVIDERS = {"openai", "claude", "gemini", "groq"}

       # Tiers that can use any provider
       PAID_TIERS = {"tier2", "tier3"}

       def __init__(self):
           self.logger = logging.getLogger(__name__)

       async def generate(
           self,
           user_id: str,
           system_prompt: str,
           user_message: str,
           max_tokens: int = 1024,
           temperature: float = 0.7,
       ) -> dict:
           """Main entry point. Returns {"content": str, "provider": str, "model": str}"""

           # 1. Load user config from user_agents table
           provider, api_key, tier = self._get_user_config(user_id)

           # 2. Enforce tier restrictions
           provider = self._enforce_tier(provider, tier)

           # 3. Resolve API key (BYOK or managed)
           resolved_key = self._resolve_key(provider, api_key)

           # 4. Call the correct provider
           method = getattr(self, self.PROVIDER_MAP[provider])
           result = await method(system_prompt, user_message, resolved_key, max_tokens, temperature)

           return result

       def _get_user_config(self, user_id: str) -> tuple[str, str | None, str]:
           """Read ai_provider, ai_api_key, tier from user_agents table."""
           db = SessionLocal()
           try:
               row = db.execute(
                   text("SELECT ai_provider, ai_api_key, tier FROM user_agents WHERE user_id = :uid"),
                   {"uid": user_id},
               ).fetchone()
               if row:
                   return (row[0] or "gemini", row[1], row[2] or "trial")
               return ("gemini", None, "trial")
           finally:
               db.close()

       def _enforce_tier(self, provider: str, tier: str) -> str:
           """Free/trial/tier1 users forced to gemini or groq."""
           if tier not in self.PAID_TIERS and provider not in self.FREE_PROVIDERS:
               self.logger.warning(
                   "User on tier=%s tried provider=%s, forcing gemini", tier, provider
               )
               return "gemini"
           return provider

       def _resolve_key(self, provider: str, byok_key: str | None) -> str:
           """Use BYOK key if provided, else fall back to env var."""
           if byok_key:
               return byok_key
           env_map = {
               "gemini": "GEMINI_API_KEY",
               "groq": "GROQ_API_KEY",
               "openai": "OPENAI_API_KEY",
               "claude": "ANTHROPIC_API_KEY",
           }
           key = os.environ.get(env_map.get(provider, ""), "")
           if not key:
               raise ValueError(f"No API key for provider={provider}. Set {env_map[provider]} or provide BYOK key.")
           return key

       async def _call_gemini(self, system_prompt, user_message, api_key, max_tokens, temperature) -> dict:
           """Call Google Gemini API."""
           import google.generativeai as genai
           genai.configure(api_key=api_key)
           model = genai.GenerativeModel("gemini-1.5-flash")

           prompt = f"{system_prompt}\n\nUser message:\n{user_message}"
           response = model.generate_content(
               prompt,
               generation_config=genai.types.GenerationConfig(
                   max_output_tokens=max_tokens,
                   temperature=temperature,
               ),
           )
           return {
               "content": response.text,
               "provider": "gemini",
               "model": "gemini-1.5-flash",
           }

       async def _call_groq(self, system_prompt, user_message, api_key, max_tokens, temperature) -> dict:
           """Call Groq API (Llama)."""
           from groq import Groq
           client = Groq(api_key=api_key)

           response = client.chat.completions.create(
               model="llama-3.1-8b-instant",
               messages=[
                   {"role": "system", "content": system_prompt},
                   {"role": "user", "content": user_message},
               ],
               max_tokens=max_tokens,
               temperature=temperature,
           )
           return {
               "content": response.choices[0].message.content,
               "provider": "groq",
               "model": "llama-3.1-8b-instant",
           }

       async def _call_openai(self, system_prompt, user_message, api_key, max_tokens, temperature) -> dict:
           """Call OpenAI API."""
           from openai import OpenAI
           client = OpenAI(api_key=api_key)

           response = client.chat.completions.create(
               model="gpt-4o-mini",
               messages=[
                   {"role": "system", "content": system_prompt},
                   {"role": "user", "content": user_message},
               ],
               max_tokens=max_tokens,
               temperature=temperature,
           )
           return {
               "content": response.choices[0].message.content,
               "provider": "openai",
               "model": "gpt-4o-mini",
           }

       async def _call_claude(self, system_prompt, user_message, api_key, max_tokens, temperature) -> dict:
           """Call Anthropic Claude API."""
           from anthropic import Anthropic
           client = Anthropic(api_key=api_key)

           response = client.messages.create(
               model="claude-haiku-3-5",
               max_tokens=max_tokens,
               system=system_prompt,
               messages=[{"role": "user", "content": user_message}],
           )
           return {
               "content": response.content[0].text,
               "provider": "claude",
               "model": "claude-haiku-3-5",
           }

2. Add required imports at top of ai_router.py:
   import logging
   import os
   from sqlalchemy import text
   from config.database import SessionLocal

3. Install new dependencies:
   pip install google-generativeai groq
   Add to requirements.txt:
   google-generativeai
   groq

4. Add env vars to .env.example:
   GEMINI_API_KEY=your-gemini-key
   GROQ_API_KEY=your-groq-key

Verification:
- python -c "from config.ai_router import AIRouter; print('AIRouter OK')"
- Ensure no import errors
- Check that all 4 provider methods exist

Git: git add . && git commit -m "Prompt 71: AI Router core with 4 providers"
```

---

## PROMPT 72 — AI ROUTER TESTS + ERROR HANDLING

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 72: AI Router Tests + Error Handling

Add robust error handling and fallback logic to the AI Router,
plus comprehensive tests.

1. Update config/ai_router.py — add error handling:

   Add to AIRouter class:

   async def generate(self, ...) -> dict:
       """Main entry point with fallback logic."""
       try:
           # ... existing logic ...
           result = await method(...)
           return result
       except Exception as exc:
           self.logger.error("Provider %s failed: %s", provider, exc)

           # Fallback: try alternate free provider
           if provider == "gemini":
               fallback = "groq"
           elif provider == "groq":
               fallback = "gemini"
           else:
               fallback = "gemini"  # paid provider failed, try free

           try:
               self.logger.info("Falling back to %s", fallback)
               fallback_key = self._resolve_key(fallback, None)
               fallback_method = getattr(self, self.PROVIDER_MAP[fallback])
               result = await fallback_method(
                   system_prompt, user_message, fallback_key, max_tokens, temperature
               )
               result["fallback"] = True
               result["original_provider"] = provider
               return result
           except Exception as fallback_exc:
               self.logger.error("Fallback %s also failed: %s", fallback, fallback_exc)
               return {
                   "content": "I apologize, but I'm unable to process this request right now. Please try again later.",
                   "provider": "none",
                   "model": "none",
                   "error": str(exc),
               }

   Add a health check method:

   async def check_provider(self, provider: str) -> dict:
       """Test if a provider is working."""
       try:
           key = self._resolve_key(provider, None)
           method = getattr(self, self.PROVIDER_MAP[provider])
           result = await method("You are a test assistant.", "Say hello.", key, 10, 0.1)
           return {"provider": provider, "status": "healthy", "model": result["model"]}
       except Exception as exc:
           return {"provider": provider, "status": "error", "error": str(exc)}

2. Create tests/test_ai_router.py:

   import pytest
   from unittest.mock import patch, MagicMock
   from config.ai_router import AIRouter

   Test cases:
   - test_enforce_tier_free_user_blocked_from_openai
   - test_enforce_tier_free_user_allowed_gemini
   - test_enforce_tier_paid_user_allowed_any
   - test_resolve_key_byok_preferred
   - test_resolve_key_env_fallback
   - test_resolve_key_missing_raises
   - test_get_user_config_default
   - test_generate_calls_correct_provider (mock provider methods)
   - test_generate_fallback_on_error
   - test_check_provider_healthy (mock)
   - test_check_provider_error (mock)

3. Add API endpoint to test providers:
   In api/routes/frontend_routes.py add:

   @router.get("/agent/providers")
   async def get_available_providers(user: dict = Depends(get_current_user)):
       """List available AI providers for the user's tier."""
       user_id = user.get("sub", "")
       router = AIRouter()
       _, _, tier = router._get_user_config(user_id)

       providers = [
           {"id": "gemini", "name": "Google Gemini", "available": True, "free": True},
           {"id": "groq", "name": "Groq (Llama)", "available": True, "free": True},
           {"id": "openai", "name": "OpenAI GPT-4", "available": tier in AIRouter.PAID_TIERS, "free": False},
           {"id": "claude", "name": "Claude (Anthropic)", "available": tier in AIRouter.PAID_TIERS, "free": False},
       ]
       return _ok({"providers": providers, "tier": tier})

Verification:
- cd /mnt/e/Digital_AI_WorkForce/hireai-gmailmind
- python -m pytest tests/test_ai_router.py -v
- All tests pass

Git: git add . && git commit -m "Prompt 72: AI Router error handling, fallback, tests"
```

---

## PROMPT 73 — GEMINI INTEGRATION FOR ALL AGENTS

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 73: Gemini Integration for All 4 Agents

Update all 4 agents to use AIRouter instead of OpenAI Agents SDK directly.

1. Update agents/base_agent.py:

   Add to BaseAgent class:

   from config.ai_router import AIRouter

   class BaseAgent(ABC):
       # ... existing code ...

       def __init__(self):
           self.ai_router = AIRouter()

       async def process_email(self, user_id: str, email: dict) -> dict:
           """Process a single email using the AI Router.

           1. Classify the email
           2. Build system prompt based on tier
           3. Call AI Router
           4. Parse and return decision
           """
           tier = self._get_user_tier(user_id)
           category = self.classify_email(email)
           system_prompt = self.get_system_prompt(tier)

           user_message = self.format_email_summary(email)
           user_message += f"\n\nEmail Category: {category}"
           user_message += "\n\nDecide: AUTO_REPLY, DRAFT_REPLY, LABEL_ARCHIVE, SCHEDULE_FOLLOWUP, or ESCALATE"
           user_message += "\nProvide your response in this format:"
           user_message += "\nACTION: <action>"
           user_message += "\nREPLY: <reply text if applicable>"
           user_message += "\nREASON: <brief reason>"

           result = await self.ai_router.generate(
               user_id=user_id,
               system_prompt=system_prompt,
               user_message=user_message,
               max_tokens=512,
               temperature=0.3,
           )

           return {
               "category": category,
               "ai_response": result["content"],
               "provider": result["provider"],
               "model": result["model"],
               "action": self._parse_action(result["content"]),
           }

       def _parse_action(self, ai_response: str) -> str:
           """Parse ACTION from AI response text."""
           for line in ai_response.split("\n"):
               if line.strip().upper().startswith("ACTION:"):
                   action = line.split(":", 1)[1].strip().upper()
                   valid = {"AUTO_REPLY", "DRAFT_REPLY", "LABEL_ARCHIVE", "SCHEDULE_FOLLOWUP", "ESCALATE"}
                   return action if action in valid else "DRAFT_REPLY"
           return "DRAFT_REPLY"

       def _get_user_tier(self, user_id: str) -> str:
           """Get user tier from database."""
           from config.database import SessionLocal
           from sqlalchemy import text
           db = SessionLocal()
           try:
               row = db.execute(
                   text("SELECT tier FROM user_agents WHERE user_id = :uid"),
                   {"uid": user_id},
               ).fetchone()
               return row[0] if row else "trial"
           finally:
               db.close()

2. Update agents/general/general_agent.py:
   - Import AIRouter (already via base)
   - Ensure get_system_prompt works for all providers (no OpenAI-specific format)
   - Test with Gemini

3. Update agents/hr/hr_agent.py:
   - Same updates
   - HR-specific prompts must work with Gemini/Groq

4. Update agents/real_estate/real_estate_agent.py:
   - Same updates
   - Real estate prompts must work with Gemini/Groq

5. Update agents/ecommerce/ecommerce_agent.py:
   - Same updates
   - E-commerce prompts must work with Gemini/Groq

Key: All system prompts must be plain text — no OpenAI-specific
function calling or tool_use format. AI Router handles the abstraction.

Verification:
- python -c "from agents.general.general_agent import GeneralAgent; print('GeneralAgent OK')"
- python -c "from agents.hr.hr_agent import HRAgent; print('HRAgent OK')"
- python -c "from agents.real_estate.real_estate_agent import RealEstateAgent; print('RealEstateAgent OK')"
- python -c "from agents.ecommerce.ecommerce_agent import EcommerceAgent; print('EcommerceAgent OK')"
- No import errors

Git: git add . && git commit -m "Prompt 73: All 4 agents use AI Router + Gemini support"
```

---

## PROMPT 74 — GROQ INTEGRATION + MODEL SELECTION

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 74: Groq Integration + Model Selection

Fine-tune Groq integration and add model selection per provider.

1. Update config/ai_router.py — model selection:

   Add model maps:

   PROVIDER_MODELS = {
       "gemini": {
           "default": "gemini-1.5-flash",
           "tier1": "gemini-1.5-flash",
           "tier2": "gemini-1.5-pro",
           "tier3": "gemini-1.5-pro",
       },
       "groq": {
           "default": "llama-3.1-8b-instant",
           "tier1": "llama-3.1-8b-instant",
           "tier2": "llama-3.1-70b-versatile",
           "tier3": "llama-3.1-70b-versatile",
       },
       "openai": {
           "default": "gpt-4o-mini",
           "tier1": "gpt-4o-mini",
           "tier2": "gpt-4o",
           "tier3": "gpt-4o",
       },
       "claude": {
           "default": "claude-haiku-3-5",
           "tier1": "claude-haiku-3-5",
           "tier2": "claude-sonnet-4-5",
           "tier3": "claude-sonnet-4-5",
       },
   }

   def _get_model(self, provider: str, tier: str) -> str:
       """Get the correct model for provider + tier combination."""
       models = self.PROVIDER_MODELS.get(provider, {})
       return models.get(tier, models.get("default", "gemini-1.5-flash"))

   Update _call_gemini to use self._get_model("gemini", tier)
   Update _call_groq to use self._get_model("groq", tier)
   Update _call_openai to use self._get_model("openai", tier)
   Update _call_claude to use self._get_model("claude", tier)

   Pass tier through generate() to all _call_* methods.

2. Add Groq-specific handling:
   - Groq has strict rate limits on free tier
   - Add retry logic with exponential backoff (max 3 retries)
   - Log rate limit errors

   import time

   async def _call_groq_with_retry(self, ...):
       for attempt in range(3):
           try:
               return await self._call_groq(...)
           except Exception as exc:
               if "rate_limit" in str(exc).lower() and attempt < 2:
                   wait = 2 ** attempt
                   self.logger.warning("Groq rate limited, retry in %ds", wait)
                   time.sleep(wait)
                   continue
               raise

3. Add GROQ_API_KEY to Railway:
   Document in .env.example:
   # Groq — Free tier (HireAI managed)
   GROQ_API_KEY=gsk_your_groq_key_here

4. Test Groq models:
   - Verify llama-3.1-8b-instant works for email classification
   - Verify response format matches expected ACTION/REPLY/REASON

Verification:
- python -c "
from config.ai_router import AIRouter
r = AIRouter()
print('Models:', r.PROVIDER_MODELS)
print('Gemini tier1:', r._get_model('gemini', 'tier1'))
print('Groq tier2:', r._get_model('groq', 'tier2'))
"

Git: git add . && git commit -m "Prompt 74: Groq integration + tier-based model selection"
```

---

## PROMPT 75 — REASONING LOOP UPDATE

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 75: Update Reasoning Loop to Use AI Router

The reasoning loop (agent/reasoning_loop.py) currently uses OpenAI
Agents SDK. Update it to use AIRouter instead.

1. Update agent/reasoning_loop.py:

   Replace OpenAI agent calls with AIRouter:

   from config.ai_router import AIRouter

   In run_agent_loop():
   - Remove OpenAI Agents SDK imports
   - Create ai_router = AIRouter()
   - For each email:
     a. Load the correct agent (from Orchestrator)
     b. Call agent.process_email(user_id, email_dict)
        (which internally uses AIRouter)
     c. Execute the returned action (reply, draft, label, etc.)
     d. Log action to action_logs table
     e. Update sender memory

   The flow becomes:

   async def run_agent_loop(user_config, user_id, single_run=True):
       # 1. Build Gmail service
       service = _build_gmail_service(user_id)
       if not service:
           return {"error": "Gmail not connected"}

       # 2. Fetch new emails
       emails = _fetch_new_emails(service)
       if not emails:
           return {"processed": 0, "message": "No new emails"}

       # 3. Load correct agent via Orchestrator
       from orchestrator.orchestrator import Orchestrator
       orchestrator = Orchestrator()
       agent = orchestrator.get_agent_for_user(user_id)

       # 4. Process each email
       results = []
       for email in emails:
           try:
               decision = await agent.process_email(user_id, email)

               # 5. Execute action
               action_result = await _execute_action(
                   service, email, decision, user_config
               )

               # 6. Log to database
               _log_action(user_id, email, decision, action_result)

               # 7. Update sender memory
               _update_sender_memory(email)

               results.append({
                   "email_from": email.get("from", ""),
                   "action": decision["action"],
                   "provider": decision["provider"],
               })
           except Exception as exc:
               logger.error("Failed processing email: %s", exc)
               results.append({"email_from": email.get("from", ""), "error": str(exc)})

       return {"processed": len(results), "results": results}

   async def _execute_action(service, email, decision, user_config):
       """Execute the AI's decision (reply, draft, label, etc.)."""
       action = decision.get("action", "DRAFT_REPLY")
       ai_response = decision.get("ai_response", "")

       if action == "AUTO_REPLY":
           # Parse reply text from AI response
           reply_text = _extract_reply(ai_response)
           if reply_text and user_config.get("autonomy", {}).get("auto_reply_known_contacts"):
               _send_reply(service, email, reply_text)
               return {"status": "sent", "action": "auto_replied"}
           else:
               _create_draft(service, email, reply_text)
               return {"status": "drafted", "action": "draft_created"}

       elif action == "DRAFT_REPLY":
           reply_text = _extract_reply(ai_response)
           _create_draft(service, email, reply_text)
           return {"status": "drafted", "action": "draft_created"}

       elif action == "ESCALATE":
           return {"status": "escalated", "action": "escalated"}

       elif action == "LABEL_ARCHIVE":
           return {"status": "archived", "action": "labeled_archived"}

       elif action == "SCHEDULE_FOLLOWUP":
           return {"status": "followup", "action": "followup_scheduled"}

       return {"status": "skipped", "action": "no_action"}

2. Keep backward compatibility:
   - Don't remove tool_wrappers.py (still used for Gmail operations)
   - Don't remove gmailmind.py (system prompt builder still used)
   - Keep existing Gmail service builder functions

3. Update scheduler/tasks.py:
   - The Celery task run_gmailmind_for_user should call the updated loop
   - Add user_id to the agent_status update

Verification:
- python -c "from agent.reasoning_loop import run_agent_loop; print('Loop OK')"
- No import errors
- Existing scheduler tasks still importable

Git: git add . && git commit -m "Prompt 75: Reasoning loop uses AI Router instead of OpenAI SDK"
```

---

## PROMPT 76 — EMAIL PROCESSING PIPELINE

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 76: Complete Email Processing Pipeline

Wire everything together: Gmail → Agent → AI Router → Action → Database.

1. Update agent/tool_wrappers.py:

   Keep all existing Gmail tool functions but make them standalone
   (not tied to OpenAI function calling):

   - read_emails(service, max_results=10) → list[dict]
   - reply_to_email(service, message_id, reply_text) → bool
   - create_draft(service, to, subject, body) → str (draft_id)
   - label_email(service, message_id, label) → bool
   - search_emails(service, query, max_results=10) → list[dict]
   - mark_as_read(service, message_id) → bool

   Each function takes a Gmail service object and returns plain data.
   NO OpenAI tool decorators or schemas.

2. Create agent/email_processor.py:

   class EmailProcessor:
       """High-level email processing pipeline."""

       def __init__(self, user_id: str):
           self.user_id = user_id
           self.ai_router = AIRouter()
           self.logger = logging.getLogger(__name__)

       async def process_inbox(self) -> dict:
           """Full pipeline: fetch → classify → decide → act → log."""

           # 1. Get Gmail service
           service = self._build_service()
           if not service:
               return {"error": "Gmail not connected", "processed": 0}

           # 2. Fetch unread emails
           emails = read_emails(service, max_results=20)
           if not emails:
               return {"processed": 0, "message": "No new emails"}

           # 3. Get agent for this user
           agent = self._get_agent()

           # 4. Process each email
           processed = 0
           for email in emails:
               try:
                   result = await agent.process_email(self.user_id, email)
                   await self._execute(service, email, result)
                   self._log(email, result)
                   processed += 1
               except Exception as exc:
                   self.logger.error("Email processing failed: %s", exc)

           # 5. Update agent status
           self._update_status(processed)

           return {"processed": processed, "total": len(emails)}

       def _build_service(self):
           """Build Gmail API service from stored credentials."""
           from agent.reasoning_loop import _build_gmail_service
           return _build_gmail_service(self.user_id)

       def _get_agent(self):
           """Get the correct agent for this user."""
           from orchestrator.orchestrator import Orchestrator
           return Orchestrator().get_agent_for_user(self.user_id)

       async def _execute(self, service, email, decision):
           """Execute the AI decision."""
           # ... (same as _execute_action from Prompt 75)

       def _log(self, email, decision):
           """Log action to action_logs table."""
           db = SessionLocal()
           try:
               db.execute(
                   text("""
                       INSERT INTO action_logs
                           (user_id, email_from, action_taken, metadata, timestamp)
                       VALUES
                           (:uid, :from, :action, :meta::jsonb, NOW())
                   """),
                   {
                       "uid": self.user_id,
                       "from": email.get("from", ""),
                       "action": decision.get("action", "unknown"),
                       "meta": json.dumps({
                           "subject": email.get("subject", ""),
                           "category": decision.get("category", ""),
                           "provider": decision.get("provider", ""),
                           "model": decision.get("model", ""),
                       }),
                   },
               )
               db.commit()
           finally:
               db.close()

       def _update_status(self, processed: int):
           """Update agent_status / user_agents with last run info."""
           db = SessionLocal()
           try:
               db.execute(
                   text("""
                       UPDATE user_agents
                       SET last_processed_at = NOW(),
                           last_error = NULL,
                           updated_at = NOW()
                       WHERE user_id = :uid
                   """),
                   {"uid": self.user_id},
               )
               db.commit()
           finally:
               db.close()

3. Update scheduler/tasks.py:
   Use EmailProcessor instead of direct reasoning loop:

   @celery_app.task(...)
   def run_gmailmind_for_user(user_id: str):
       processor = EmailProcessor(user_id)
       import asyncio
       result = asyncio.run(processor.process_inbox())
       return result

Verification:
- python -c "from agent.email_processor import EmailProcessor; print('EmailProcessor OK')"
- python -c "from scheduler.tasks import run_gmailmind_for_user; print('Task OK')"

Git: git add . && git commit -m "Prompt 76: Complete email processing pipeline with AI Router"
```

---

## PROMPT 77 — FRONTEND AGENT STATUS (REAL DATA)

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 77: Dashboard Shows Real Agent Data

Update frontend to show real data from backend instead of mock data.

1. Update frontend api hooks — /mnt/e/Digital_AI_WorkForce/hireai-frontend/

   In src/hooks/use-dashboard.ts (create if not exists):

   import useSWR from "swr";
   import { api } from "@/lib/api";

   const fetcher = (url: string) => api.get(url).then(r => r.data?.data || r.data);

   export function useDashboardStats() {
       return useSWR("/api/dashboard/stats", fetcher, { refreshInterval: 30000 });
   }

   export function useAgentStatus() {
       return useSWR("/api/agent/status", fetcher, { refreshInterval: 10000 });
   }

   export function useRecentEmails(page = 1) {
       return useSWR(`/api/emails/recent?page=${page}&limit=10`, fetcher, { refreshInterval: 30000 });
   }

   export function useAgentHealth() {
       return useSWR("/api/health/user", fetcher, { refreshInterval: 30000 });
   }

2. Update src/app/dashboard/page.tsx:
   - Import and use the SWR hooks
   - Show real emails_today, auto_replied, escalated counts
   - Show real agent status (running/paused/error)
   - Usage meter uses real emails_this_month from backend

3. Update backend /api/dashboard/stats endpoint:
   In api/routes/dashboard_routes.py (or frontend_routes.py):

   @router.get("/stats")
   async def get_dashboard_stats(user: dict = Depends(get_current_user)):
       user_id = user.get("sub", "")
       db = SessionLocal()
       try:
           today = datetime.now(timezone.utc).date()
           yesterday = today - timedelta(days=1)
           month_start = today.replace(day=1)

           # Today's stats
           today_row = db.execute(text("""
               SELECT COUNT(*),
                      COUNT(*) FILTER (WHERE action_taken = 'auto_replied'),
                      COUNT(*) FILTER (WHERE action_taken = 'escalated')
               FROM action_logs
               WHERE user_id = :uid AND DATE(timestamp) = :today
           """), {"uid": user_id, "today": str(today)}).fetchone()

           # Yesterday
           yesterday_row = db.execute(text("""
               SELECT COUNT(*),
                      COUNT(*) FILTER (WHERE action_taken = 'auto_replied')
               FROM action_logs
               WHERE user_id = :uid AND DATE(timestamp) = :yesterday
           """), {"uid": user_id, "yesterday": str(yesterday)}).fetchone()

           # This month
           month_row = db.execute(text("""
               SELECT COUNT(*) FROM action_logs
               WHERE user_id = :uid AND DATE(timestamp) >= :month_start
           """), {"uid": user_id, "month_start": str(month_start)}).fetchone()

           return _ok({
               "emails_today": today_row[0] if today_row else 0,
               "auto_replied_today": today_row[1] if today_row else 0,
               "escalated_today": today_row[2] if today_row else 0,
               "avg_response_time": 2.3,
               "emails_yesterday": yesterday_row[0] if yesterday_row else 0,
               "auto_replied_yesterday": yesterday_row[1] if yesterday_row else 0,
               "agent_uptime_hours": 24,
               "emails_in_queue": 0,
               "emails_this_month": month_row[0] if month_row else 0,
           })
       except Exception as exc:
           logger.error("Dashboard stats error: %s", exc)
           return _ok({
               "emails_today": 0, "auto_replied_today": 0,
               "escalated_today": 0, "avg_response_time": 0,
               "emails_yesterday": 0, "auto_replied_yesterday": 0,
               "agent_uptime_hours": 0, "emails_in_queue": 0,
               "emails_this_month": 0,
           })
       finally:
           db.close()

4. Health indicator should use real data from /api/health/user endpoint.

Verification:
- npm run build (frontend) → 0 errors
- Backend endpoints return valid JSON
- Dashboard shows "0" for counts (not mock data)

Git: git add . && git commit -m "Prompt 77: Dashboard shows real agent data from backend"
```

---

## PROMPT 78 — AGENT AUTO-START AFTER SETUP

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 78: Agent Auto-Start After Setup Wizard

When user completes setup wizard, automatically start their agent.

1. Update backend POST /auth/setup endpoint (auth.py):

   After creating user_agents record, dispatch Celery task:

   # At the end of save_setup(), after db.commit():
   try:
       from scheduler.tasks import run_gmailmind_for_user
       run_gmailmind_for_user.delay(user_id)
       logger.info("Auto-started agent for user: %s", user_id)
   except Exception as exc:
       logger.warning("Could not auto-start agent: %s", exc)
       # Non-fatal — user can start manually

2. Add manual start/stop endpoints in frontend_routes.py:

   @router.post("/agent/start")
   async def start_agent(user: dict = Depends(get_current_user)):
       """Manually start the agent."""
       user_id = user.get("sub", "")
       try:
           # Update status
           db = SessionLocal()
           try:
               db.execute(
                   text("UPDATE user_agents SET is_paused = false WHERE user_id = :uid"),
                   {"uid": user_id},
               )
               db.commit()
           finally:
               db.close()

           # Dispatch task
           try:
               from scheduler.tasks import run_gmailmind_for_user
               run_gmailmind_for_user.delay(user_id)
           except Exception:
               pass

           return _ok({"message": "Agent started"})
       except Exception as exc:
           logger.error("Start agent failed: %s", exc)
           return _ok({"message": "Agent started"})

   @router.post("/agent/stop")
   async def stop_agent(user: dict = Depends(get_current_user)):
       """Stop the agent."""
       user_id = user.get("sub", "")
       try:
           db = SessionLocal()
           try:
               db.execute(
                   text("UPDATE user_agents SET is_paused = true WHERE user_id = :uid"),
                   {"uid": user_id},
               )
               db.commit()
           finally:
               db.close()
       except Exception:
           pass
       return _ok({"message": "Agent stopped"})

3. Update frontend dashboard Agent page:
   - Start/Stop buttons should call /api/agent/start and /api/agent/stop
   - Show real status from /api/agent/status
   - After setup wizard → agent shows "Active"

4. Update frontend setup-wizard.tsx:
   - After successful /auth/setup call, the backend auto-starts the agent
   - No frontend changes needed — backend handles it

Verification:
- POST /auth/setup → user_agents row created + agent task dispatched
- GET /api/agent/status → is_running: true
- Dashboard shows "Active" after setup

Git: git add . && git commit -m "Prompt 78: Agent auto-start after setup + start/stop endpoints"
```

---

## PROMPT 79 — GMAIL OAUTH REAL FLOW

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 79: Real Gmail OAuth Connection

The setup wizard currently fakes Gmail connection. Make it real.

1. Update frontend setup wizard step 2 (Connect Gmail):

   Replace the fake handleConnectGmail with real OAuth:

   const handleConnectGmail = () => {
       // Open backend OAuth URL in popup/redirect
       const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
       const oauthUrl = `${backendUrl}/auth/google?setup=true&email=${encodeURIComponent(data.gmailAddress)}`;
       window.open(oauthUrl, "_blank", "width=500,height=600");
   };

   // Listen for OAuth callback message
   useEffect(() => {
       const handler = (event: MessageEvent) => {
           if (event.data?.type === "gmail-connected") {
               setData(prev => ({ ...prev, gmailConnected: true }));
           }
       };
       window.addEventListener("message", handler);
       return () => window.removeEventListener("message", handler);
   }, []);

2. Update backend /auth/google/callback:

   After saving OAuth token, if setup=true in state:
   - Return HTML page that posts message to parent window
   - window.opener.postMessage({ type: "gmail-connected" }, "*")
   - Then close the popup

3. Alternative simple flow (if OAuth not ready):

   If Google OAuth is not configured yet, keep the simple flow:
   - User enters Gmail address
   - Click "Connect" → validates format → marks as connected
   - Backend stores the email address
   - Real OAuth can be added in Phase 6

   Add a note in the UI:
   "Gmail will be fully connected when you authorize via Google"

4. Store Gmail address in user_agents:
   The /auth/setup endpoint already saves gmail_email.
   Ensure the dashboard reads it from there.

Verification:
- Setup wizard Gmail step works (simple or OAuth)
- Gmail address saved to user_agents table
- Agent status shows gmail_connected value

Git: git add . && git commit -m "Prompt 79: Gmail connection flow in setup wizard"
```

---

## PROMPT 80 — PROVIDER HEALTH CHECK API

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 80: Provider Health Check + Status API

Add endpoints to check if AI providers are working.

1. Add to api/routes/frontend_routes.py:

   @router.get("/agent/provider-health")
   async def check_provider_health(user: dict = Depends(get_current_user)):
       """Check health of user's configured AI provider."""
       user_id = user.get("sub", "")
       router_instance = AIRouter()
       provider, _, tier = router_instance._get_user_config(user_id)
       provider = router_instance._enforce_tier(provider, tier)

       health = await router_instance.check_provider(provider)
       return _ok(health)

   @router.get("/agent/all-providers-health")
   async def check_all_providers():
       """Check health of all available providers (admin)."""
       router_instance = AIRouter()
       results = {}
       for provider in ["gemini", "groq"]:
           try:
               results[provider] = await router_instance.check_provider(provider)
           except Exception as exc:
               results[provider] = {"status": "error", "error": str(exc)}
       return _ok(results)

2. Update frontend agent page:
   - Show provider status indicator (green/red dot)
   - Show which model is being used
   - Show fallback info if provider failed

3. Add to dashboard health indicator:
   - Include AI provider health in the health score
   - If provider is down, health score drops
   - Show "AI: Gemini (healthy)" or "AI: Groq (error)"

Verification:
- GET /api/agent/provider-health → returns provider status
- Dashboard shows AI provider health
- npm run build → 0 errors

Git: git add . && git commit -m "Prompt 80: Provider health check endpoints + dashboard indicator"
```

---

## PROMPT 81 — UPDATE EXISTING TESTS

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 81: Update All Existing Tests for AI Router

Update existing tests to work with the new AI Router system.

1. Find all existing test files:
   - tests/test_general_agent.py
   - tests/test_hr_agent.py
   - tests/test_real_estate_agent.py
   - tests/test_ecommerce_agent.py
   - tests/test_orchestrator.py
   - tests/test_feature_gates.py
   - tests/test_reasoning_loop.py
   - tests/test_memory.py
   - tests/test_security.py
   - Any other test files

2. Update agent tests:
   - Mock AIRouter.generate() instead of OpenAI calls
   - Ensure process_email returns correct format
   - Test with mock Gemini responses
   - Test with mock Groq responses

3. Update orchestrator tests:
   - Verify it routes to correct agent
   - Verify tier enforcement works
   - Test free user → Gemini/Groq only
   - Test paid user → any provider

4. Update reasoning loop tests:
   - Mock EmailProcessor
   - Test full pipeline with mocked providers
   - Test error handling and fallback

5. Add new test file tests/test_email_processor.py:
   - test_process_inbox_no_gmail
   - test_process_inbox_no_emails
   - test_process_inbox_success
   - test_execute_auto_reply
   - test_execute_draft
   - test_execute_escalate
   - test_log_action
   - test_update_status

6. Run full test suite:
   python -m pytest tests/ -v --tb=short

   Target: ALL tests pass (existing + new)

Verification:
- python -m pytest tests/ -v → all pass
- No import errors
- No broken tests from Phase 1-4

Git: git add . && git commit -m "Prompt 81: All tests updated for AI Router system"
```

---

## PROMPT 82 — REAL GEMINI EMAIL TEST

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 82: Real Gemini Email Processing Test

Test with a real Gmail account and real Gemini API.

1. Create scripts/test_gemini_real.py:

   """
   Real integration test: Gemini processes an email.
   Requires: GEMINI_API_KEY env var set
   """
   import asyncio
   import os
   from config.ai_router import AIRouter
   from agents.general.general_agent import GeneralAgent

   async def test_gemini_classification():
       """Test that Gemini can classify an email correctly."""
       router = AIRouter()

       # Simulate an email
       test_email = {
           "from": "john@example.com",
           "subject": "Interested in your services",
           "body": "Hi, I saw your website and I'm interested in learning more about your consulting services. Can you send me your pricing?",
           "date": "2024-01-15",
       }

       agent = GeneralAgent()
       system_prompt = agent.get_system_prompt("trial")
       user_message = agent.format_email_summary(test_email)
       user_message += "\n\nDecide: AUTO_REPLY, DRAFT_REPLY, LABEL_ARCHIVE, SCHEDULE_FOLLOWUP, or ESCALATE"
       user_message += "\nACTION: <action>\nREPLY: <reply text>\nREASON: <reason>"

       # Call Gemini directly (bypass user config)
       result = await router._call_gemini(
           system_prompt, user_message,
           os.environ["GEMINI_API_KEY"],
           512, 0.3
       )

       print("Provider:", result["provider"])
       print("Model:", result["model"])
       print("Response:", result["content"][:500])

       assert result["provider"] == "gemini"
       assert len(result["content"]) > 10
       print("\n✅ Gemini classification test PASSED")

   async def test_gemini_all_categories():
       """Test Gemini with different email types."""
       categories = [
           {"subject": "Invoice #123", "body": "Please find attached invoice for $500."},
           {"subject": "Meeting tomorrow", "body": "Can we schedule a call for 3pm?"},
           {"subject": "URGENT: Server down", "body": "Production server is not responding!"},
           {"subject": "Newsletter - March 2024", "body": "Here are this month's updates..."},
       ]

       router = AIRouter()
       for cat in categories:
           result = await router._call_gemini(
               "Classify this email as: BUSINESS, URGENT, NEWSLETTER, or PERSONAL",
               f"Subject: {cat['subject']}\nBody: {cat['body']}",
               os.environ["GEMINI_API_KEY"],
               50, 0.1
           )
           print(f"  {cat['subject']} → {result['content'].strip()}")

       print("\n✅ Gemini multi-category test PASSED")

   if __name__ == "__main__":
       asyncio.run(test_gemini_classification())
       asyncio.run(test_gemini_all_categories())

2. Create scripts/test_groq_real.py:
   Same structure but using _call_groq and GROQ_API_KEY.

3. Run tests:
   GEMINI_API_KEY=your-key python scripts/test_gemini_real.py
   GROQ_API_KEY=your-key python scripts/test_groq_real.py

Verification:
- Both scripts run without errors
- Gemini returns valid classification
- Groq returns valid classification
- Response format is parseable

Git: git add . && git commit -m "Prompt 82: Real Gemini + Groq email classification tests"
```

---

## PROMPT 83 — FRONTEND BUILD + DEPLOY

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 83: Frontend Build Verification + Deploy

Verify frontend builds cleanly with all Phase 5 changes.

1. Check all frontend files compile:
   cd /mnt/e/Digital_AI_WorkForce/hireai-frontend
   npm run build

   Must show:
   ✓ Compiled successfully
   ✓ Generating static pages (23/23)
   0 TypeScript errors

2. Verify all pages work:
   - / (landing page)
   - /login, /signup
   - /dashboard (with real data hooks)
   - /dashboard/agent (with start/stop/provider)
   - /dashboard/emails (with real email list)
   - /dashboard/analytics
   - /dashboard/settings
   - /dashboard/billing
   - /pricing, /features, /docs
   - /verify-email, /forgot-password, /reset-password

3. Fix any TypeScript errors:
   - Missing type definitions
   - Unused imports
   - Type mismatches with new API response shapes

4. Git commit all changes:
   cd /mnt/e/Digital_AI_WorkForce
   git add .
   git commit -m "Prompt 83: Frontend build verified — 0 errors"

5. Deploy to Vercel:
   cd /mnt/e/Digital_AI_WorkForce/hireai-frontend
   npx vercel --prod --yes --token <TOKEN> --scope hire-ai-1

Verification:
- npm run build → 0 errors
- Vercel deployment succeeds
- Live site loads correctly

Git: git add . && git commit -m "Prompt 83: Frontend verified and deployed"
```

---

## PROMPT 84 — BACKEND DEPLOY TO RAILWAY

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 84: Backend Deploy to Railway

Deploy the updated backend with AI Router to Railway.

1. Update requirements.txt:
   Ensure these are included:
   google-generativeai
   groq
   openai
   anthropic
   fastapi
   uvicorn
   celery
   redis
   sqlalchemy
   psycopg2-binary
   bcrypt
   PyJWT
   python-dotenv
   cryptography
   httpx
   pydantic
   pgvector
   google-api-python-client
   google-auth-oauthlib

2. Update Railway env vars:
   Add these via Railway dashboard:
   - GEMINI_API_KEY (HireAI managed — already there)
   - GROQ_API_KEY (HireAI managed — add new)

   Verify existing:
   - DATABASE_URL
   - JWT_SECRET
   - REDIS_URL (if using Celery)
   - CORS_ORIGINS (include frontend URL)

3. Verify Procfile or railway.json:
   web: uvicorn api.main:app --host 0.0.0.0 --port $PORT

4. Test health endpoint after deploy:
   curl https://your-railway-url.railway.app/health
   → {"success": true, "data": {"status": "healthy"}}

5. Test AI Router endpoint:
   curl https://your-railway-url.railway.app/api/agent/providers \
     -H "Authorization: Bearer <jwt-token>"
   → Returns list of available providers

6. Update frontend .env:
   NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app

Verification:
- Railway deploy succeeds
- /health returns healthy
- /api/agent/providers returns provider list
- Frontend can call backend APIs

Git: git add . && git commit -m "Prompt 84: Backend deployed to Railway with AI Router"
```

---

## PROMPT 85 — PHASE 5 COMPLETION + VERIFICATION

```
Please read PHASE5_PROMPTS.md first.

Now implement Prompt 85: Phase 5 Final Verification

Complete final checklist for Phase 5.

1. Verify AI Router:
   ✅ AIRouter class exists in config/ai_router.py
   ✅ Supports 4 providers: Gemini, Groq, OpenAI, Claude
   ✅ Tier enforcement works (free → Gemini/Groq only)
   ✅ Fallback logic works (if provider A fails → try provider B)
   ✅ BYOK key resolution works
   ✅ Model selection per tier works

2. Verify Agent System:
   ✅ GeneralAgent uses AIRouter
   ✅ HRAgent uses AIRouter
   ✅ RealEstateAgent uses AIRouter
   ✅ EcommerceAgent uses AIRouter
   ✅ All agents return consistent response format
   ✅ process_email works for all agents

3. Verify Email Pipeline:
   ✅ EmailProcessor class exists
   ✅ Gmail → fetch → classify → decide → act → log
   ✅ Actions: auto_reply, draft, escalate, label, followup
   ✅ Action logs saved to database
   ✅ Sender memory updated

4. Verify Dashboard:
   ✅ Agent status shows real data
   ✅ Email count shows real numbers
   ✅ Health score uses real calculation
   ✅ Usage meter shows real email count
   ✅ Provider health indicator works

5. Verify Setup Flow:
   ✅ Setup wizard → saves AI provider
   ✅ After setup → agent auto-starts
   ✅ Dashboard loads (no loop)
   ✅ Agent status shows "Active"

6. Run all tests:
   cd /mnt/e/Digital_AI_WorkForce/hireai-gmailmind
   python -m pytest tests/ -v --tb=short

   Expected: ALL tests pass

7. Create PHASE5_COMPLETION_REPORT.md:

   # Phase 5 Completion Report

   ## What Was Built
   - AI Router with 4 provider support
   - Gemini integration (free tier)
   - Groq integration (free tier)
   - OpenAI support (BYOK)
   - Claude support (BYOK)
   - Email processing pipeline
   - Real dashboard data
   - Agent auto-start
   - Provider health checks

   ## Architecture
   Gmail → EmailProcessor → Agent → AIRouter → Provider → Response
                                                    ↓
                                              action_logs DB

   ## Files Created/Modified
   - config/ai_router.py (NEW)
   - agent/email_processor.py (NEW)
   - agents/base_agent.py (MODIFIED)
   - agents/general/general_agent.py (MODIFIED)
   - agents/hr/hr_agent.py (MODIFIED)
   - agents/real_estate/real_estate_agent.py (MODIFIED)
   - agents/ecommerce/ecommerce_agent.py (MODIFIED)
   - agent/reasoning_loop.py (MODIFIED)
   - scheduler/tasks.py (MODIFIED)
   - api/routes/frontend_routes.py (MODIFIED)
   - api/routes/auth.py (MODIFIED)
   - tests/test_ai_router.py (NEW)
   - tests/test_email_processor.py (NEW)
   - scripts/test_gemini_real.py (NEW)
   - scripts/test_groq_real.py (NEW)

   ## Test Results
   - Total tests: ~290
   - All passing: ✅

   ## What's Next (Phase 5.5)
   - Stripe payment integration
   - Subscription management
   - Invoice generation
   - Payment webhook handling

8. Final git:
   cd /mnt/e/Digital_AI_WorkForce
   git add .
   git commit -m "Phase 5 Complete: AI Router + Multi-Provider + Real Pipeline"
   git push origin main

Verification:
- All 15 prompts (71-85) implemented
- All tests pass
- Frontend deployed and working
- Backend deployed and working
- Free users can use Gemini/Groq
- Setup wizard → dashboard works without loop
- Agent starts and processes emails (with valid Gmail OAuth)
```

---

## QUICK REFERENCE

| Prompt | Title | Key Files |
|--------|-------|-----------|
| 71 | AI Router Core | config/ai_router.py |
| 72 | AI Router Tests + Error Handling | tests/test_ai_router.py |
| 73 | Gemini Integration All Agents | agents/*/agent.py |
| 74 | Groq Integration + Model Selection | config/ai_router.py |
| 75 | Reasoning Loop Update | agent/reasoning_loop.py |
| 76 | Email Processing Pipeline | agent/email_processor.py |
| 77 | Frontend Real Data | src/hooks/use-dashboard.ts |
| 78 | Agent Auto-Start | auth.py, frontend_routes.py |
| 79 | Gmail OAuth Real Flow | setup-wizard.tsx |
| 80 | Provider Health Check | frontend_routes.py |
| 81 | Update Existing Tests | tests/*.py |
| 82 | Real Gemini/Groq Test | scripts/test_*.py |
| 83 | Frontend Build + Deploy | Vercel |
| 84 | Backend Deploy | Railway |
| 85 | Phase 5 Completion | PHASE5_COMPLETION_REPORT.md |

## TIER → PROVIDER MATRIX

| Tier | Gemini | Groq | OpenAI | Claude |
|------|--------|------|--------|--------|
| Trial | ✅ Managed | ✅ Managed | ❌ | ❌ |
| Tier 1 | ✅ Managed | ✅ Managed | ❌ | ❌ |
| Tier 2 | ✅ Any | ✅ Any | ✅ BYOK | ✅ BYOK |
| Tier 3 | ✅ Any | ✅ Any | ✅ BYOK | ✅ BYOK |

## MODEL MATRIX

| Provider | Free/Tier1 | Tier2/Tier3 |
|----------|-----------|-------------|
| Gemini | gemini-1.5-flash | gemini-1.5-pro |
| Groq | llama-3.1-8b-instant | llama-3.1-70b-versatile |
| OpenAI | gpt-4o-mini | gpt-4o |
| Claude | claude-haiku-3-5 | claude-sonnet-4-5 |
