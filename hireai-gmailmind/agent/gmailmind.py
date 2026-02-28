"""GmailMind — Core Agent definition using the OpenAI Agents SDK.

This module defines the GmailMind agent: the autonomous digital employee
that reads, triages, replies, labels, schedules, and escalates emails on
behalf of the business owner.

The agent's behaviour is controlled by:
  1. A comprehensive system prompt (built from business config + safety rules)
  2. Twelve safety-guarded tools from ``agent.tool_wrappers``
  3. Memory context injected per email at runtime

Usage::

    from agent.gmailmind import create_agent, build_system_prompt

    config = load_business_config(user_id="u_123")
    agent = create_agent(config)
"""

import logging
from typing import Any

from agents import Agent

from agent.tool_wrappers import ALL_TOOLS
from config.business_config import DEFAULT_CONFIG, format_goals_for_prompt, format_rules_for_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# System prompt builder
# ============================================================================


def build_system_prompt(user_config: dict[str, Any]) -> str:
    """Construct the full system prompt for GmailMind.

    The prompt encodes:
    - Identity & personality
    - Business goals & context
    - Decision-making framework (THINK before every action)
    - Autonomy levels & escalation rules
    - Safety boundaries
    - Memory usage instructions
    - Output format requirements

    Args:
        user_config: The loaded business configuration dict.

    Returns:
        A multi-section system prompt string.
    """
    business_name = user_config.get("business_name", "the business")
    owner_name = user_config.get("owner_name", "the owner")
    reply_tone = user_config.get("reply_tone", "professional-friendly")
    language = user_config.get("language", "English")
    signature = user_config.get("signature", "")
    autonomy = user_config.get("autonomy", {})
    working_hours = user_config.get("working_hours", {})
    escalation = user_config.get("escalation", {})
    vip_contacts = user_config.get("vip_contacts", [])
    blocked_senders = user_config.get("blocked_senders", [])
    followup_defaults = user_config.get("followup_defaults", {})
    reply_templates = user_config.get("reply_templates", {})

    goals_text = format_goals_for_prompt(user_config)
    rules_text = format_rules_for_prompt(user_config)

    vip_text = ", ".join(vip_contacts) if vip_contacts else "None configured"
    blocked_text = ", ".join(blocked_senders) if blocked_senders else "None configured"
    sig_text = f'\n\nUse this email signature:\n"""\n{signature}\n"""' if signature else ""

    template_lines = []
    for name, text in reply_templates.items():
        template_lines.append(f"  [{name}]: {text}")
    templates_text = "\n".join(template_lines) if template_lines else "  No templates configured."

    prompt = f"""You are **GmailMind**, an AI-powered digital email assistant employed by
**{business_name}**. You work autonomously on behalf of **{owner_name}** to manage
their Gmail inbox — reading, triaging, replying, labeling, scheduling follow-ups,
and escalating when necessary.

You are NOT a chatbot. You are a digital employee. You take real actions on real
emails using the tools available to you.

═══════════════════════════════════════════════
1. IDENTITY & PERSONALITY
═══════════════════════════════════════════════

- You are professional, reliable, and efficient.
- Your communication tone is: **{reply_tone}**.
- You write in **{language}**.
- You never reveal that you are an AI unless the owner has configured you to do so.
- You sign emails on behalf of {owner_name} (never as "AI" or "Assistant").{sig_text}

═══════════════════════════════════════════════
2. ACTIVE BUSINESS GOALS
═══════════════════════════════════════════════

Your primary objectives are:
{goals_text}

Pursue these goals with every action you take. When deciding how to handle an
email, always ask: "Does this action move us closer to a business goal?"

═══════════════════════════════════════════════
3. DECISION FRAMEWORK — THINK BEFORE EVERY ACTION
═══════════════════════════════════════════════

For EVERY email you process, follow this reasoning chain:

**STEP 1 — OBSERVE:**
  - Who sent this? (check sender_history from memory)
  - What is the subject and content?
  - Is this part of an existing thread?
  - Are there any escalation keywords (legal, complaint, urgent, etc.)?

**STEP 2 — CLASSIFY:**
  Assign the email to one of these categories:
    - LEAD: New potential client/customer inquiry
    - CLIENT: Existing client communication
    - VENDOR: Supplier, service provider, or partner
    - INTERNAL: Team communication
    - NEWSLETTER: Marketing, subscriptions, updates
    - SPAM: Unwanted / suspicious email
    - URGENT: Contains escalation keywords or VIP sender
    - UNKNOWN: Cannot determine — needs human review

**STEP 3 — DECIDE:**
  Based on the category and the rules below, choose ONE action:

  A) **AUTO-REPLY** — Send an immediate reply.
     Use when: Known contacts, clear questions with clear answers,
     routine acknowledgments, meeting confirmations.
     Condition: autonomy.auto_reply_known_contacts is {autonomy.get('auto_reply_known_contacts', True)}

  B) **DRAFT REPLY** — Create a draft for the owner to review.
     Use when: New leads (first contact), sensitive topics, unclear intent,
     requests involving money/contracts, anything you're uncertain about.
     Condition: autonomy.auto_reply_new_leads is {autonomy.get('auto_reply_new_leads', False)}

  C) **LABEL & ARCHIVE** — Organize without replying.
     Use when: Newsletters, notifications, automated emails, FYI messages.
     Condition: autonomy.auto_label_and_archive is {autonomy.get('auto_label_and_archive', True)}

  D) **SCHEDULE FOLLOW-UP** — Set a reminder to check back later.
     Use when: Waiting for a response, time-sensitive opportunities,
     pending decisions.
     Condition: autonomy.auto_schedule_followups is {autonomy.get('auto_schedule_followups', True)}

  E) **ESCALATE** — Alert the owner immediately.
     Use when: Legal matters, complaints, threats, financial requests,
     VIP contacts with urgent messages, anything matching escalation keywords.
     Preferred channel: {escalation.get('channel', 'slack')}

  F) **IGNORE** — Do nothing (spam, blocked senders).
     Use when: Email is spam or sender is in blocked list.

**STEP 4 — ACT:**
  Execute the chosen action using the appropriate tools.
  You may chain multiple tools (e.g., reply + label + schedule follow-up).

**STEP 5 — REMEMBER:**
  After acting, always update the sender's memory with what you did and why.

═══════════════════════════════════════════════
4. CATEGORY HANDLING RULES
═══════════════════════════════════════════════

{rules_text}

═══════════════════════════════════════════════
5. MEMORY USAGE
═══════════════════════════════════════════════

Before processing each email, you will receive context about:
  - **sender_history**: Past interactions with this sender (from long-term memory)
  - **active_business_goals**: Current business objectives
  - **today_actions_count**: How many actions you've taken today

USE THIS CONTEXT. If you've interacted with a sender before:
  - Reference previous conversations in your reply
  - Maintain continuity (don't ask questions they already answered)
  - Adjust your approach based on past outcomes

If this is a first-time sender:
  - Treat them as a potential lead
  - Be welcoming but careful
  - Create a new memory entry for them

═══════════════════════════════════════════════
6. SAFETY BOUNDARIES — ABSOLUTE RULES
═══════════════════════════════════════════════

These rules CANNOT be overridden under ANY circumstances:

  1. NEVER delete any email permanently.
  2. NEVER send an email to more than 50 recipients at once.
  3. NEVER include passwords, API keys, tokens, or secrets in outgoing emails.
  4. NEVER reply to emails flagged as spam.
  5. NEVER commit to financial transactions (payments, wire transfers, invoices).
  6. NEVER impersonate the owner as CEO, legal representative, or authority figure.
  7. STOP all actions if the daily action limit has been exceeded.

If you detect ANY of these situations, STOP and escalate to the owner.

═══════════════════════════════════════════════
7. AUTONOMY CONFIGURATION
═══════════════════════════════════════════════

  - Auto-reply to known contacts: {autonomy.get('auto_reply_known_contacts', True)}
  - Auto-reply to new leads: {autonomy.get('auto_reply_new_leads', False)}
  - Auto-label and archive: {autonomy.get('auto_label_and_archive', True)}
  - Auto-schedule follow-ups: {autonomy.get('auto_schedule_followups', True)}
  - Escalate unknown senders: {autonomy.get('escalate_unknown_senders', False)}

When auto-reply is disabled for a category, create a DRAFT instead.

═══════════════════════════════════════════════
8. SPECIAL CONTACTS
═══════════════════════════════════════════════

  VIP contacts (always prioritize): {vip_text}
  Blocked senders (never reply): {blocked_text}

═══════════════════════════════════════════════
9. FOLLOW-UP DEFAULTS
═══════════════════════════════════════════════

  - Lead follow-up: {followup_defaults.get('lead_followup_hours', 24)} hours
  - Client follow-up: {followup_defaults.get('client_followup_hours', 48)} hours
  - Vendor follow-up: {followup_defaults.get('vendor_followup_hours', 72)} hours

═══════════════════════════════════════════════
10. WORKING HOURS
═══════════════════════════════════════════════

  Timezone: {working_hours.get('timezone', 'UTC')}
  Active: {working_hours.get('start', '09:00')} — {working_hours.get('end', '18:00')}
  Days: {', '.join(working_hours.get('days', ['Mon-Fri']))}

Outside working hours, prefer creating drafts over sending replies,
unless the email is urgent or from a VIP contact.

═══════════════════════════════════════════════
11. REPLY TEMPLATES
═══════════════════════════════════════════════

Use these as starting points (customize based on context):
{templates_text}

═══════════════════════════════════════════════
12. OUTPUT FORMAT
═══════════════════════════════════════════════

After processing each email, output a brief summary of what you did:
  - Email ID and sender
  - Category assigned
  - Action taken
  - Tools used
  - Any follow-ups scheduled
  - Any escalations made

This summary is used for the daily report.
"""
    return prompt


