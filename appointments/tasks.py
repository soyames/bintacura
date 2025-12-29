from celery import shared_task
from django.utils import timezone
from .models import Appointment


@shared_task
def send_appointment_reminders():  # Send appointment reminders
    from datetime import timedelta

    tomorrow = timezone.now().date() + timedelta(days=1)

    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=["confirmed", "pending"],
        reminder_sent=False,
    )

    for appointment in appointments:
        appointment.reminder_sent = True
        appointment.save()

    return f"Sent {appointments.count()} reminders"


@shared_task
def update_appointment_status():  # Update appointment status
    from datetime import timedelta

    yesterday = timezone.now().date() - timedelta(days=1)

    Appointment.objects.filter(
        appointment_date__lt=yesterday, status="confirmed"
    ).update(status="no_show")

    return "Updated past appointments"
