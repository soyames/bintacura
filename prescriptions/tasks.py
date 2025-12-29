from celery import shared_task
from django.utils import timezone
from .models import Prescription


@shared_task
def expire_old_prescriptions():  # Expire old prescriptions
    from datetime import date

    today = date.today()

    expired = Prescription.objects.filter(valid_until__lt=today, status="active")
    expired.update(status="expired")

    return f"Expired {expired.count()} prescriptions"


@shared_task
def check_refill_reminders():  # Check refill reminders
    from datetime import date, timedelta

    soon_to_expire = Prescription.objects.filter(
        valid_until__lte=date.today() + timedelta(days=7),
        status="active",
        refills_used__lt=models.F("max_refills"),
    )

    return f"Found {soon_to_expire.count()} prescriptions needing refill reminders"
