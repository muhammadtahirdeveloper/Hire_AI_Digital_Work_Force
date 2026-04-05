"""Celery application configuration for GmailMind.

Sets up the Celery app with:
  - Redis as the message broker and result backend.
  - A periodic beat schedule that drives the autonomous agent loop,
    processes due follow-ups, and sends end-of-day reports.

Usage — start the worker::

    celery -A scheduler.celery_app worker --loglevel=info

Usage — start the beat scheduler::

    celery -A scheduler.celery_app beat --loglevel=info
"""

import ssl

from celery import Celery
from celery.schedules import crontab

from config.settings import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    POLL_INTERVAL_SECONDS,
)

# ============================================================================
# Celery app
# ============================================================================

app = Celery("gmailmind")

# --- TLS/SSL config for rediss:// URLs (e.g. Upstash Redis) ---
_redis_ssl = {}
if CELERY_BROKER_URL.startswith("rediss://"):
    _redis_ssl = {
        "broker_use_ssl": {"ssl_cert_reqs": ssl.CERT_REQUIRED},
        "redis_backend_use_ssl": {"ssl_cert_reqs": ssl.CERT_REQUIRED},
    }

app.conf.update(
    # --- Broker & backend ---
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,

    # --- Serialisation ---
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # --- Timezone ---
    timezone="UTC",
    enable_utc=True,

    # --- Reliability ---
    task_acks_late=True,                  # ack after task completes (not on receipt)
    worker_prefetch_multiplier=1,         # one task at a time per worker
    task_reject_on_worker_lost=True,      # re-queue if worker crashes
    task_soft_time_limit=540,             # 9-minute soft limit per task
    task_time_limit=600,                  # 10-minute hard limit per task

    # --- Auto-discover tasks ---
    imports=["scheduler.tasks"],

    # --- TLS (applied only for rediss:// URLs) ---
    **_redis_ssl,
)

# ============================================================================
# Beat schedule — periodic tasks
# ============================================================================

app.conf.beat_schedule = {
    # --- Main agent loop: runs every POLL_INTERVAL_SECONDS ---
    # Dispatcher queries all active users and fans out per-user tasks.
    "run-gmailmind-agent-loop": {
        "task": "scheduler.tasks.run_gmailmind_all_users",
        "schedule": POLL_INTERVAL_SECONDS,
        "options": {"queue": "agent"},
    },

    # --- Process due follow-ups: every 2 minutes ---
    "process-due-followups": {
        "task": "scheduler.tasks.process_due_followups",
        "schedule": 120.0,
        "options": {"queue": "followups"},
    },

    # --- Daily summary report: every day at 18:00 UTC ---
    "send-daily-report": {
        "task": "scheduler.tasks.send_daily_report",
        "schedule": crontab(hour=18, minute=0),
        "args": ("default",),
        "options": {"queue": "reports"},
    },

    # --- Weekly HR recruitment report: every Monday at 09:00 UTC ---
    "send-hr-weekly-report": {
        "task": "scheduler.tasks.send_hr_weekly_report",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
        "args": ("default",),
        "options": {"queue": "reports"},
    },

    # --- Weekly Real Estate report: every Monday at 09:00 UTC ---
    "send-re-weekly-report": {
        "task": "scheduler.tasks.send_real_estate_weekly_report",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
        "args": ("default",),
        "options": {"queue": "reports"},
    },

    # --- Weekly E-commerce report: every Monday at 09:30 UTC ---
    "send-ecommerce-weekly-report": {
        "task": "scheduler.tasks.send_ecommerce_weekly_report",
        "schedule": crontab(hour=9, minute=30, day_of_week=1),
        "args": ("default",),
        "options": {"queue": "reports"},
    },

    # --- Renew Gmail watches: daily at 03:00 UTC ---
    "renew-gmail-watches": {
        "task": "scheduler.tasks.renew_gmail_watches",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "agent"},
    },

    # --- Event reminders: every 30 minutes ---
    "send-event-reminders": {
        "task": "scheduler.tasks.send_event_reminders",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "followups"},
    },

    # --- Weekly user summary: every Monday at 08:00 UTC ---
    "send-weekly-user-summary": {
        "task": "scheduler.tasks.send_weekly_user_summary",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
        "args": ("default",),
        "options": {"queue": "reports"},
    },
}

# Queue routing: realtime (high priority) > agent > followups > reports
app.conf.task_default_queue = "default"
app.conf.task_routes = {
    "scheduler.tasks.run_gmailmind_for_user": {"queue": "agent"},
    "scheduler.tasks.run_gmailmind_all_users": {"queue": "agent"},
    "scheduler.tasks.process_due_followups": {"queue": "followups"},
    "scheduler.tasks.send_daily_report": {"queue": "reports"},
    "scheduler.tasks.send_hr_weekly_report": {"queue": "reports"},
    "scheduler.tasks.send_real_estate_weekly_report": {"queue": "reports"},
    "scheduler.tasks.send_ecommerce_weekly_report": {"queue": "reports"},
    "scheduler.tasks.renew_gmail_watches": {"queue": "agent"},
    "scheduler.tasks.send_event_reminders": {"queue": "followups"},
    "scheduler.tasks.send_weekly_user_summary": {"queue": "reports"},
}
# Worker consumes queues in priority order:
# celery -A scheduler.celery_app worker -Q realtime,agent,default,followups,reports
