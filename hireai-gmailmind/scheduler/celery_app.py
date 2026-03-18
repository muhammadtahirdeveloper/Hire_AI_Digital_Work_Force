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
}

# Default queue for tasks that don't specify one.
app.conf.task_default_queue = "default"
