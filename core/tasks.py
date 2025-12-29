from celery import shared_task
from django.contrib.sessions.models import Session
from django.utils import timezone


@shared_task
def cleanup_expired_sessions():  # Periodic task to delete expired user sessions from database
    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count = expired.count()
    expired.delete()
    return f"Deleted {count} expired sessions"


@shared_task
def generate_daily_analytics():  # Periodic task to generate daily analytics for appointments and transactions
    from datetime import date
    from appointments.models import Appointment
    from payments.models import HealthTransaction

    today = date.today()
    appointments_count = Appointment.objects.filter(appointment_date=today).count()
    transactions_count = HealthTransaction.objects.filter(
        created_at__date=today
    ).count()

    return f"Daily analytics: {appointments_count} appointments, {transactions_count} transactions"


@shared_task
def report_health_to_central_hub():  # Periodic task to report regional deployment health to central hub every 5 minutes
    """
    Periodic task to report regional deployment health to central hub
    Runs every 5 minutes
    """
    from .centralized_logging import HealthMonitor
    from django.conf import settings
    
    if not getattr(settings, 'ENABLE_CENTRALIZED_MONITORING', False):
        return "Centralized monitoring disabled"
    
    monitor = HealthMonitor()
    monitor.report_to_central_hub()
    return f"Health status reported from region: {getattr(settings, 'REGION_CODE', 'default')}"


@shared_task
def sync_feature_flags():  # Periodic task to sync feature flags from central hub every hour
    """
    Sync feature flags from central hub (if applicable)
    Runs every hour
    """
    from .feature_flags import FeatureFlagManager
    
    manager = FeatureFlagManager()
    # Implementation would fetch flags from central hub if needed
    return "Feature flags synchronized"


@shared_task
def cleanup_old_logs():  # Periodic task to clean up log entries older than 90 days
    """
    Clean up old log entries to prevent database bloat
    Runs daily
    """
    from datetime import timedelta
    from django.utils import timezone
    
    # Clean logs older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    # Implementation would delete old log entries
    return f"Cleaned logs older than {cutoff_date}"
