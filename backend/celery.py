import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("BintaCura")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-appointment-reminders": {
        "task": "appointments.tasks.send_appointment_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "process-insurance-invoices": {
        "task": "insurance.tasks.process_pending_invoices",
        "schedule": crontab(hour=0, minute=0),
    },
    "expire-prescriptions": {
        "task": "prescriptions.tasks.expire_old_prescriptions",
        "schedule": crontab(hour=1, minute=0),
    },
    "cleanup-old-sessions": {
        "task": "core.tasks.cleanup_expired_sessions",
        "schedule": crontab(hour=2, minute=0),
    },
    "backup-database": {
        "task": "core.backup_tasks.backup_database_task",
        "schedule": crontab(hour=3, minute=0),
    },
    "cleanup-old-backups": {
        "task": "core.backup_tasks.cleanup_old_backups",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
}