# ============================================================================
# Agent factory
# ============================================================================


def create_agent(user_config: dict[str, Any]) -> Agent:
    """Create and return a configured GmailMind agent.

    The agent is wired to all 12 safety-guarded tools and receives a
    system prompt built from the user's business configuration.

    Args:
        user_config: The loaded business configuration dict.

    Returns:
        An ``Agent`` instance ready to be run via ``Runner.run()``.
    """
    system_prompt = build_system_prompt(user_config)

    agent = Agent(
        name="GmailMind",
        instructions=system_prompt,
        tools=ALL_TOOLS,
        model="gpt-4o",
    )

    logger.info(
        "GmailMind agent created (model=gpt-4o, tools=%d, business=%s).",
        len(ALL_TOOLS),
        user_config.get("business_name", "unknown"),
    )
    return agent


def build_email_context_message(
    email_data: dict[str, Any],
    sender_history: dict[str, Any] | None,
    business_goals: list[str],
    today_actions_count: int,
    pending_followups: list[dict[str, Any]] | None = None,
) -> str:
    """Build the per-email context message sent to the agent.

    This message is passed as user input when running the agent for each
    email, giving it all the context it needs to make a decision.

    Args:
        email_data: The email dict (id, thread_id, subject, sender, body, etc.).
        sender_history: Long-term memory profile for this sender, or None.
        business_goals: List of active business goal strings.
        today_actions_count: Number of actions taken today so far.
        pending_followups: Any pending follow-ups related to this sender.

    Returns:
        A formatted context string for the agent.
    """
    email_id = email_data.get("id", "unknown")
    thread_id = email_data.get("thread_id", "unknown")
    subject = email_data.get("subject", "(no subject)")
    body = email_data.get("body", "")
    snippet = email_data.get("snippet", "")
    labels = email_data.get("labels", [])

    sender = email_data.get("sender", {})
    if isinstance(sender, dict):
        sender_email = sender.get("email", "unknown")
        sender_name = sender.get("name", "")
    else:
        sender_email = str(sender)
        sender_name = ""

    # Build sender history section
    if sender_history:
        history_entries = sender_history.get("history", [])
        recent_history = history_entries[-5:] if history_entries else []
        history_text = ""
        for entry in recent_history:
            ts = entry.get("timestamp", "")
            action = entry.get("action", "")
            note = entry.get("note", "")
            history_text += f"    - [{ts}] {action}: {note}\n"

        sender_section = f"""  Known contact: YES
  Name: {sender_history.get('name', sender_name)}
  Company: {sender_history.get('company', 'Unknown')}
  Tags: {', '.join(sender_history.get('tags', []))}
  Last interaction: {sender_history.get('last_interaction', 'Unknown')}
  Recent history:
{history_text if history_text else '    (no recent history)'}"""
    else:
        sender_section = f"""  Known contact: NO (first-time sender)
  Name: {sender_name if sender_name else 'Unknown'}
  Company: Unknown
  Tags: None"""

    # Build follow-up section
    followup_section = ""
    if pending_followups:
        followup_section = "\n  Pending follow-ups for this sender:\n"
        for fu in pending_followups:
            followup_section += (
                f"    - Due: {fu.get('due_time', '?')} | "
                f"Note: {fu.get('note', 'none')} | "
                f"Status: {fu.get('status', 'pending')}\n"
            )

    # Build goals section
    goals_text = "\n".join(f"  {i}. {g}" for i, g in enumerate(business_goals, 1))

    context = f"""
═══════════════════════════════════════════════
NEW EMAIL TO PROCESS
═══════════════════════════════════════════════

**Email Details:**
  ID: {email_id}
  Thread ID: {thread_id}
  From: {sender_name} <{sender_email}>
  Subject: {subject}
  Labels: {', '.join(labels) if labels else 'none'}
  Snippet: {snippet}

**Full Body:**
{body if body else '(empty body)'}

**Sender Memory:**
{sender_section}{followup_section}

**Session Context:**
  Actions taken today: {today_actions_count}
  Active business goals:
{goals_text}

═══════════════════════════════════════════════
INSTRUCTIONS: Apply the THINK framework (Observe → Classify → Decide → Act → Remember).
Process this email and take the appropriate action(s) using your tools.
═══════════════════════════════════════════════
"""
    return context


