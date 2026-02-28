"""Daily report generator for GmailMind.

Produces structured summaries and HTML-formatted email reports of
everything the agent did during a given day.

Usage::

    from agent.report_generator import ReportGenerator

    rg = ReportGenerator()
    report = rg.generate_daily_summary(user_id="u_123", date="2026-02-28")
    html   = rg.format_email_report(report)
    items  = rg.get_attention_items(user_id="u_123")
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func, text

from config.database import SessionLocal
from models.schemas import ActionLog, FollowUp

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates daily summaries, HTML email reports, and attention-item lists."""

    # Action keywords used for classification.
    _AUTO_REPLY_ACTIONS = {"reply_to_email", "send_email", "auto_reply"}
    _ESCALATION_ACTIONS = {"send_escalation_alert", "escalate"}
    _DRAFT_ACTIONS = {"create_draft"}
    _FOLLOWUP_ACTIONS = {"schedule_followup"}
    _LABEL_ACTIONS = {"label_email"}
    _LEAD_KEYWORDS = {"lead", "new_lead", "potential_client"}

    # ------------------------------------------------------------------ #
    #  1. generate_daily_summary
    # ------------------------------------------------------------------ #

    def generate_daily_summary(self, user_id: str, date: str) -> dict[str, Any]:
        """Pull all actions from DB for this user + date and build stats.

        Args:
            user_id: The user identifier.
            date: Date string in ``YYYY-MM-DD`` format.

        Returns:
            Structured report dict with counts, breakdowns, and
            attention items.
        """
        day_start, day_end = self._day_range(date)

        db = SessionLocal()
        try:
            rows = (
                db.execute(
                    select(ActionLog)
                    .where(ActionLog.timestamp >= day_start)
                    .where(ActionLog.timestamp < day_end)
                    .order_by(ActionLog.timestamp.asc())
                )
                .scalars()
                .all()
            )

            # ---- Core counters ----
            emails_processed = 0
            auto_replied = 0
            escalated = 0
            followups_set = 0
            leads_created = 0
            drafts_created = 0
            labeled = 0
            errors = 0

            unique_senders: set[str] = set()
            tools_used: dict[str, int] = {}
            actions_breakdown: dict[str, int] = {}
            response_times: list[float] = []
            action_details: list[dict[str, Any]] = []

            for row in rows:
                tool = row.tool_used or ""
                action = row.action_taken or ""
                meta = row.extra_metadata or {}
                sender = row.email_from or ""

                # Track tools
                tools_used[tool] = tools_used.get(tool, 0) + 1

                # Track actions
                actions_breakdown[action] = actions_breakdown.get(action, 0) + 1

                # Unique senders
                if sender:
                    unique_senders.add(sender)

                # Classify
                if tool in self._AUTO_REPLY_ACTIONS or "reply" in action.lower():
                    auto_replied += 1
                if tool in self._ESCALATION_ACTIONS or "escalat" in action.lower():
                    escalated += 1
                if tool in self._DRAFT_ACTIONS or "draft" in action.lower():
                    drafts_created += 1
                if tool in self._FOLLOWUP_ACTIONS or "followup" in action.lower() or "follow_up" in action.lower():
                    followups_set += 1
                if tool in self._LABEL_ACTIONS:
                    labeled += 1
                if any(kw in action.lower() for kw in self._LEAD_KEYWORDS):
                    leads_created += 1
                if "error" in action.lower() or "error" in (row.outcome or "").lower():
                    errors += 1
                if tool == "read_emails" or action == "agent_processed_email":
                    emails_processed += 1

                # Response time (if stored in metadata)
                rt = meta.get("response_time_seconds")
                if rt is not None:
                    try:
                        response_times.append(float(rt))
                    except (TypeError, ValueError):
                        pass

                action_details.append({
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "sender": sender,
                    "action": action,
                    "tool": tool,
                    "outcome": (row.outcome or "")[:200],
                })

            avg_response_time = (
                round(sum(response_times) / len(response_times), 1)
                if response_times
                else None
            )

            # Pending follow-ups
            pending_followups = (
                db.execute(
                    select(func.count())
                    .select_from(FollowUp)
                    .where(FollowUp.status == "pending")
                )
                .scalar()
                or 0
            )

            # Attention items
            attention = self._find_attention_items(rows)

            report: dict[str, Any] = {
                "date": date,
                "user_id": user_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                # ---- Key metrics ----
                "emails_processed": emails_processed,
                "auto_replied": auto_replied,
                "escalated": escalated,
                "followups_set": followups_set,
                "leads_created": leads_created,
                "drafts_created": drafts_created,
                "labeled": labeled,
                "errors": errors,
                "avg_response_time_seconds": avg_response_time,
                # ---- Aggregate ----
                "total_actions": len(rows),
                "unique_senders": len(unique_senders),
                "pending_followups": pending_followups,
                # ---- Breakdowns ----
                "tools_breakdown": tools_used,
                "actions_breakdown": actions_breakdown,
                # ---- Details ----
                "action_details": action_details,
                "attention_items": attention,
            }

            logger.info(
                "Report generated for %s on %s: %d actions, %d emails.",
                user_id, date, len(rows), emails_processed,
            )
            return report

        finally:
            db.close()

    # ------------------------------------------------------------------ #
    #  2. format_email_report
    # ------------------------------------------------------------------ #

    def format_email_report(self, report: dict[str, Any]) -> str:
        """Convert a report dict into an HTML email body.

        Includes tables, emoji indicators, and an action list.

        Args:
            report: The dict returned by ``generate_daily_summary``.

        Returns:
            A complete HTML string ready to send via Gmail.
        """
        date = report.get("date", "Unknown")
        total = report.get("total_actions", 0)
        emails = report.get("emails_processed", 0)
        replied = report.get("auto_replied", 0)
        escalated = report.get("escalated", 0)
        followups = report.get("followups_set", 0)
        leads = report.get("leads_created", 0)
        drafts = report.get("drafts_created", 0)
        errors = report.get("errors", 0)
        avg_rt = report.get("avg_response_time_seconds")
        senders = report.get("unique_senders", 0)
        pending_fu = report.get("pending_followups", 0)
        tools = report.get("tools_breakdown", {})
        attention = report.get("attention_items", [])

        avg_rt_text = f"{avg_rt}s" if avg_rt is not None else "N/A"

        # ---- Tools breakdown rows ----
        tool_rows = ""
        for tool_name, count in sorted(tools.items(), key=lambda x: -x[1]):
            tool_rows += f"<tr><td>{tool_name}</td><td align='center'>{count}</td></tr>\n"
        if not tool_rows:
            tool_rows = "<tr><td colspan='2'>No tools used today</td></tr>\n"

        # ---- Attention items rows ----
        attention_rows = ""
        for item in attention:
            kind = item.get("type", "info")
            icon = {"escalation": "\u26a0\ufe0f", "error": "\u274c", "draft": "\u270f\ufe0f"}.get(kind, "\u2139\ufe0f")
            attention_rows += (
                f"<tr>"
                f"<td>{icon} {kind.upper()}</td>"
                f"<td>{item.get('sender', '')}</td>"
                f"<td>{item.get('description', '')}</td>"
                f"</tr>\n"
            )
        if not attention_rows:
            attention_rows = "<tr><td colspan='3'>Nothing needs your attention today \u2705</td></tr>\n"

        html = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
  h1 {{ color: #1a73e8; font-size: 22px; }}
  h2 {{ color: #444; font-size: 16px; margin-top: 24px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 8px 12px; text-align: left; font-size: 14px; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  .metric {{ display: inline-block; width: 45%; vertical-align: top; margin: 6px 0; }}
  .metric-value {{ font-size: 28px; font-weight: 700; color: #1a73e8; }}
  .metric-label {{ font-size: 12px; color: #777; text-transform: uppercase; }}
  .footer {{ margin-top: 30px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
</style>
</head>
<body>

<h1>\U0001f4ca GmailMind Daily Report &mdash; {date}</h1>

<h2>\U0001f4c8 Key Metrics</h2>

<div>
  <div class="metric">
    <div class="metric-value">{emails}</div>
    <div class="metric-label">\U0001f4e8 Emails Processed</div>
  </div>
  <div class="metric">
    <div class="metric-value">{replied}</div>
    <div class="metric-label">\u2709\ufe0f Auto-Replied</div>
  </div>
  <div class="metric">
    <div class="metric-value">{escalated}</div>
    <div class="metric-label">\u26a0\ufe0f Escalated</div>
  </div>
  <div class="metric">
    <div class="metric-value">{followups}</div>
    <div class="metric-label">\u23f0 Follow-ups Set</div>
  </div>
  <div class="metric">
    <div class="metric-value">{leads}</div>
    <div class="metric-label">\U0001f31f Leads Created</div>
  </div>
  <div class="metric">
    <div class="metric-value">{drafts}</div>
    <div class="metric-label">\u270f\ufe0f Drafts Created</div>
  </div>
</div>

<table>
  <tr>
    <th>Metric</th><th>Value</th>
  </tr>
  <tr><td>Total Actions</td><td>{total}</td></tr>
  <tr><td>Unique Senders</td><td>{senders}</td></tr>
  <tr><td>Avg Response Time</td><td>{avg_rt_text}</td></tr>
  <tr><td>Pending Follow-ups</td><td>{pending_fu}</td></tr>
  <tr><td>Errors</td><td>{errors}</td></tr>
</table>

<h2>\U0001f527 Tools Breakdown</h2>
<table>
  <tr><th>Tool</th><th>Uses</th></tr>
  {tool_rows}
</table>

<h2>\U0001f6a8 Items Needing Your Attention</h2>
<table>
  <tr><th>Type</th><th>Sender</th><th>Details</th></tr>
  {attention_rows}
</table>

<div class="footer">
  Generated by <strong>GmailMind</strong> &mdash; HireAI Digital Employee #1<br>
  Report time: {report.get('generated_at', '')}
</div>

</body>
</html>"""
        return html

    # ------------------------------------------------------------------ #
    #  3. get_attention_items
    # ------------------------------------------------------------------ #

    def get_attention_items(self, user_id: str) -> list[dict[str, Any]]:
        """Return actions that need human review.

        Scans today's action log for:
          - Escalations (sent or pending).
          - Drafts awaiting approval.
          - Errors or safety violations.

        Args:
            user_id: The user identifier.

        Returns:
            A list of attention-item dicts, each with ``type``, ``sender``,
            ``description``, ``timestamp``, and ``action_id``.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

        db = SessionLocal()
        try:
            rows = (
                db.execute(
                    select(ActionLog)
                    .where(ActionLog.timestamp >= today_start)
                    .order_by(ActionLog.timestamp.desc())
                )
                .scalars()
                .all()
            )

            items = self._find_attention_items(rows)

            # Also add pending follow-ups that are overdue
            now = datetime.now(timezone.utc)
            overdue = (
                db.execute(
                    select(FollowUp)
                    .where(FollowUp.status == "pending")
                    .where(FollowUp.due_time < now)
                    .order_by(FollowUp.due_time.asc())
                )
                .scalars()
                .all()
            )

            for fu in overdue:
                items.append({
                    "type": "overdue_followup",
                    "sender": fu.sender,
                    "description": (
                        f"Follow-up overdue since "
                        f"{fu.due_time.isoformat() if fu.due_time else '?'}. "
                        f"Note: {fu.note or '(none)'}"
                    ),
                    "timestamp": fu.due_time.isoformat() if fu.due_time else "",
                    "action_id": fu.id,
                })

            logger.info(
                "get_attention_items for %s: found %d items.", user_id, len(items),
            )
            return items

        finally:
            db.close()

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _day_range(date: str) -> tuple[datetime, datetime]:
        """Parse a date string and return (start, end) datetimes.

        Args:
            date: ``YYYY-MM-DD`` string.

        Returns:
            A tuple of (day_start_utc, next_day_start_utc).
        """
        day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return day, day + timedelta(days=1)

    @staticmethod
    def _find_attention_items(rows: list) -> list[dict[str, Any]]:
        """Scan action log rows for items needing human attention.

        Args:
            rows: List of ``ActionLog`` ORM instances.

        Returns:
            List of attention-item dicts.
        """
        items: list[dict[str, Any]] = []

        for row in rows:
            tool = row.tool_used or ""
            action = row.action_taken or ""
            outcome = row.outcome or ""
            sender = row.email_from or ""
            ts = row.timestamp.isoformat() if row.timestamp else ""

            # Escalations
            if (
                tool == "send_escalation_alert"
                or "escalat" in action.lower()
            ):
                items.append({
                    "type": "escalation",
                    "sender": sender,
                    "description": outcome[:300] or action,
                    "timestamp": ts,
                    "action_id": row.id,
                })

            # Drafts awaiting approval
            elif tool == "create_draft" or "draft" in action.lower():
                items.append({
                    "type": "draft",
                    "sender": sender,
                    "description": f"Draft created — {outcome[:200] or action}",
                    "timestamp": ts,
                    "action_id": row.id,
                })

            # Errors and safety violations
            elif (
                "error" in action.lower()
                or "error" in outcome.lower()
                or "safety" in outcome.lower()
            ):
                items.append({
                    "type": "error",
                    "sender": sender,
                    "description": outcome[:300] or action,
                    "timestamp": ts,
                    "action_id": row.id,
                })

        return items