# ============================================================================
# GmailMind class wrapper
# ============================================================================


class GmailMind:
    """Convenience wrapper around ``create_agent()``.

    Allows the agent to be instantiated as a class::

        from agent.gmailmind import GmailMind

        agent = GmailMind()
        agent.name       # "GmailMind"
        agent.agent      # underlying Agent instance

    Args:
        user_config: Optional business config dict. Uses DEFAULT_CONFIG when
            not provided.
    """

    def __init__(self, user_config: dict[str, Any] | None = None) -> None:
        self._config = user_config or dict(DEFAULT_CONFIG)
        self._agent = create_agent(self._config)

    # Proxy core attributes from the underlying Agent so callers can use
    # GmailMind instances directly where they'd use an Agent.

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def instructions(self) -> str:
        return self._agent.instructions

    @property
    def tools(self) -> list:
        return self._agent.tools

    @property
    def model(self) -> str:
        return self._agent.model

    @property
    def agent(self) -> Agent:
        """Return the underlying OpenAI Agents SDK ``Agent`` instance."""
        return self._agent

    @property
    def config(self) -> dict[str, Any]:
        """Return the business configuration used to build this agent."""
        return self._config

    def __repr__(self) -> str:
        return (
            f"<GmailMind(name={self.name!r}, model={self.model!r}, "
            f"tools={len(self.tools)})>"
        )
